"""Connect native libraries, ranked search lists, and the shared Discover Board."""
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from home import rpc, cached_blurred_art
from home_content import duration_label, playback
from library_content import HUBS, PKC, board_rows, edit_query, provider_item
from skin_xml import expand, card_rect

SEARCH = 11100
DISCOVER = 11101
SOURCES = ('top', 'movies', 'tvshows', 'episodes', 'music', 'spotify',
           'people', 'collections', 'genres', 'plex')
VIEW_IDS = tuple(range(4200, 4226))


def selected(control, field):
    return xbmc.getInfoLabel(f'Container({control}).ListItem.{field}')


def helper(command, *arguments):
    # User query text travels only through the documented Home property.
    xbmc.executebuiltin(','.join(('RunScript(script.starlight', command, 'window=11100', *arguments)) + ')')


def search_monitor():
    window = xbmcgui.Window(SEARCH)
    home = xbmcgui.Window(10000)
    token = str(time.monotonic_ns())
    home.setProperty('Starlight.Search.Monitor', token)
    monitor = xbmc.Monitor()
    previous = recent = results = None
    previous_art = None
    while xbmcgui.getCurrentWindowId() == SEARCH and home.getProperty('Starlight.Search.Monitor') == token:
        if home.getProperty('Starlight.Search.Keyboard') == 'true' and xbmc.getCondVisibility('Window.IsVisible(10103)'):
            keyboard_window = xbmcgui.Window(10103)
            query = keyboard_window.getControl(312).getText()[:256]
            home.setProperty('Starlight.Search.Query', query)
        query = home.getProperty('Starlight.Search.Query')[:256]
        if query != previous:
            previous = query
            if xbmc.getCondVisibility('System.HasAddon(script.starlight)'):
                helper('search', 'control=699', 'plex=true')
            else:
                home.setProperty('Starlight.Search.Errors', 'helper')
        current_results = home.getProperty('Starlight.Search.Results')
        if current_results != results:
            results = current_results
            window.setProperty('Starlight.Search.Revision', str(time.monotonic_ns()))
        current_recent = home.getProperty('Starlight.Search.Recent')
        if current_recent != recent:
            recent = current_recent
            window.setProperty('Starlight.Search.RecentRevision', str(time.monotonic_ns()))
        control = int(window.getProperty('Starlight.Search.Container') or 610)
        art = selected(control, 'Art(fanart)') or selected(control, 'Art(thumb)')
        if art != previous_art:
            previous_art = art
            blurred = cached_blurred_art(art)
            if xbmcgui.getCurrentWindowId() != SEARCH or home.getProperty('Starlight.Search.Monitor') != token:
                break
            window.setProperty('Starlight.Library.Blurred', blurred)
        if monitor.waitForAbort(.05):
            break
    if home.getProperty('Starlight.Search.Monitor') == token:
        home.clearProperty('Starlight.Search.Monitor')


