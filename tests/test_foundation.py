"""Foundation contracts: parse, resolve assets, enforce provenance, reproduce pixels."""
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
                    if name.startswith('$'):
                        continue
                    with self.subTest(path=path.name, texture=name):
                        self.assertTrue((ROOT / 'media' / name).is_file())
                    count += 1
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
        for path in (ROOT / '1080i').glob('*.xml'):
            for node in ET.parse(path).iter('font'):
                if not list(node):
                    self.assertIn(node.text, names)

    def test_clean_room_guard(self):
        forbidden = re.compile(rb'arctic|(?<![a-z])fuse(?![a-z])|jurial|skinvariables|texturemaker|themoviedb', re.I)
        excluded = {Path(__file__).resolve()}
        for path in project_files():
            if path in excluded:
                continue
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertIsNone(forbidden.search(path.read_bytes()))

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

    def test_localized_labels_resolve(self):
        source = (ROOT / 'language/resource.language.en_gb/strings.po').read_text()
        ids = set(re.findall(r'msgctxt "#(\d+)"', source))
        used = set()
        for path in (ROOT / '1080i').glob('*.xml'):
            used.update(re.findall(r'\$LOCALIZE\[(31\d+)\]', path.read_text()))
        self.assertEqual(used, ids)

    def test_addon_contract(self):
        addon = ET.parse(ROOT / 'addon.xml').getroot()
        self.assertEqual(addon.get('id'), 'skin.starlight')
        self.assertEqual(addon.get('version'), '2.0.0')
        self.assertEqual({n.get('addon'): n.get('version') for n in addon.findall('requires/import')},
                         {'xbmc.gui': '5.17.0', 'xbmc.python': '3.0.0'})
        resolution = addon.find("extension[@point='xbmc.gui.skin']/res")
        self.assertEqual((resolution.get('width'), resolution.get('height')), ('1920', '1080'))
        metadata = addon.find("extension[@point='xbmc.addon.metadata']")
        self.assertTrue(metadata.findtext('news').splitlines()[0].startswith('v2.0.0'))
        for asset in metadata.findall('assets/*'):
            self.assertTrue((ROOT / asset.text).is_file())


if __name__ == '__main__':
    unittest.main()
