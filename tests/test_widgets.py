"""Library failures: mixed order, empty data, duplicate board cards, specials,
watched episodes, zero duration, missing artwork, malformed source and RPC errors.
Duration failures: minute-only output, hour boundaries, negatives and fractional minutes.
Quality failure: movie or episode queries omit the native video stream details.
Exercise selection and presentation before the Kodi adapter creates controls.
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'resources/lib/home_content.py'
        if not path.exists():
            raise AssertionError('Native Home content provider is missing')
        spec = importlib.util.spec_from_file_location('home_content', path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_continue_merges_media_by_lastplayed(self):
        movies = [{'movieid': 1, 'lastplayed': '2026-10-15', 'file': 'one.mkv'}]
        episodes = [{'episodeid': 2, 'lastplayed': '2026-10-17', 'file': 'two.mkv'}]
        rows = self.module.continue_items(movies, episodes)
        self.assertEqual([r['file'] for r in rows], ['two.mkv', 'one.mkv'])
        self.assertEqual(self.module.continue_items([], []), [])

    def test_board_partitions_without_duplicates(self):
        rows = [{'movieid': n} for n in range(8)]
        self.assertEqual(self.module.partition(rows, 'feature'), [{'movieid': 0}])
        self.assertEqual(self.module.partition(rows, 'tiles'), [{'movieid': n} for n in range(1, 5)])
        self.assertEqual(self.module.partition([], 'feature'), [])
        with self.assertRaises(ValueError):
            self.module.partition(rows, '../invalid')

    def test_next_episode_skips_specials_and_watched(self):
        rows = [{'season': 0, 'episode': 1, 'playcount': 0},
                {'season': 1, 'episode': 1, 'playcount': 1},
                {'season': 2, 'episode': 1, 'playcount': 0},
                {'season': 1, 'episode': 2, 'playcount': 0}]
        self.assertEqual(self.module.next_episode(rows), rows[3])
        self.assertIsNone(self.module.next_episode(rows[:2]))

    def test_progress_handles_zero_and_clamps_resume(self):
        self.assertEqual(self.module.playback({'runtime': 7200, 'resume': {'position': 1800}}),
                         {'progress': 25, 'minutes': 90, 'resume': 1800})
        self.assertEqual(self.module.playback({'runtime': 0}),
                         {'progress': 0, 'minutes': 0, 'resume': 0})
        self.assertEqual(self.module.playback({'runtime': 60, 'resume': {'position': 100}})['progress'], 100)

    def test_blurred_art_encodes_paths_and_falls_back(self):
        self.assertEqual(self.module.blurred_art(''),
                         'image://special%3A%2F%2Fskin%2Ffanart.jpg/?width=16&height=9')
        self.assertEqual(self.module.blurred_art('image://https%3A%2F%2Fexample.com%2Fa.jpg/'),
                         'image://https%3A%2F%2Fexample.com%2Fa.jpg/?width=16&height=9')

    def test_duration_uses_hours_and_minutes_at_boundaries(self):
        self.assertTrue(callable(getattr(self.module, 'duration_label', None)),
                        'Duration formatter is missing')
        for minutes, expected in [(-1, '0 m'), (0, '0 m'), (.1, '1 m'),
                                  (48, '48 m'), (60, '1 h 0 m'),
                                  (114, '1 h 54 m'), (117, '1 h 57 m'),
                                  (6000, '100 h 0 m')]:
            with self.subTest(minutes=minutes):
                self.assertEqual(self.module.duration_label(minutes), expected)
        self.assertEqual(self.module.duration_label(114, '%d hours %d minutes', '%d minutes'),
                         '1 hours 54 minutes')

    def test_all_video_queries_request_stream_details(self):
        for source in ('continue', 'movies', 'episodes', 'next'):
            calls = []

            def rpc(method, params):
                calls.append((method, params))
                return {'tvshows': [{'tvshowid': 7}]} if method == 'VideoLibrary.GetTVShows' else {}

            self.module.library_items(source, rpc)
            for method, params in calls:
                if method != 'VideoLibrary.GetTVShows':
                    with self.subTest(source=source, method=method):
                        self.assertIn('streamdetails', params['properties'])

    def test_rpc_errors_fail_the_listing(self):
        with self.assertRaises(RuntimeError):
            self.module.rpc_result({'error': {'message': 'Invalid params'}})
        self.assertEqual(self.module.rpc_result({'result': {}}), {})

    def test_nextup_filters_started_shows_before_limit(self):
        def rpc(method, params):
            if method == 'VideoLibrary.GetTVShows':
                self.assertEqual(params.get('filter'),
                                 {'field': 'inprogress', 'operator': 'true', 'value': ''})
                return {'tvshows': [{'tvshowid': 7, 'episode': 8, 'watchedepisodes': 0}]}
            self.assertEqual(method, 'VideoLibrary.GetEpisodes')
            self.assertEqual(params['tvshowid'], 7)
            return {'episodes': [{'episodeid': 12, 'season': 1, 'episode': 1,
                                  'playcount': 0, 'file': 'first.mkv'}]}
        rows = self.module.library_items('next', rpc)
        self.assertEqual([(r['episodeid'], r['media'], r['next']) for r in rows],
                         [(12, 'episode', True)])
