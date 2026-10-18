"""Expose native library widgets through the skin's own content provider."""
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from home_content import blurred_art, duration_label, library_items, partition, playback, rpc_result


def rpc(method, params):
    return rpc_result(json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}))))


def listing():
    handle = int(sys.argv[1])
    args = parse_qs(sys.argv[2].lstrip('?'))
    source = args.get('source', ['continue'])[0]
    part = args.get('part', ['row'])[0]
    if source not in ('continue', 'next', 'movies', 'episodes') or part not in ('feature', 'tiles', 'row'):
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    home = xbmcgui.Window(10000)
    key = 'Starlight.Source.' + source
    cached = json.loads(home.getProperty(key) or '{}')
    # Both board halves share a short-lived snapshot; playback invalidates the snapshot.
    if time.time() - cached.get('time', 0) < 15:
        rows = cached['rows']
    else:
        try:
            rows = library_items(source, rpc)
        except RuntimeError as error:
            xbmc.log(str(error), xbmc.LOGERROR)
            xbmcplugin.endOfDirectory(handle, succeeded=False)
            return
        home.setProperty(key, json.dumps({'time': time.time(), 'rows': rows}))
    addon = xbmcaddon.Addon('skin.starlight')
    for row in partition(rows, part):
        state = playback(row)
        title = row.get('title') or row.get('label', '')
        label = row.get('showtitle') if row['media'] == 'episode' and source in ('continue', 'next') else title
        item = xbmcgui.ListItem(label=label or title, path=row['file'])
        item.setProperty('IsPlayable', 'true')
        art = row.get('art', {})
        art['fanart'] = art.get('fanart') or art.get('tvshow.fanart') or 'special://skin/fanart.jpg'
        if row['media'] == 'episode':
            art['landscape'] = art.get('thumb') or art.get('tvshow.landscape') or art['fanart']
        item.setArt(art)
        item.setProperty('Starlight.Media', row['media'])
        tag = item.getVideoInfoTag()
        tag.setMediaType(row['media'])
        tag.setDbId(row[row['media'] + 'id'])
        tag.setTitle(row.get('title') or row.get('label', ''))
        tag.setYear(row.get('year', 0))
        tag.setMpaa(row.get('mpaa', ''))
        tag.setDuration(row.get('runtime', 0))
        for stream in row.get('streamdetails', {}).get('video', []):
            tag.addVideoStream(xbmc.VideoStreamDetail(
                width=stream.get('width', 0), height=stream.get('height', 0),
                aspect=stream.get('aspect', 0.0), duration=stream.get('duration', 0),
                codec=stream.get('codec', ''), hdrtype=stream.get('hdrtype', '')))
        tag.setPlaycount(row.get('playcount', 0))
        tag.setResumePoint(state['resume'], row.get('resume', {}).get('total') or row.get('runtime', 0))
        if row['media'] == 'episode':
            tag.setTvShowTitle(row.get('showtitle', ''))
            tag.setSeason(row.get('season', 0))
            tag.setEpisode(row.get('episode', 0))
        item.setProperty('Starlight.Blurred', blurred_art(art.get('fanart') or art.get('tvshow.fanart', '')))
        item.setProperty('Starlight.Progress', str(state['progress']))
        item.setProperty('Starlight.Resume', 'true' if state['resume'] else '')
        item.setProperty('Starlight.Action', addon.getLocalizedString(31016 if state['resume'] else 31017))
        templates = (addon.getLocalizedString(31039), addon.getLocalizedString(31019))
        duration = duration_label(state['minutes'], *templates)
        item.setProperty('Starlight.Duration', duration_label(row.get('runtime', 0) / 60, *templates))
        item.setProperty('Starlight.Time', duration)
        detail = addon.getLocalizedString(31018) % duration if state['resume'] else duration
        detail = addon.getLocalizedString(31038) % (row['season'], row['episode'], detail) if row['media'] == 'episode' else detail
        item.setProperty('Starlight.Detail', detail)
        item.setProperty('Starlight.Next', 'true' if row.get('next') else '')
        xbmcplugin.addDirectoryItem(handle, row['file'], item, isFolder=False)
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'play':
        media, dbid = sys.argv[2:]
        if media in ('movie', 'episode') and dbid.isdecimal() and int(dbid) > 0:
            for source in ('continue', 'next', 'movies', 'episodes'):
                xbmcgui.Window(10000).clearProperty('Starlight.Source.' + source)
            rpc('Player.Open', {'item': {media + 'id': int(dbid)}, 'options': {'resume': True}})
    else:
        listing()
