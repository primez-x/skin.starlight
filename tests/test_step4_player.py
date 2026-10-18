"""Player failures: missing native windows, stale queue positions, video queues,
empty queues, repeat wrap, invalid selection, absent helper, paused spectrum,
unpadded countdowns, moved stage slots, and malformed player navigation.
Kodi input, spectrum rendering, auto-width labels and account actions need a box.
"""
import importlib.util
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'resources/lib'))
WINDOWS = ('VideoOSD.xml', 'DialogSeekBar.xml', 'MusicVisualisation.xml',
           'MusicOSD.xml', 'DialogFullScreenInfo.xml', 'Custom_1104.xml',
           'Custom_1105.xml', 'DialogPlayerProcessInfo.xml', 'VideoOSDBookmarks.xml', 'MyPlaylist.xml')


class PlayerWindowTests(unittest.TestCase):
    def test_windows_expand_without_duplicate_ids_or_unresolved_params(self):
        from render_home import HomePreview
        preview = HomePreview(ROOT)
        for name in WINDOWS:
            with self.subTest(window=name):
                path = ROOT / '1080i' / name
                self.assertTrue(path.exists(), name + ' is missing')
                tree = preview.expand(ET.parse(path).getroot())
                ids = [n.get('id') for n in tree.iter('control') if n.get('id')]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertNotIn('$PARAM[', ET.tostring(tree).decode())

    def test_native_album_fallback_and_bookmark_list_exist(self):
        self.assertTrue((ROOT / 'media/DefaultAlbumCover.png').exists(), 'Native audio fallback is missing')
        path = ROOT / '1080i/VideoOSDBookmarks.xml'
        self.assertTrue(path.exists(), 'Native chapter and bookmark dialog is missing')
        tree = ET.parse(path)
        self.assertEqual(tree.find(".//control[@id='11']").get('type'), 'list')

    def test_native_visualisation_and_helper_degradation(self):
        path = ROOT / '1080i/MusicVisualisation.xml'
        self.assertTrue(path.exists(), 'Music now playing is missing')
        from render_home import HomePreview
        tree = HomePreview(ROOT).expand(ET.parse(path).getroot())
        self.assertEqual(tree.find(".//control[@id='2']").get('type'), 'visualisation')
        source = (ROOT / '1080i/Includes_Player.xml').read_text()
        self.assertIn('Skin.HasSetting(Player.Visualiser.Disabled)', ET.tostring(tree).decode())
        self.assertIn('Player.Paused', ET.tostring(tree).decode())
        self.assertIn('System.HasAddon(script.starlight)', source)
        self.assertIn('Spotify.CurrentTrackLiked', source)
        self.assertIn('Starlight.NextTrack.Progress', source)
        addon = ET.parse(ROOT / 'addon.xml')
        self.assertNotIn('script.starlight', [n.get('addon') for n in addon.iter('import')])

    def test_queue_has_two_script_owned_rows_and_safe_return(self):
        path = ROOT / '1080i/Custom_1104.xml'
        self.assertTrue(path.exists(), 'Queue view is missing')
        from render_home import HomePreview
        tree = HomePreview(ROOT).expand(ET.parse(path).getroot())
        for identity in (510, 520):
            row = tree.find(f".//control[@id='{identity}']")
            self.assertIsNotNone(row)
            self.assertIsNone(row.find('content'))
            self.assertEqual(row.findtext('onup'), 'ActivateWindow(visualisation)')
            self.assertEqual(row.findtext('onback'), 'ActivateWindow(visualisation)')
            self.assertIn('queue-play', row.findtext('onclick'))
            self.assertIn('Starlight.Action', ET.tostring(row.find('focusedlayout')).decode())


class QueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'resources/lib/player_content.py'
        if not path.exists():
            raise AssertionError('Player queue adapter is missing')
        spec = importlib.util.spec_from_file_location('player_content', path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def snapshot_rpc(self, method, params):
        if method == 'Player.GetActivePlayers': return [{'playerid': 0, 'type': 'audio'}]
        if method == 'Player.GetProperties': return {'playlistid': 0, 'position': 2, 'repeat': 'off', 'shuffled': True}
        if method == 'Playlist.GetItems':
            return {'items': [{'file': f'file-{n}', 'title': f'Track {n}', 'artist': ['Artist'],
                               'art': {'thumb': f'art-{n}'}} for n in range(5)], 'limits': {'total': 5}}
        raise AssertionError(method)

    def test_partition_preserves_actual_queue_order_and_positions(self):
        snapshot = self.module.queue_snapshot(self.snapshot_rpc)
        self.assertEqual([r['position'] for r in snapshot['next']], [3, 4])
        self.assertEqual([r['position'] for r in snapshot['played']], [1, 0])
        self.assertEqual(snapshot['total'], 5)

    def test_repeat_all_wraps_in_native_queue_order(self):
        def rpc(method, params):
            result = self.snapshot_rpc(method, params)
            if method == 'Player.GetProperties': result.update(position=4, repeat='all')
            return result
        snapshot = self.module.queue_snapshot(rpc)
        self.assertEqual([r['position'] for r in snapshot['next']], [0, 1, 2, 3])

    def test_large_queues_page_without_silent_truncation(self):
        def rpc(method, params):
            if method == 'Playlist.GetItems':
                start, end = params['limits']['start'], min(1330, params['limits']['end'])
                return {'items': [{'file': f'file-{n}'} for n in range(start,end)], 'limits': {'total':1330}}
            return self.snapshot_rpc(method, params)
        snapshot = self.module.queue_snapshot(rpc)
        self.assertEqual(len(snapshot['next']), 1327)
        self.assertEqual(snapshot['next'][-1]['position'], 1329)

    def test_no_audio_or_queue_has_no_fabricated_rows(self):
        self.assertIsNone(self.module.queue_snapshot(lambda *a: []))
        self.assertIsNone(self.module.queue_snapshot(lambda *a: [{'type': 'video', 'playerid': 1}]))
        def rpc(method, params):
            if method == 'Player.GetProperties': return {'playlistid': -1, 'position': -1}
            return self.snapshot_rpc(method, params)
        self.assertIsNone(self.module.queue_snapshot(rpc))

    def test_stale_or_invalid_selection_cannot_play_another_record(self):
        calls = []
        def rpc(method, params):
            calls.append((method, params))
            if method == 'Playlist.GetItems': return {'items': [{'file': 'replacement'}]}
            return self.snapshot_rpc(method, params)
        self.assertFalse(self.module.play_queue_item('3', 'file-3', rpc))
        self.assertNotIn('Player.Open', [m for m,p in calls])
        for position in ('-1', '../3', '3,4', '1.5', ''):
            with self.subTest(position=position):
                self.assertFalse(self.module.play_queue_item(position, 'file-3', rpc))

    def test_matching_selection_plays_native_position_without_queue_mutation(self):
        calls = []
        def rpc(method, params):
            calls.append((method, params))
            if method == 'Playlist.GetItems': return {'items': [{'file': 'file-3'}]}
            if method == 'Player.Open': return 'OK'
            return self.snapshot_rpc(method, params)
        self.assertTrue(self.module.play_queue_item('3', 'file-3', rpc))
        self.assertEqual(calls[-1], ('Player.Open', {'item': {'playlistid': 0, 'position': 3}}))
        self.assertFalse(any(m in ('Playlist.Clear', 'Playlist.Add', 'Playlist.Remove') for m,p in calls))

    def test_closed_queue_request_cannot_replace_a_newer_queue(self):
        properties = {}
        resets = []
        control = SimpleNamespace(size=lambda:0, reset=lambda:resets.append(True),
                                  addItems=lambda rows:None, selectItem=lambda index:None)
        window = SimpleNamespace(setProperty=lambda key,value:properties.__setitem__(key,value),
                                 getProperty=lambda key:properties.get(key,''),
                                 clearProperty=lambda key:properties.pop(key,None),
                                 getControl=lambda identity:control, setFocusId=lambda identity:None)
        def rpc(method, params):
            if method == 'Playlist.GetItems': properties['Starlight.Queue.Request'] = 'newer-request'
            return self.snapshot_rpc(method, params)
        class Monitor:
            def waitForAbort(self, seconds): return True
        class Item:
            def __init__(self, **kwargs): pass
            def setArt(self, art): pass
            def setProperty(self, key, value): pass
        xbmc = SimpleNamespace(Monitor=Monitor, getCondVisibility=lambda expression:True,
                               getLocalizedString=lambda identity:'Play')
        fake_home = SimpleNamespace(rpc=rpc, cached_blurred_art=lambda art:art)
        spec = importlib.util.spec_from_file_location('step4_adapter', ROOT / 'resources/player.py')
        adapter = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'xbmc':xbmc, 'xbmcgui':SimpleNamespace(Window=lambda identity:window,ListItem=Item), 'home':fake_home}):
            spec.loader.exec_module(adapter)
            adapter.monitor_queue()
        self.assertEqual(resets, [])

    def test_pill_grows_and_remains_centred_with_a_width_cap(self):
        self.assertEqual(self.module.pill_geometry(300), (738, 444))
        self.assertEqual(self.module.pill_geometry(900), (438, 1044))
        self.assertEqual(self.module.pill_geometry(4000), (388, 1144))


if __name__ == '__main__':
    unittest.main()