def search_listing(handle, args):
    """Read the helper cache through a native provider so Kodi dispatches clicks."""
    source = args.get('row', ['top'])[0]
    if source not in (*SOURCES, 'recent'):
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    home = xbmcgui.Window(10000)
    if source == 'recent':
        for query in json.loads(home.getProperty('Starlight.Search.Recent') or '[]')[:10]:
            item = xbmcgui.ListItem(label=query)
            xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)
    else:
        rows = json.loads(home.getProperty('Starlight.Search.Results') or '{}').get(source, [])
        shapes = {'movie': 'poster', 'tvshow': 'poster', 'episode': 'landscape', 'song': 'square',
                  'album': 'square', 'artist': 'circle', 'person': 'circle', 'set': 'poster', 'genre': 'square'}
        for record in rows[:20 if source == 'top' else 100]:
            kind = record['type']
            label = {'library': 'Library', 'spotify': 'Spotify', 'plex': 'Plex'}[record['source']]
            artist = record.get('artist') or ''
            artist = ' / '.join(artist) if isinstance(artist, list) else artist
            media_label = {'tvshow': 'TV show', 'set': 'Collection'}.get(kind, kind.title())
            detail = ' · '.join(value for value in (label, media_label, artist) if value)
            path = record.get('path') or 'plugin://skin.starlight/?' + urlencode(
                {'source': 'searchresults', 'row': source, 'record': record['id']})
            item = xbmcgui.ListItem(label=record['title'], label2=detail, path=path)
            item.setArt(record.get('art') or {})
            item.setProperty('Starlight.Search.Record', json.dumps(record, ensure_ascii=False))
            item.setProperty('Starlight.Search.Shape', shapes[kind])
            item.setProperty('Starlight.Search.Type', kind)
            item.setProperty('IsPlayable', 'false')
            xbmcplugin.addDirectoryItem(handle, item.getPath(), item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


def search_keyboard():
    home = xbmcgui.Window(10000)
    if home.getProperty('Starlight.Search.Keyboard'):
        return
    window = xbmcgui.Window(SEARCH)
    window.setProperty('Starlight.Search.Source', 'top')
    window.getControl(600).selectItem(0)
    home.setProperty('Starlight.Search.Keyboard', 'true')
    keyboard = xbmc.Keyboard(home.getProperty('Starlight.Search.Query'), '')
    try:
        keyboard.doModal()
        home.setProperty('Starlight.Search.Query', keyboard.getText()[:256])
    finally:
        home.clearProperty('Starlight.Search.Keyboard')
        window = xbmcgui.Window(SEARCH)
        if window.getProperty('Starlight.Search.ReturnResults'):
            window.clearProperty('Starlight.Search.ReturnResults')
            target = 610 if int(home.getProperty('Starlight.Search.Count.top') or 0) else 30
            window.setFocusId(target)
        else:
            window.setFocusId(30)


def keyboard_ready():
    # Keep the native window alive while Python holds the borrowed edit control.
    keyboard_window = xbmcgui.Window(10103)
    if xbmcgui.Window(10000).getProperty('Starlight.Search.Keyboard') == 'true':
        field = keyboard_window.getControl(312)
        field.setPosition(196, 46)
        field.setWidth(1424)
    else:
        field = keyboard_window.getControl(312)
        field.setPosition(196, 154)
        field.setWidth(1644)


def keyboard_results():
    if xbmcgui.Window(10000).getProperty('Starlight.Search.Keyboard') == 'true':
        xbmcgui.Window(SEARCH).setProperty('Starlight.Search.ReturnResults', 'true')
        xbmc.executebuiltin('SendClick(10103,300)')
    else:
        xbmc.executebuiltin('SetFocus(312)')


def search_key(key=None):
    home = xbmcgui.Window(10000)
    key = key or selected(40, 'Property(Key)')
    home.setProperty('Starlight.Search.Query', edit_query(home.getProperty('Starlight.Search.Query'), key))


def search_recent():
    # Script-owned recent records contain plain text; no query enters an action string.
    query = selected(50, 'Label')
    xbmcgui.Window(10000).setProperty('Starlight.Search.Query', query[:256])


def search_source():
    source = selected(600, 'Property(Source)')
    if source in SOURCES:
        window = xbmcgui.Window(SEARCH)
        window.setProperty('Starlight.Search.Source', source)
        target = 610 if source == 'top' else 620
        if int(xbmcgui.Window(10000).getProperty('Starlight.Search.Count.' + source) or 0):
            window.setFocusId(target)


def discover_listing(handle, args):
    hub = args.get('hub', ['trending'])[0]
    part = args.get('part', ['feature'])[0]
    if hub not in HUBS or part not in ('feature', 'tiles', 'row'):
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    home = xbmcgui.Window(10000)
    key = 'Starlight.Discover.Snapshot.' + hub
    try:
        snapshot = discover_snapshot(hub, home, key)
        for record in board_rows(snapshot['records'], part):
            properties = {name.casefold(): value for name, value in record.get('customproperties', {}).items()}
            path = provider_item(properties.get('starlight.infopath', ''))
            if not path:
                continue
            item = xbmcgui.ListItem(label=record.get('title') or record.get('label', ''), path=path)
            art = record.get('art', {})
            item.setArt(art)
            item.setProperty('IsPlayable', 'false')
            item.setProperty('Starlight.InfoPath', path)
            item.setProperty('Starlight.Source', 'Plex')
            item.setProperty('Starlight.ProviderKey', properties.get('starlight.providerkey', ''))
            item.setProperty('Starlight.Duration', duration_label(record.get('runtime', 0) / 60,
                             xbmc.getLocalizedString(31039), xbmc.getLocalizedString(31019)) if record.get('runtime', 0) > 0 else '')
            tag = item.getVideoInfoTag()
            tag.setTitle(record.get('title') or record.get('label', ''))
            tag.setYear(record.get('year', 0))
            tag.setGenres(record.get('genre', []))
            tag.setPlot(record.get('plot', ''))
            tag.setDuration(record.get('runtime', 0))
            xbmcplugin.addDirectoryItem(handle, path, item, isFolder=False)
        xbmcplugin.setContent(handle, 'videos')
        xbmcplugin.endOfDirectory(handle, cacheToDisc=False)
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        xbmc.log('Starlight Discover: ' + str(error), xbmc.LOGERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def discover_snapshot(hub, home, key):
    """Serialize the two Board loads across Kodi's separate plugin interpreters."""
    lock = Path(xbmcvfs.translatePath('special://temp/')) / ('starlight-discover-' + hub + '.lock')
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 60
    while True:
        snapshot = json.loads(home.getProperty(key) or '{}')
        if time.time() - snapshot.get('time', 0) < 30:
            return snapshot
        try:
            descriptor = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            break
        except FileExistsError:
            # A process crash leaves no active owner; bound that recovery to an old lock.
            try:
                if time.time() - lock.stat().st_mtime > 180:
                    lock.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline or monitor.waitForAbort(.1):
                raise RuntimeError('Discover source did not finish')
    try:
        snapshot = json.loads(home.getProperty(key) or '{}')
        if time.time() - snapshot.get('time', 0) >= 30:
            records = rpc('Files.GetDirectory', {'directory': PKC + 'discover?hub=' + hub,
                          'media': 'video', 'properties': ['title', 'art', 'year', 'runtime', 'genre', 'plot', 'customproperties']}).get('files', [])
            snapshot = {'time': time.time(), 'records': records}
            home.setProperty(key, json.dumps(snapshot))
        return snapshot
    finally:
        lock.unlink(missing_ok=True)


def discover_open():
    control = xbmcgui.Window(DISCOVER).getFocusId()
    if control not in (510, 511, 512):
        return
    path = provider_item(selected(control, 'Property(Starlight.InfoPath)'))
    if path:
        # PKC resolves exact library identity or opens provider-only native information.
        xbmc.executebuiltin('RunPlugin(' + path + ')')


def discover_tab():
    hub = selected(600, 'Property(Hub)')
    if hub in HUBS:
        xbmcgui.Window(DISCOVER).setProperty('Starlight.Discover.Hub', hub)
        xbmcgui.Window(DISCOVER).setFocusId(510)


def views():
    # Read labels from the shared XML so the menu and native view names cannot drift.
    root = ET.parse(Path(__file__).resolve().parents[1] / '1080i/Includes_Library.xml')
    views = root.find("include[@name='LibraryViews']/definition")
    names = {}
    for node in views.findall('control'):
        view = node.find('viewtype')
        if view is not None:
            identity = int(node.get('id'))
            string_id = re.fullmatch(r'\$LOCALIZE\[(\d+)\]', view.get('label')).group(1)
            names[identity] = xbmc.getLocalizedString(int(string_id))
    window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    current = window.getProperty('Starlight.Library.Container')
    index = xbmcgui.Dialog().select(xbmc.getLocalizedString(31431), [names[identity] for identity in VIEW_IDS],
                                   preselect=VIEW_IDS.index(int(current)) if current.isdecimal() and int(current) in VIEW_IDS else 0)
    if index >= 0:
        identity = VIEW_IDS[index]
        window.setProperty('Starlight.Library.Container', str(identity))
        xbmc.executebuiltin(f'Container.SetViewMode({identity})')
        window.setFocusId(identity)


def category(control):
    path = selected(control, 'FolderPath')
    # Native directory URLs contain only database paths and numeric query values.
    if re.fullmatch(r'(?:videodb|musicdb)://[A-Za-z0-9_/?=&.%-]+', path):
        window = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        window.setProperty('Starlight.Library.Genre', selected(control, 'Label'))
        xbmc.executebuiltin('Container.Update(' + path + ')')
        window.setFocusId(int(window.getProperty('Starlight.Library.Container') or 4212))


def page_monitor(kind):
    window_id = xbmcgui.getCurrentWindowId()
    window = xbmcgui.Window(window_id)
    token = str(time.monotonic_ns())
    window.setProperty('Starlight.Library.Monitor', token)
    monitor = xbmc.Monitor()
    previous = ''
    previous_record = None
    expected = (DISCOVER,) if kind == 'discover' else (10025, 10502)
    while window_id in expected and xbmcgui.getCurrentWindowId() == window_id and window.getProperty('Starlight.Library.Monitor') == token:
        focused = window.getFocusId()
        if focused in VIEW_IDS and kind != 'discover':
            window.setProperty('Starlight.Library.Container', str(focused))
        control = focused if kind == 'discover' and focused in (510, 511, 512) else 510 if kind == 'discover' else int(window.getProperty('Starlight.Library.Container') or 4212)
        art = selected(control, 'Art(fanart)') or selected(control, 'Art(thumb)')
        if art != previous:
            previous = art
            window.setProperty('Starlight.Library.Blurred', cached_blurred_art(art))
        record = (control, selected(control, 'DBTYPE'), selected(control, 'DBID'))
        if record != previous_record and kind == 'library':
            previous_record = record
            window.clearProperty('Starlight.Library.Time')
            media, rawid = record[1:]
            if media in ('episode', 'song') and rawid.isdecimal() and int(rawid) > 0:
                try:
                    if media == 'episode':
                        details = rpc('VideoLibrary.GetEpisodeDetails', {'episodeid': int(rawid),
                                      'properties': ['runtime', 'resume']})['episodedetails']
                        state = playback(details)
                        duration = duration_label(state['minutes'], xbmc.getLocalizedString(31039), xbmc.getLocalizedString(31019))
                        value = xbmc.getLocalizedString(31018) % duration if state['resume'] else duration
                    else:
                        details = rpc('AudioLibrary.GetSongDetails', {'songid': int(rawid),
                                      'properties': ['duration']})['songdetails']
                        value = duration_label(details.get('duration', 0) / 60,
                                               xbmc.getLocalizedString(31039), xbmc.getLocalizedString(31019))
                    window.setProperty('Starlight.Library.Time', value)
                except (RuntimeError, KeyError) as error:
                    xbmc.log('Starlight library duration: ' + str(error), xbmc.LOGWARNING)
        if monitor.waitForAbort(.15):
            break
    if window.getProperty('Starlight.Library.Monitor') == token:
        window.clearProperty('Starlight.Library.Monitor')



def search_results():
    window = xbmcgui.Window(SEARCH)
    source = window.getProperty('Starlight.Search.Source') or 'top'
    home = xbmcgui.Window(10000)
    if not home.getProperty('Starlight.Search.Query'):
        target = 50 if int(xbmc.getInfoLabel('Container(50).NumItems') or 0) else 30
    elif source != 'top':
        target = 620 if int(home.getProperty('Starlight.Search.Count.' + source) or 0) else 600
    else:
        target = next((610 + index for index, name in enumerate(SOURCES)
                       if int(home.getProperty('Starlight.Search.Count.' + name) or 0)), 30)
    window.setFocusId(target)


def library_context_anchor(window, window_id, focused):
    """Compute the selected card rectangle from native cursor and scroll metrics."""
    filenames = {10025: 'MyVideoNav.xml', 10502: 'MyMusicNav.xml',
                 SEARCH: 'Custom_1100.xml', DISCOVER: 'Custom_1101.xml'}
    allowed = set(VIEW_IDS) if window_id in (10025, 10502) else set(range(610, 621)) if window_id == SEARCH else {510, 511, 512}
    if window_id not in filenames or focused not in allowed:
        return None
    directory = Path(__file__).resolve().parents[1] / '1080i'
    includes, constants = {}, {}
    for path in directory.glob('Includes*.xml'):
        root = ET.parse(path)
        includes.update({node.get('name'): node for node in root.iter('include') if node.get('name')})
        constants.update({node.get('name'): node.text for node in root.iter('constant')})

    def condition(expression):
        expression = re.sub(r'Control.HasFocus\((\d+)\)',
                            lambda match: 'true' if int(match[1]) == focused else 'false', expression)
        expression = expression.replace('Window.Property(', f'Window({window_id}).Property(')
        return xbmc.getCondVisibility(expression)

    tree = expand(ET.parse(directory / filenames[window_id]).getroot(), includes, condition)
    cursor = int(window.getControl(6502).getLabel() or 0)
    if window_id == SEARCH:
        shape = window.getControl(6503).getLabel()
        container = tree.find(f".//control[@id='{focused}']")
        layouts = container.findall('focusedlayout')
        layout = next((node for node in layouts if condition(node.get('condition', 'true'))), None)
        for node in layouts:
            if node is not layout:
                container.remove(node)
        if layout is not None:
            chosen = next((node for node in layout.findall('control')
                           if node.findtext('visible', '').endswith(',' + shape + ')')), None)
            if chosen is not None:
                layout[:] = list(chosen)
                layout[:] = [node for node in layout if node.tag == 'control']
    scroll = int(window.getControl(6501).getLabel().split('/')[0] or 0)
    return card_rect(tree, focused, cursor, scroll, constants, condition)


if __name__ == '__main__':
    actions = {'search-monitor': search_monitor, 'search-keyboard': search_keyboard,
               'search-results': search_results,
               'keyboard-ready': keyboard_ready, 'keyboard-results': keyboard_results,
               'search-key': search_key, 'search-recent': search_recent,
               'search-source': search_source, 'discover-tab': discover_tab,
               'discover-open': discover_open, 'views': views,
               'library-monitor': lambda: page_monitor('library'),
               'discover-monitor': lambda: page_monitor('discover')}
    try:
        if len(sys.argv) == 2 and sys.argv[1] in actions:
            actions[sys.argv[1]]()
        elif len(sys.argv) == 3 and sys.argv[1] == 'search-key' and sys.argv[2] in ('space', 'delete'):
            search_key(sys.argv[2])
        elif len(sys.argv) == 3 and sys.argv[1] == 'category' and sys.argv[2] in ('700', '701'):
            category(int(sys.argv[2]))
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        xbmc.log('Starlight library: ' + str(error), xbmc.LOGERROR)
