"""Foundation contracts: parse, resolve assets, enforce provenance, reproduce pixels."""
import ast
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def project_files():
    result = subprocess.run(
        ['git', '-C', str(ROOT), 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, check=False)
    if result.returncode == 0 and Path(result.stdout.strip()) == ROOT:
        paths = subprocess.check_output(
            ['git', '-C', str(ROOT), 'ls-files', '--cached', '--others',
             '--exclude-standard', '-z']).decode().split('\0')
        return [ROOT / path for path in paths if path]
    return [path for path in ROOT.rglob('*') if path.is_file()
            and '__pycache__' not in path.parts and '.git' not in path.parts]


def digest_tree(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*.png'))}


class FoundationTests(unittest.TestCase):
    def test_preview_native_resolution_comparison(self):
        from render_home import HomePreview
        preview = HomePreview(ROOT)
        for resolution, expected in (('2160', True), ('1080', False), ('', False)):
            preview.item = {'VideoResolution': resolution}
            self.assertEqual(preview.condition(
                'Integer.IsGreaterOrEqual(ListItem.VideoResolution,2160)'), expected)

    def test_xml_parses(self):
        paths = list(ROOT.rglob('*.xml'))
        self.assertGreaterEqual(len(paths), 7)
        for path in paths:
            with self.subTest(path=path):
                ET.parse(path)

    def test_texture_references_resolve(self):
        count = 0
        for path in (ROOT / '1080i').glob('*.xml'):
            for node in ET.parse(path).iter():
                if 'texture' in node.tag and node.text and node.text.strip():
                    name = node.text.strip()
                    if '$' in name:
                        continue
                    with self.subTest(path=path.name, texture=name):
                        target = ROOT / name.removeprefix('special://skin/') if name.startswith('special://skin/') else ROOT / 'media' / name
                        self.assertTrue(target.is_file())
                    count += 1
                diffuse = node.get('diffuse', '')
                if diffuse and not diffuse.startswith('$'):
                    self.assertTrue((ROOT / 'media' / diffuse).is_file(), diffuse)
                if node.tag == 'imagepath' and node.text:
                    frames = sorted((ROOT / 'media' / node.text).glob('*.png'))
                    self.assertEqual(len(frames), 24)
                    self.assertEqual(len({p.read_bytes() for p in frames}), 24)
        self.assertGreater(count, 10)

    def test_fonts_resolve(self):
        fonts = ET.parse(ROOT / '1080i/Font.xml')
        self.assertEqual(fonts.find('fontset').get('id'), 'Default')
        names = set()
        for font in fonts.findall('.//font'):
            name = font.findtext('name')
            self.assertNotIn(name, names)
            names.add(name)
            path = ROOT / 'fonts' / font.findtext('filename')
            self.assertTrue(path.is_file(), str(path))
            self.assertEqual(path.read_bytes()[:4], b'\x00\x01\x00\x00')
        self.assertTrue((ROOT / 'fonts/OFL.txt').is_file())
        # Add-on dialogs (PlexKodiConnect Skip intro, Up Next) name Kodi's standard fonts.
        # Kodi falls back to font13, so a missing name renders no text at all.
        self.assertLessEqual({'font10', 'font11', 'font12', 'font12_title', 'font13', 'font14', 'font16',
                              'font20', 'font20_title', 'font25_narrow', 'font25_title', 'font27',
                              'font30', 'font37', 'font_clock'}, names)
        for path in (ROOT / '1080i').glob('*.xml'):
            for node in ET.parse(path).iter('font'):
                if not list(node):
                    if (node.text or '').startswith('$PARAM['):
                        parameter = node.text[7:-1]
                        defaults = [n.get('default') for n in ET.parse(path).iter('param')
                                    if n.get('name') == parameter and n.get('default')]
                        self.assertTrue(defaults, parameter)
                        for value in defaults:
                            self.assertIn(value, names)
                    else:
                        self.assertIn(node.text, names)

    def test_clean_room_guard(self):
        forbidden = re.compile(rb'arctic|(?<![a-z])fuse(?![a-z])|jurial|skinvariables|texturemaker|themoviedb', re.I)
        excluded = {Path(__file__).resolve()}
        for path in project_files():
            if path in excluded:
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIsNone(forbidden.search(path.read_bytes()))

    def test_conditions_require_info_labels(self):
        # Kodi resolves the first argument as an info label, never plain text.
        pattern = re.compile(r'(?:String\.(?:IsEqual|IsEmpty)|Integer\.\w+)\(\s*([^,)<\n]+)')
        for path in (ROOT / '1080i').glob('*.xml'):
            for match in pattern.finditer(path.read_text()):
                with self.subTest(path=path.name, argument=match[1]):
                    self.assertRegex(match[1], r'^(?:ListItem\.|Container(?:\(|\.)|Window(?:\(|\.)|Skin\.String\(|Control\.|System\.|Player\.|MusicPlayer\.|VideoPlayer\.|Weather\.)')

    def test_item_layouts_use_fixed_controls(self):
        import sys
        sys.path.insert(0, str(ROOT / 'resources/lib'))
        from skin_xml import expand
        includes = {node.get('name'): node
                    for path in (ROOT / '1080i').glob('Includes*.xml')
                    for node in ET.parse(path).iter('include') if node.get('name')}
        for path in (ROOT / '1080i').glob('*.xml'):
            if path.name.startswith('Includes'):
                continue
            # Expand every choice, including inactive layouts and optional dialogs.
            tree = expand(ET.parse(path).getroot(), includes, lambda _: True)
            for layout in tree.iter():
                if layout.tag not in ('itemlayout', 'focusedlayout'):
                    continue
                with self.subTest(path=path.name, layout=layout.tag):
                    self.assertFalse(any(node.get('type') == 'grouplist' for node in layout.iter('control')))
                    self.assertFalse(any(node.text == 'auto' for node in layout.iter('width')))

    def test_skin_strings_use_kodi_localization(self):
        for path in (ROOT / 'resources').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'getLocalizedString':
                    with self.subTest(path=path.name, line=node.lineno):
                        self.assertIsInstance(node.func.value, ast.Name)
                        self.assertEqual(node.func.value.id, 'xbmc')

    def test_texture_build_is_deterministic_and_current(self):
        with tempfile.TemporaryDirectory(prefix='starlight-textures-') as scratch:
            outputs = [Path(scratch) / name for name in ('first', 'second')]
            for output in outputs:
                subprocess.run([sys.executable, str(ROOT / 'tools/build_textures.py'),
                                '--output', str(output)], check=True, capture_output=True)
            expected = digest_tree(outputs[0])
            self.assertGreater(len(expected), 35)
            self.assertEqual(expected, digest_tree(outputs[1]))
            self.assertEqual(expected, digest_tree(ROOT / 'media'))

    def test_include_and_constant_references_resolve(self):
        trees = [ET.parse(p) for p in (ROOT / '1080i').glob('*.xml')]
        names = {node.get('name') for tree in trees
                 for node in tree.iter('include') if node.get('name')}
        constants = {node.get('name'): node.text for tree in trees
                     for node in tree.iter('constant')}
        for tree in trees:
            for node in tree.iter('include'):
                if node.get('file'):
                    self.assertTrue((ROOT / '1080i' / node.get('file')).is_file())
                elif not node.get('name'):
                    self.assertIn(node.get('content') or node.text, names)
            for node in tree.iter():
                if 'border' in node.attrib:
                    self.assertIn(node.get('border'), constants)
                    self.assertTrue(all(int(v) >= 0 for v in constants[node.get('border')].split(',')))

    def test_variable_references_resolve(self):
        paths = list((ROOT / '1080i').glob('*.xml'))
        names = {node.get('name') for path in paths
                 for node in ET.parse(path).iter('variable')}
        for path in paths:
            for name in re.findall(r'\$VAR\[([^],]+)', path.read_text()):
                with self.subTest(path=path.name, variable=name):
                    self.assertIn(name, names)

    def test_home_replaces_foundation_board(self):
        home = ET.parse(ROOT / '1080i/Home.xml')
        self.assertTrue(any(n.get('content') == 'HubRail' for n in home.iter('include')))
        self.assertTrue((ROOT / '1080i/Includes_Home.xml').is_file())
        for name in ('search', 'home', 'movies', 'tv', 'music', 'discover', 'settings', 'play'):
            self.assertTrue((ROOT / 'media/icons' / (name + '.png')).is_file(), name)

    def test_home_default_focus_exists_in_every_layout(self):
        from render_home import HomePreview
        focusable = {'list', 'fixedlist', 'panel', 'button'}
        for layout in ('', 'board', 'hero', 'landscape', 'poster', 'square'):
            with self.subTest(layout=layout):
                preview = HomePreview(ROOT, settings={'Home.Continue.Layout': layout})
                home = preview.home
                controls = {node.get('id'): node for node in home.iter('control') if node.get('id')}
                target = home.findtext('defaultcontrol')
                self.assertIn(target, controls)
                control = controls[target]
                while control.get('type') not in focusable:
                    default = control.findtext('defaultcontrol')
                    descendants = {node.get('id'): node for node in control.iter('control')
                                   if node is not control and node.get('id')}
                    if default:
                        self.assertIn(default, descendants)
                        control = descendants[default]
                    else:
                        control = next(node for node in descendants.values()
                                       if node.get('type') in focusable)
                self.assertIn(control.get('id'), ('510', '512'))

    def test_localized_labels_resolve(self):
        source = (ROOT / 'language/resource.language.en_gb/strings.po').read_text()
        ids = set(re.findall(r'msgctxt "#(\d+)"', source))
        used = set()
        for path in (ROOT / '1080i').glob('*.xml'):
            used.update(re.findall(r'\$LOCALIZE\[(31\d+)\]', path.read_text()))
        self.assertLessEqual(used, ids)

    def test_addon_contract(self):
        addon = ET.parse(ROOT / 'addon.xml').getroot()
        self.assertEqual(addon.get('id'), 'skin.starlight')
        self.assertEqual({n.get('addon'): n.get('version') for n in addon.findall('requires/import')},
                         {'xbmc.gui': '5.17.0', 'xbmc.python': '3.0.0', 'script.starlight': '1.0.0'})
        resolution = addon.find("extension[@point='xbmc.gui.skin']/res")
        self.assertEqual((resolution.get('width'), resolution.get('height')), ('1920', '1080'))
        metadata = addon.find("extension[@point='xbmc.addon.metadata']")
        self.assertTrue(metadata.findtext('news').splitlines()[0].startswith('v' + addon.get('version')))
        for asset in metadata.findall('assets/*'):
            self.assertTrue((ROOT / asset.text).is_file())


if __name__ == '__main__':
    unittest.main()
