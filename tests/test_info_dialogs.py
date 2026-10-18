"""Window failures: absent native IDs, wrong control types, duplicate IDs,
unsafe default choice, missing keyboard columns, and unresolved resources.
Data failures: invalid IDs, empty libraries, specials, completed shows,
encoded actor names, mixed credits, missing roles, and invalid provider paths.
"""
import importlib.util
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'resources/lib'))

# Kodi 21.3-Omega source, https://github.com/xbmc/xbmc/blob/21.3-Omega/xbmc/
# video/dialogs/GUIDialogVideoInfo.cpp:74-88,474-535; control 5 is optional.
# dialogs/GUIDialogContextMenu.cpp:42-45,114-174.
# dialogs/GUIDialogSelect.cpp:19-25,336-389.
# dialogs/GUIDialogBoxBase.cpp:18-20; GUIDialogBoxBase.h:16-23.
# dialogs/GUIDialogYesNo.cpp:18,72-76; GUIDialogOK.cpp:18,84-89;
# dialogs/GUIDialogProgress.cpp:23,148-153. All three load DialogConfirm.xml.
# dialogs/GUIDialogKaiToast.cpp:19-21,106-138 (402 must be a fadelabel).
# dialogs/GUIDialogExtendedProgressBar.cpp:18-20,147-153.
# dialogs/GUIDialogKeyboardGeneric.cpp:45-66,139-168,549-560.
# dialogs/GUIDialogTextViewer.cpp:23-24,74-91.
# dialogs/GUIDialogBusy.cpp:110-114; GUIDialogBusyNoCancel.cpp:15-20;
# dialogs/GUIDialogVolumeBar.cpp:22-25. No native control IDs for busy/volume.
WINDOW_IDS = {
    'DialogVideoInfo.xml': {3: 'image', 4: 'textbox', 6: 'button', 7: 'button',
                            8: 'button', 9: 'button', 10: 'button', 11: 'button',
                            12: 'button', 13: 'button', 14: 'button', 15: 'button', 50: 'list'},
    'DialogContextMenu.xml': {999: 'image', 996: 'grouplist', 1000: 'button'},
    'DialogSelect.xml': {1: 'label', 2: 'label', 3: 'list', 6: 'list',
                         5: 'button', 7: 'button', 8: 'button'},
    'DialogConfirm.xml': {1: 'label', 9: 'textbox', 10: 'button', 11: 'button',
                          12: 'button', 20: 'progress'},
    'DialogNotification.xml': {400: 'image', 401: 'label', 402: 'fadelabel'},
    'DialogExtendedProgressBar.xml': {30: 'label', 31: 'label', 32: 'progress'},
    'DialogVolumeBar.xml': {},
    'DialogBusy.xml': {},
    'DialogKeyboard.xml': {**{n: 'button' for n in range(100, 180)},
                           8: 'button', 32: 'button', 300: 'button', 301: 'button',
                           302: 'button', 303: 'button', 304: 'button',
                           305: 'button', 306: 'button', 308: 'button',
                           309: 'button', 310: 'button', 311: 'label', 312: 'edit',
                           313: 'label', 314: 'label'},
    'DialogTextViewer.xml': {1: 'label', 5: 'textbox'},
    'Custom_1103.xml': {700: 'fixedlist', 710: 'fixedlist'},
}


