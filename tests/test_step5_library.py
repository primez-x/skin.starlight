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
VIEWS = set(range(500, 509)) | set(range(510, 516)) | {517, 518} | set(range(520, 525)) | {526, 527, 528, 529}


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
