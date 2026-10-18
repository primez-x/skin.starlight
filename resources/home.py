"""Expose native library widgets through the skin's own content provider."""
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from home_content import blurred_art, duration_label, library_items, partition, playback, rpc_result
from info_content import episode_items, person_items


def rpc(method, params):
    return rpc_result(json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}))))


def cached_blurred_art(art):
    # Kodi's first large-image load returns the decoded source before disk resize.
    # Bind the resized cache file so the first backdrop also uses 16x9 pixels.
    url = blurred_art(art)
    query = {'properties': ['cachedurl'],
             'filter': {'field': 'url', 'operator': 'is', 'value': url}}
    rows = rpc('Textures.GetTextures', query).get('textures', [])
    if not rows:
        image = xbmcvfs.File(url)
        image.close()
        rows = rpc('Textures.GetTextures', query).get('textures', [])
    return 'special://masterprofile/Thumbnails/' + rows[0]['cachedurl'] if rows else 'special://skin/media/background_void.png'


def listing():
    handle = int(sys.argv[1])
    args = parse_qs(sys.argv[2].lstrip('?'))
    source = args.get('source', ['continue'])[0]
    part = args.get('part', ['row'])[0]
    if source in ('infoepisodes', 'person', 'cast', 'seasons'):
        info_listing(handle, source, args)
        return
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
    add_videos(handle, partition(rows, part), source)
    xbmcplugin.setContent(handle, 'videos')
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def add_videos(handle, rows, source):
    for row in rows:
        state = playback(row)
        title = row.get('title') or row.get('label', '')
        label = row.get('showtitle') if row['media'] == 'episode' and source in ('continue', 'next') else title
        item = xbmcgui.ListItem(label=label or title, path=row.get('file', ''))
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
        item.setProperty('Starlight.Blurred', cached_blurred_art(art.get('fanart') or art.get('tvshow.fanart', '')))
        item.setProperty('Starlight.Progress', str(state['progress']))
        item.setProperty('Starlight.Resume', 'true' if state['resume'] else '')
        item.setProperty('Starlight.Action', xbmc.getLocalizedString(31016 if state['resume'] else 31017))
        templates = (xbmc.getLocalizedString(31039), xbmc.getLocalizedString(31019))
        duration = duration_label(state['minutes'], *templates)
        if source == 'infoepisodes' and not state['resume']:
            duration = duration_label(row.get('runtime', 0) // 60, *templates)
        item.setProperty('Starlight.Duration', duration_label(row.get('runtime', 0) / 60, *templates))
        item.setProperty('Starlight.Time', duration)
        detail = xbmc.getLocalizedString(31018) % duration if state['resume'] else duration
        detail = xbmc.getLocalizedString(31038) % (row['season'], row['episode'], detail) if row['media'] == 'episode' else detail
        item.setProperty('Starlight.Detail', detail)
        item.setProperty('Starlight.Next', 'true' if row.get('next') else '')
        role_year = ' · '.join(str(value) for value in (row.get('role'), row.get('year')) if value)
        item.setProperty('Starlight.RoleYear', role_year)
        if source == 'infoepisodes':
            item.setLabel(f"{row.get('episode', 0)}. {title}")
            item.setProperty('Starlight.Detail', detail.split(' · ', 1)[-1])
        xbmcplugin.addDirectoryItem(handle, row.get('file', ''), item, isFolder=row['media'] == 'tvshow')


def info_listing(handle, source, args):
    try:
        if source == 'person':
            rows = person_items(xbmcgui.Window(11103).getProperty('Starlight.Person.Name'), rpc)
            add_videos(handle, rows, source)
        elif source == 'infoepisodes':
            showid = args.get('showid', [''])[0]
            season = args.get('season', [''])[0]
            rows = episode_items(showid, season, rpc) if showid and season else []
            nextid = xbmcgui.Window(12003).getProperty('Starlight.Info.NextID')
            add_videos(handle, [dict(row, next=str(row['episodeid']) == nextid) for row in rows], source)
        else:
            info = xbmcgui.Window(12003)
            records = json.loads(info.getProperty('Starlight.Info.' + source) or '[]')
            for record in records:
                item = xbmcgui.ListItem(label=record['label'], label2=record.get('role', ''))
                item.setArt({'thumb': record.get('thumbnail') or 'special://skin/media/person_placeholder.png'})
                item.setProperty('Starlight.Season', str(record.get('season', '')))
                xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)
        xbmcplugin.setContent(handle, 'videos' if source == 'infoepisodes' else 'files')
    except (RuntimeError, ValueError) as error:
        xbmc.log('Starlight info: ' + str(error), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def clear_home_cache():
    for source in ('continue', 'next', 'movies', 'episodes'):
        xbmcgui.Window(10000).clearProperty('Starlight.Source.' + source)


def play(media, dbid):
    if media in ('movie', 'episode') and dbid.isdecimal() and int(dbid) > 0:
        clear_home_cache()
        rpc('Player.Open', {'item': {media + 'id': int(dbid)}, 'options': {'resume': True}})


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'play':
        play(*sys.argv[2:])
    else:
        listing()
