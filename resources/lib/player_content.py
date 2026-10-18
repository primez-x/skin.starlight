"""Native audio queue snapshots and checked position playback."""


def audio_state(rpc):
    active = rpc('Player.GetActivePlayers', {})
    player = next((p for p in active if p.get('type') == 'audio'), None)
    if player is None:
        return None
    state = rpc('Player.GetProperties', {'playerid': player['playerid'],
                'properties': ['playlistid', 'position', 'repeat', 'shuffled']})
    return state if state.get('playlistid') == 0 and state.get('position', -1) >= 0 else None


def queue_snapshot(rpc):
    state = audio_state(rpc)
    if state is None:
        return None
    position = state['position']
    rows = []
    total = 1
    while len(rows) < total:
        start = len(rows)
        result = rpc('Playlist.GetItems', {'playlistid': 0, 'limits': {'start': start, 'end': start + 200},
                     'properties': ['title', 'artist', 'album', 'art', 'file', 'duration']})
        page = result.get('items', [])
        total = result.get('limits', {}).get('total', start + len(page))
        if not page and start < total:
            raise RuntimeError('The audio queue changed during refresh')
        rows.extend(dict(row, position=start + index) for index, row in enumerate(page))
    if audio_state(rpc) != state:
        raise RuntimeError('The audio queue changed during refresh')
    upcoming = [r for r in rows if r['position'] > position]
    if state.get('repeat') == 'all':
        upcoming += [r for r in rows if r['position'] < position]
    return {'next': upcoming,
            'played': list(reversed([r for r in rows if r['position'] < position])),
            'position': position, 'total': total,
            'repeat': state.get('repeat', 'off'), 'shuffled': state.get('shuffled', False)}


def play_queue_item(position, expected_file, rpc):
    if not isinstance(position, str) or not position.isdecimal() or not expected_file:
        return False
    if audio_state(rpc) is None:
        return False
    index = int(position)
    result = rpc('Playlist.GetItems', {'playlistid': 0, 'properties': ['file'],
                 'limits': {'start': index, 'end': index + 1}}).get('items', [])
    if len(result) != 1 or result[0].get('file') != expected_file:
        return False
    rpc('Player.Open', {'item': {'playlistid': 0, 'position': index}})
    return True


def pill_geometry(text_width):
    width = max(300, min(1000, int(text_width))) + 144
    return (1920 - width) // 2, width
