"""Native Kodi library selection shared by the two board containers."""
import math
from urllib.parse import quote, unquote


def continue_items(movies, episodes):
    return sorted([dict(row, media='movie') for row in movies] +
                  [dict(row, media='episode') for row in episodes],
                  key=lambda row: (row.get('lastplayed', ''), row.get('label', '')),
                  reverse=True)[:20]


def partition(rows, part):
    if part == 'feature':
        return rows[:1]
    if part == 'tiles':
        return rows[1:5]
    if part == 'row':
        return rows
    raise ValueError('Unknown board partition')


def next_episode(rows):
    candidates = [row for row in rows if row.get('season', 0) > 0
                  and not row.get('playcount', 0)]
    return min(candidates, key=lambda row: (row['season'], row['episode']), default=None)


def playback(row):
    duration = max(0, row.get('resume', {}).get('total') or row.get('runtime', 0))
    position = min(duration, max(0, row.get('resume', {}).get('position', 0)))
    return {'progress': round(position * 100 / duration) if duration else 0,
            'minutes': math.ceil((duration - position) / 60), 'resume': position}


def duration_label(minutes, hours='%d h %d m', short='%d m'):
    total = max(0, math.ceil(minutes))
    return hours % divmod(total, 60) if total >= 60 else short % total


def blurred_art(art):
    # Kodi's image cache downsamples to 16x9; the GUI's linear filter softens the result.
    path = art or 'special://skin/fanart.jpg'
    if path.startswith('image://'):
        path = unquote(path[8:].split('/')[0])
    return 'image://' + quote(path, safe='') + '/?width=16&height=9'


def rpc_result(response):
    if 'error' in response:
        raise RuntimeError('Kodi library query failed: ' + response['error'].get('message', 'Unknown error'))
    return response['result']


PROPERTIES = ['title', 'file', 'art', 'resume', 'runtime', 'year', 'mpaa', 'lastplayed', 'playcount', 'streamdetails']
EPISODE_PROPERTIES = [p for p in PROPERTIES if p not in ('year', 'mpaa')] + ['showtitle', 'season', 'episode', 'tvshowid']


def library_items(source, rpc):
    """Read the synced library. No Plex server request or section ID is required."""
    if source == 'continue':
        params = {'filter': {'field': 'inprogress', 'operator': 'true', 'value': ''},
                  'sort': {'method': 'lastplayed', 'order': 'descending'}, 'limits': {'end': 20}}
        movies = rpc('VideoLibrary.GetMovies', dict(params, properties=PROPERTIES)).get('movies', [])
        episodes = rpc('VideoLibrary.GetEpisodes', dict(params, properties=EPISODE_PROPERTIES)).get('episodes', [])
        return continue_items(movies, episodes)
    if source in ('movies', 'episodes'):
        media = 'movie' if source == 'movies' else 'episode'
        method = 'VideoLibrary.GetRecentlyAddedMovies' if media == 'movie' else 'VideoLibrary.GetRecentlyAddedEpisodes'
        props = PROPERTIES if media == 'movie' else EPISODE_PROPERTIES
        result = rpc(method, {'properties': props, 'limits': {'end': 20}})
        return [dict(row, media=media) for row in result.get(source, [])]
    if source != 'next':
        raise ValueError('Unknown Home source')
    shows = rpc('VideoLibrary.GetTVShows', {
        'properties': ['lastplayed', 'watchedepisodes', 'episode'],
        'filter': {'field': 'inprogress', 'operator': 'true', 'value': ''},
        'sort': {'method': 'lastplayed', 'order': 'descending'}, 'limits': {'end': 50}}).get('tvshows', [])
    rows = []
    for show in shows:
        result = rpc('VideoLibrary.GetEpisodes', {
            'tvshowid': show['tvshowid'], 'properties': EPISODE_PROPERTIES,
            'filter': {'and': [{'field': 'playcount', 'operator': 'is', 'value': '0'},
                               {'field': 'season', 'operator': 'greaterthan', 'value': '0'}]},
            'sort': {'method': 'episode', 'order': 'ascending'}, 'limits': {'end': 1}})
        row = next_episode(result.get('episodes', []))
        if row:
            rows.append(dict(row, media='episode', next=True))
        if len(rows) == 20:
            break
    return rows