class WindowTests(unittest.TestCase):
    def test_native_lists_use_info_labels(self):
        # Python ControlList reads only records added through the Python wrapper.
        source = (ROOT / 'resources/info.py').read_text()
        self.assertNotRegex(source, r'\.(?:size|getListItem|getSelectedItem)\(')

    def test_native_window_names_resolve(self):
        # xbmc/input/WindowTranslator.cpp:79,82,121,126,162 (21.3-Omega).
        names = {'volumebar','notification','movieinformation','textviewer','extendedprogressdialog'}
        paths = [ROOT / 'resources/info.py', *(ROOT / '1080i').glob('Dialog*.xml')]
        for path in paths:
            for name in re.findall(r'(?:Window.IsVisible|Dialog.Close)\(([a-zA-Z0-9_]+)\)', path.read_text()):
                with self.subTest(path=path.name, name=name):
                    self.assertTrue(name.isdecimal() or name in names, name)

    def test_native_notification_icons_exist(self):
        # GUIDialogKaiToast.cpp:126-138 selects these names when no icon is supplied.
        for name in ('DefaultIconInfo.png', 'DefaultIconWarning.png', 'DefaultIconError.png'):
            self.assertTrue((ROOT / 'media' / name).is_file(), name)

    def test_native_window_contracts(self):
        from render_home import HomePreview
        preview = HomePreview(ROOT)
        for name, required in WINDOW_IDS.items():
            with self.subTest(window=name):
                path = ROOT / '1080i' / name
                self.assertTrue(path.is_file(), name + ' is missing')
                tree = preview.expand(ET.parse(path).getroot())
                controls = [node for node in tree.iter('control') if node.get('id')]
                ids = [int(node.get('id')) for node in controls]
                self.assertEqual(len(ids), len(set(ids)), name + ' has duplicate IDs')
                actual = {int(node.get('id')): node.get('type') for node in controls}
                for control, kind in required.items():
                    self.assertEqual(actual.get(control), kind, f'{name}: {control}')

    def test_native_cast_and_plot_can_coexist(self):
        path = ROOT / '1080i/DialogVideoInfo.xml'
        self.assertTrue(path.exists(), 'Video info is missing')
        tree = ET.parse(path)
        self.assertIsNone(tree.find(".//control[@id='5']"),
                          'Native toggle 5 hides cast while plot shows')

    def test_expanded_window_resources_resolve(self):
        from render_home import HomePreview
        preview = HomePreview(ROOT)
        fonts = {node.findtext('name') for node in ET.parse(ROOT / '1080i/Font.xml').iter('font')}
        for name in WINDOW_IDS:
            path = ROOT / '1080i' / name
            self.assertTrue(path.exists(), name + ' is missing')
            tree = preview.expand(ET.parse(path).getroot())
            controls = {node.get('id') for node in tree.iter('control') if node.get('id')}
            for node in tree.iter():
                value = (node.text or '').strip()
                with self.subTest(window=name, element=node.tag, value=value):
                    self.assertNotIn('$PARAM[', value)
                    self.assertFalse(any('$PARAM[' in value for value in node.attrib.values()))
                    if node.tag == 'font':
                        self.assertIn(value, fonts)
                    if node.tag == 'pagecontrol' and value.isdecimal():
                        self.assertIn(value, controls, 'A native page control is missing')
                    # GUIAction.cpp:95-105 accepts integer navigation targets.
                    # Dynamic targets must use a SetFocus action.
                    if node.tag in ('onup','ondown','onleft','onright'):
                        self.assertFalse(value.startswith('$'), 'Dynamic navigation needs SetFocus')
                    if 'texture' in node.tag and value and '$' not in value:
                        asset = ROOT / value[15:] if value.startswith('special://skin/') else ROOT / 'media' / value
                        self.assertTrue(asset.is_file(), str(asset))
                    diffuse = node.get('diffuse', '')
                    if diffuse and '$' not in diffuse:
                        self.assertTrue((ROOT / 'media' / diffuse).is_file(), diffuse)

    def test_confirmation_default_is_safe(self):
        path = ROOT / '1080i/DialogConfirm.xml'
        self.assertTrue(path.exists(), 'Confirmation sheet is missing')
        self.assertEqual(ET.parse(path).findtext('defaultcontrol'), '10')


class InfoContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'resources/lib/info_content.py'
        if not path.exists():
            raise AssertionError('Info library provider is missing')
        spec = importlib.util.spec_from_file_location('info_content', path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_ids_reject_non_library_inputs(self):
        for value in ('', '0', '-1', '../7', '7&actor=x', '1.0'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.module.library_id(value)
        self.assertEqual(self.module.library_id('23'), 23)

    def test_show_lands_on_resume_then_next_regular_episode(self):
        rows = [{'episodeid': 1, 'season': 0, 'episode': 1, 'playcount': 0},
                {'episodeid': 2, 'season': 1, 'episode': 1, 'playcount': 1},
                {'episodeid': 3, 'season': 1, 'episode': 2, 'playcount': 0},
                {'episodeid': 4, 'season': 2, 'episode': 1, 'playcount': 0,
                 'runtime': 2400, 'resume': {'position': 1200}, 'lastplayed': '2026-10-16'}]
        self.assertEqual(self.module.landing_episode(rows)['episodeid'], 4)
        self.assertEqual(self.module.landing_episode(rows[:3])['episodeid'], 3)
        self.assertIsNone(self.module.landing_episode([]))
        self.assertEqual(self.module.landing_episode(rows[1:2])['episodeid'], 2)

    def test_episode_directory_uses_native_videodb_and_enriches_time(self):
        def rpc(method, params):
            self.assertEqual(method, 'Files.GetDirectory')
            self.assertEqual(params['directory'], 'videodb://tvshows/titles/7/4/')
            return {'files': [{'id': 33, 'type': 'episode', 'file': 'videodb://tvshows/titles/7/4/33',
                               'title': 'Retrograde', 'season': 4, 'episode': 4, 'runtime': 2580,
                               'playcount': 0, 'resume': {'position': 1320}, 'art': {}}]}
        rows = self.module.episode_items('7', '4', rpc)
        self.assertEqual([(r['episodeid'], r['media'], r['runtime']) for r in rows], [(33, 'episode', 2580)])
        with self.assertRaises(ValueError):
            self.module.episode_items('7', '-2', rpc)

    def test_person_filters_encode_actor_and_merge_newest_first(self):
        def rpc(method, params):
            self.assertEqual(method, 'Files.GetDirectory')
            directory = params['directory']
            self.assertIn('?actor=O%27Brien%20%26%20Sons', directory)
            if directory.startswith('videodb://movies/'):
                return {'files': [{'id': 12, 'type': 'movie', 'title': 'Older', 'year': 1982,
                                   'cast': [{'name': "O'Brien & Sons", 'role': 'Deckard'}]}]}
            return {'files': [{'id': 13, 'type': 'tvshow', 'title': 'Newer', 'year': 2025, 'cast': []}]}
        rows = self.module.person_items("O'Brien & Sons", rpc)
        self.assertEqual([(r['title'], r['role'], r['media']) for r in rows],
                         [('Newer', '', 'tvshow'), ('Older', 'Deckard', 'movie')])
        self.assertEqual(self.module.person_items('', rpc), [])

    def test_empty_directories_stay_empty(self):
        self.assertEqual(self.module.episode_items('7', '0', lambda *a: {}), [])
        self.assertEqual(self.module.person_items('Nobody', lambda *a: {}), [])


class CardAnchorTests(unittest.TestCase):
    def test_person_anchor_follows_top_navigation_scale(self):
        from render_window import WindowPreview
        from skin_xml import card_rect
        preview = WindowPreview(ROOT, 'person', {'Hub.Navigation':'top_centre'})
        self.assertEqual(card_rect(preview.home,700,0,0,preview.constants,preview.condition),
                         (187,652,179,268))

    def test_home_anchors_follow_layout_and_scroll(self):
        from render_home import HomePreview
        path = ROOT / 'resources/lib/skin_xml.py'
        self.assertTrue(path.exists(), 'Shared XML geometry is missing')
        spec = importlib.util.spec_from_file_location('skin_xml', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cases = [({}, 510, 0, 0, (152,212,968,545)),
                 ({}, 511, 3, 0, (1488,511,369,208)),
                 ({}, 522, 0, 300, (188,568,176,264)),
                 ({'Home.Continue.Layout':'hero'}, 512, 0, 0, (175,556,451,255)),
                 ({'Hub.Navigation':'top_centre'}, 510, 0, 0, (36,212,968,545))]
        for settings, control, position, scroll, expected in cases:
            preview = HomePreview(ROOT, settings=settings)
            preview.focus = control
            with self.subTest(settings=settings, control=control):
                self.assertEqual(module.card_rect(preview.home, control, position, scroll,
                                                      preview.constants, preview.condition), expected)


if __name__ == '__main__':
    unittest.main()
