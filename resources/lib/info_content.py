"""Native video database queries for info pages and actor credits."""
from urllib.parse import quote

from home_content import next_episode, playback


def library_id(value):
    if not str(value).isascii() or not str(value).isdecimal() or int(value) <= 0:
        raise ValueError('A positive Kodi database ID is required')
    return int(value)


def landing_episode(rows):
    regular = [row for row in rows if row.get('season', 0) > 0]
    resumed = [row for row in regular if playback(row)['resume'] and not row.get('playcount')]
    return max(resumed, key=lambda row: row.get('lastplayed', ''), default=None) or next_episode(regular) or next(iter(regular), None)


def episode_items(showid, season, rpc):
    showid = library_id(showid)
    if not str(season).isascii() or not str(season).isdecimal():
        raise ValueError('A non-negative Kodi season number is required')
    result = rpc('Files.GetDirectory', {
        'directory': f'videodb://tvshows/titles/{showid}/{int(season)}/', 'media': 'video',
        'properties': ['title', 'art', 'resume', 'runtime', 'playcount', 'season', 'episode',
                       'showtitle', 'streamdetails', 'lastplayed'],
        'sort': {'method': 'episode', 'order': 'ascending'}})
    return [dict(row, media='episode', episodeid=row['id']) for row in result.get('files', [])
            if row.get('type') == 'episode' and row.get('id', 0) > 0]


def person_items(name, rpc):
    if not name.strip():
        return []
    rows = []
    for media in ('movie', 'tvshow'):
        result = rpc('Files.GetDirectory', {
            'directory': f'videodb://{media}s/titles/?actor=' + quote(name, safe=''), 'media': 'video',
            'properties': ['title', 'year', 'art', 'cast'],
            'sort': {'method': 'year', 'order': 'descending'}})
        for row in result.get('files', []):
            if row.get('id', 0) <= 0 or row.get('type') != media:
                continue
            role = next((actor.get('role', '') for actor in row.get('cast', [])
                         if actor.get('name', '').casefold() == name.casefold()), '')
            rows.append(dict(row, media=media, role=role, **{media + 'id': row['id']}))
    return sorted(rows, key=lambda row: (row.get('year', 0), row.get('title', '')), reverse=True)
