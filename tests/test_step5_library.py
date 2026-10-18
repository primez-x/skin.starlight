"""Step 5 failures: absent views, unsafe routes, duplicate Board records,
source mixing, stale keyboard input, missing focus targets, and empty libraries.
Kodi owns native navigation. Static checks do not replace a Kodi session.
"""
import ast
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'resources/lib'))
sys.path.insert(0, str(ROOT / 'tools'))
VIEWS = set(range(4200, 4226))


class LibraryTests(unittest.TestCase):
    def expanded(self, name):
        from render_home import HomePreview
        return HomePreview(ROOT).expand(ET.parse(ROOT / '1080i' / name).getroot())

    def test_native_views_and_navigation_targets(self):
        for name in ('MyVideoNav.xml', 'MyMusicNav.xml'):
            with self.subTest(window=name):
                tree = self.expanded(name)
                declared = {int(value) for value in tree.findtext('views').split(',')}
                self.assertEqual(declared, VIEWS)
                controls = {int(n.get('id')): n for n in tree.iter('control') if n.get('id')}
                self.assertLessEqual(VIEWS | {2, 3, 4, 9000}, controls.keys())
                for identity in VIEWS:
                    self.assertIsNotNone(controls[identity].find('viewtype'))
                    self.assertIsNone(controls[identity].find('content'))
                    self.assertEqual(controls[identity].findtext('onleft'), '9000')
                self.assertIn('resources/library.py,views', ET.tostring(tree, encoding='unicode'))

    def test_hub_library_routes_open_the_requested_directory(self):
        tree = ET.parse(ROOT / '1080i/Includes_Home.xml')
        routes = [value for node in tree.iter()
                  for value in [node.text or '', node.get('value', '')]
                  if re.match(r'ActivateWindow\((Videos|Music),', value)]
        self.assertEqual(len(routes), 6)
        for route in routes:
            with self.subTest(route=route):
                self.assertNotRegex(route, r',\s*return\s*\)')

    def test_genre_selection_uses_native_folder_paths_and_rejects_commands(self):
        from types import SimpleNamespace
        tree = ast.parse((ROOT / 'resources/library.py').read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'category')
        for window_id in (10025, 10502):
            for control in (700, 701):
                for path in ('videodb://movies/genres/2/', 'videodb://tvshows/genres/3/',
                             'musicdb://genres/4/', '', 'https://example.com/',
                             'videodb://movies/genres/2/),Quit()'):
                    with self.subTest(window=window_id, control=control, path=path):
                        actions, properties, focus = [], {}, []
                        window = SimpleNamespace(setProperty=properties.__setitem__,
                                                 getProperty=lambda key: '4212',
                                                 setFocusId=focus.append)
                        fields = {'FolderPath': path, 'FileNameAndPath': '', 'Label': 'Adventure'}
                        namespace = {'re': re, 'selected': lambda identity, field: fields[field],
                                     'xbmc': SimpleNamespace(executebuiltin=actions.append),
                                     'xbmcgui': SimpleNamespace(Window=lambda identity: window,
                                                               getCurrentWindowId=lambda: window_id)}
                        exec(compile(ast.Module(body=[function], type_ignores=[]), '<category>', 'exec'), namespace)
                        namespace['category'](control)
                        valid = path.startswith(('videodb://', 'musicdb://')) and ')' not in path
                        self.assertEqual(actions, ['Container.Update(' + path + ')'] if valid else [])
                        self.assertEqual(focus, [4212] if valid else [])
                        self.assertEqual(properties, {'Starlight.Library.Genre': 'Adventure'} if valid else {})

    def test_view_registry_matches_runtime_and_preview(self):
        from render_library import VIEW_IDS
        self.assertEqual(tuple(VIEW_IDS), tuple(sorted(VIEWS)))
        tree = ast.parse((ROOT / 'resources/library.py').read_text())
        registry = next(node for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(target, ast.Name) and target.id == 'VIEW_IDS'
                                for target in node.targets))
        self.assertEqual(eval(compile(ast.Expression(registry.value), '<registry>', 'eval')),
                         tuple(sorted(VIEWS)))

    def test_grid_masks_match_card_geometry(self):
        from PIL import Image
        expected = {'library/expanded_mask.png': (736, 312),
                    'library/row-poster_mask.png': (216, 312),
                    'library/row-landscape_mask.png': (416, 232),
                    'home_wide_mask.png': (416, 232)}
        for name, size in expected.items():
            with Image.open(ROOT / 'media' / name) as image:
                self.assertEqual(image.size, size, name)
            self.assertTrue(all(value % 4 == 0 for value in size))
        for filename in ('MyVideoNav.xml', 'MyMusicNav.xml', 'Home.xml', 'Custom_1101.xml'):
            tree = self.expanded(filename)
            parents = {child: node for node in tree.iter() for child in node}
            for texture in tree.iter('texture'):
                name = texture.get('diffuse')
                if name not in expected:
                    continue
                card = parents[texture]
                self.assertEqual(tuple(int(card.findtext(axis)) for axis in ('width', 'height')),
                                 expected[name], (filename, name))

    def test_native_search_lists_and_explicit_window(self):
        tree = self.expanded('Custom_1100.xml')
        controls = {int(n.get('id')): n for n in tree.iter('control') if n.get('id')}
        for identity in range(610, 621):
            self.assertIn('source=searchresults', controls[identity].findtext('content'))
            self.assertIn('window=11100', controls[identity].findtext('onclick'))
        source = (ROOT / 'resources/library.py').read_text()
        self.assertIn('window=11100', source)
        self.assertIn('Starlight.Search.Keyboard', source)
        self.assertIn('getText()', source)
        self.assertIn('search.select', ET.tostring(tree, encoding='unicode'))

    def test_search_shapes_share_width_and_heading_headroom(self):
        source = ET.parse(ROOT / '1080i/Includes_Library.xml')
        for name in ('SearchResultCard', 'SearchCompactCard'):
            include = source.find(f"include[@name='{name}']")
            widths = {node.get('value') for node in include.findall(".//include[@content='LibraryCard']/param[@name='width']")}
            self.assertEqual(len(widths), 1, name)
        page = ET.parse(ROOT / '1080i/Custom_1100.xml')
        for identity in range(1510, 1520):
            group = page.find(f".//control[@id='{identity}']")
            heading = group.find("control[@type='label']")
            row = group.find("control[@type='fixedlist']")
            self.assertGreaterEqual(int(row.findtext('top')) - int(heading.findtext('height')), 40)

    def test_provider_info_has_one_primary_and_one_cast_action(self):
        tree = self.expanded('DialogVideoInfo.xml')
        controls = {node.get('id'): node for node in tree.iter('control')}
        self.assertIn('418', controls)
        self.assertNotIn('409', controls)
        self.assertEqual([node.text for node in controls['250'].findall('onclick')],
                         ['RunScript(special://skin/resources/info.py,person)'])
        self.assertNotIn('def provider_initialize', (ROOT / 'resources/library.py').read_text())

    def test_discover_shares_home_board(self):
        raw = ET.parse(ROOT / '1080i/Custom_1101.xml')
        self.assertIsNotNone(raw.find(".//include[@content='HomeBoardWidget']"))
        source = (ROOT / '1080i/Includes_Home.xml').read_text()
        self.assertIn('name="onclick" default="RunScript(special://skin/resources/home.py,play,', source)
        self.assertIn('name="playable" default="true"', source)
        tree = self.expanded('Custom_1101.xml')
        self.assertIn('source=discover', ET.tostring(tree, encoding='unicode'))

    def test_provider_actions_reject_external_or_injected_urls(self):
        from library_content import provider_item
        good = 'plugin://plugin.video.plexkodiconnect/starlight/item?rating_key=abc123'
        self.assertEqual(provider_item(good), good)
        for value in ('https://example.com', good + '&other=x',
                      good + '%22%29', good.replace('item?', 'watchlist?'),
                      good.replace('abc123', '../escape'), ''):
            with self.subTest(value=value):
                self.assertIsNone(provider_item(value))

    def test_board_snapshot_partitions(self):
        from library_content import board_rows
        records = [{'file': str(n)} for n in range(8)]
        self.assertEqual(board_rows(records, 'feature'), records[:1])
        self.assertEqual(board_rows(records, 'tiles'), records[1:5])
        self.assertEqual(board_rows(records, 'row'), records[5:])
        self.assertEqual(board_rows([], 'tiles'), [])
        with self.assertRaises(ValueError):
            board_rows(records, 'invalid')

    def test_search_input_limits_and_characters(self):
        from library_content import edit_query
        self.assertEqual(edit_query('blade', 'space'), 'blade ')
        self.assertEqual(edit_query('blade', 'delete'), 'blad')
        self.assertEqual(edit_query('', 'delete'), '')
        self.assertEqual(edit_query('a' * 256, 'b'), 'a' * 256)
        with self.assertRaises(ValueError):
            edit_query('blade', 'RunPlugin(unsafe)')

    def test_new_window_resources_and_ids(self):
        fonts = {n.findtext('name') for n in ET.parse(ROOT / '1080i/Font.xml').iter('font')}
        for name in ('MyVideoNav.xml', 'MyMusicNav.xml', 'Custom_1100.xml', 'Custom_1101.xml'):
            tree = self.expanded(name)
            ids = [n.get('id') for n in tree.iter('control') if n.get('id')]
            self.assertEqual(len(ids), len(set(ids)), name)
            for node in tree.iter():
                text = node.text or ''
                self.assertNotIn('$PARAM[', text, name)
                self.assertFalse(any('$PARAM[' in value for value in node.attrib.values()), name)
                if node.tag == 'font':
                    self.assertIn(text, fonts)
                if 'texture' in node.tag and text and '$' not in text:
                    self.assertTrue((ROOT / 'media' / text).exists(), text)

    def test_no_new_prose_uses_ambiguous_pronoun(self):
        for name in ('resources/library.py', 'resources/lib/library_content.py', 'tools/render_library.py'):
            tree = ast.parse((ROOT / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
                    self.assertNotRegex(ast.get_docstring(node) or '', r'\b(?:it|its)\b')
