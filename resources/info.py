"""Info actions use Kodi database IDs. Person enrichment stays provider-owned."""
import json
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET

import xbmc
import xbmcgui

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from home import rpc, play, clear_home_cache, cached_blurred_art
from home_content import duration_label, playback
from info_content import landing_episode, library_id
from skin_xml import expand, card_rect

INFO = 12003
PERSON = 11103


def initialize():
    window = xbmcgui.Window(INFO)
    request = str(time.monotonic_ns())
    window.setProperty('Starlight.Info.Request', request)
    # Read the native dialog record before focus enters a secondary container.
    media = xbmc.getInfoLabel('ListItem.DBTYPE')
    rawid = xbmc.getInfoLabel('ListItem.DBID')
    for key in ('Ready', 'Error', 'More', 'cast', 'seasons', 'ShowID', 'Season', 'NextID',
                'Resume', 'Time', 'Duration', 'Progress', 'Media', 'DBID', 'Watched', 'SeasonCount'):
        window.clearProperty('Starlight.Info.' + key)
    window.setProperty('Starlight.Info.Blurred', cached_blurred_art(xbmc.getInfoLabel('ListItem.Art(fanart)')))
    window.setProperty('Starlight.Info.Hub', xbmcgui.Window(10000).getProperty('Starlight.Hub') or
                       ('tv' if media in ('tvshow', 'season', 'episode') else 'movies'))
    if media not in ('movie', 'episode', 'tvshow', 'season'):
        window.setProperty('Starlight.Info.Ready', 'true')
        return
    try:
        dbid = library_id(rawid)
        window.setProperty('Starlight.Info.Media', media)
        window.setProperty('Starlight.Info.DBID', str(dbid))
        if media == 'season':
            details = rpc('VideoLibrary.GetSeasonDetails', {'seasonid': dbid,
                          'properties': ['season', 'tvshowid']})['seasondetails']
            showid, season = details['tvshowid'], details['season']
            detail = rpc('VideoLibrary.GetTVShowDetails', {'tvshowid': showid,
                         'properties': ['cast', 'art', 'playcount']})['tvshowdetails']
        else:
            fields = ['cast', 'art', 'playcount']
            if media in ('movie', 'episode'):
                fields += ['runtime', 'resume']
            detail = rpc('VideoLibrary.Get' + {'movie': 'Movie', 'episode': 'Episode',
                         'tvshow': 'TVShow'}[media] + 'Details',
                         {media + 'id': dbid, 'properties': fields})[media + 'details']
        if window.getProperty('Starlight.Info.Request') != request:
            return
        window.setProperty('Starlight.Info.cast', json.dumps([
            dict(actor, label=actor['name']) for actor in detail.get('cast', [])]))
        window.setProperty('Starlight.Info.Watched', 'true' if detail.get('playcount') else '')
        state = playback(detail)
        templates = xbmc.getLocalizedString(31039), xbmc.getLocalizedString(31019)
        for key, value in {'Resume': 'true' if state['resume'] else '',
                           'Progress': str(state['progress']),
                           'Time': duration_label(state['minutes'], *templates),
                           'Duration': duration_label(detail.get('runtime', 0) / 60, *templates)}.items():
            window.setProperty('Starlight.Info.' + key, value)
        for control in (9018, 9019):
            window.getControl(control).setPercent(state['progress'])
        if media in ('tvshow', 'season'):
            showid = showid if media == 'season' else dbid
            episodes = rpc('VideoLibrary.GetEpisodes', {'tvshowid': showid,
                           'properties': ['season', 'episode', 'playcount', 'resume', 'runtime', 'lastplayed'],
                           'sort': {'method': 'episode', 'order': 'ascending'}}).get('episodes', [])
            if window.getProperty('Starlight.Info.Request') != request:
                return
            target = landing_episode(episodes if media == 'tvshow' else
                                     [row for row in episodes if row['season'] == season])
            season = target['season'] if target else season if media == 'season' else 1
            seasons = sorted({row['season'] for row in episodes})
            window.setProperty('Starlight.Info.SeasonCount', str(sum(number > 0 for number in seasons)))
            window.setProperty('Starlight.Info.seasons', json.dumps([
                {'label': xbmc.getLocalizedString(31040) % number, 'season': number} for number in seasons]))
            window.setProperty('Starlight.Info.ShowID', str(showid))
            window.setProperty('Starlight.Info.Season', str(season))
            window.setProperty('Starlight.Info.NextID', str(target['episodeid']) if target else '')
        window.setProperty('Starlight.Info.Ready', 'true')
        if media in ('tvshow', 'season'):
            land(window, 550, target['episodeid'] if target else None, request)
        else:
            land(window, 9 if state['resume'] else 8, request=request)
    except (RuntimeError, ValueError, KeyError) as error:
        if window.getProperty('Starlight.Info.Request') != request:
            return
        xbmc.log('Starlight info: ' + str(error), xbmc.LOGERROR)
        window.setProperty('Starlight.Info.Error', 'true')
        window.setProperty('Starlight.Info.Ready', 'true')
        land(window, 8, request=request)


def land(window, control, target=None, request=None):
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 5
    while xbmc.getCondVisibility('Window.IsVisible(movieinformation)') and time.monotonic() < deadline:
        if request and window.getProperty('Starlight.Info.Request') != request:
            return
        if control != 550:
            window.setFocusId(control)
            return
        listing = window.getControl(control)
        count = int(xbmc.getInfoLabel(f'Container({control}).NumItems') or 0)
        if count:
            tabs = window.getControl(560)
            season = window.getProperty('Starlight.Info.Season')
            for index in range(int(xbmc.getInfoLabel('Container(560).NumItems') or 0)):
                if xbmc.getInfoLabel(f'Container(560).ListItemAbsolute({index}).Property(Starlight.Season)') == season:
                    tabs.selectItem(index)
                    break
            index = next((n for n in range(count)
                          if xbmc.getInfoLabel(f'Container({control}).ListItemAbsolute({n}).DBID') == str(target)), 0)
            listing.selectItem(index)
            window.setFocusId(control)
            return
        if monitor.waitForAbort(.05):
            return
    if xbmc.getCondVisibility('Window.IsVisible(movieinformation)'):
        window.setFocusId(560)


def open_person():
    person = xbmcgui.Window(PERSON)
    info = xbmcgui.Window(INFO)
    name = xbmc.getInfoLabel('Container(250).ListItem.Label')
    if not name:
        return
    for key in ('Name', 'Thumb', 'Meta', 'Biography', 'CreditsPath', 'ImagesPath', 'ProviderKey'):
        person.clearProperty('Starlight.Person.' + key)
    person.setProperty('Starlight.Person.Name', name)
    person.setProperty('Starlight.Person.Thumb', xbmc.getInfoLabel('Container(250).ListItem.Art(thumb)'))
    person.setProperty('Starlight.Person.Meta', xbmc.getLocalizedString(31042))
    person.setProperty('Starlight.Person.Blurred', info.getProperty('Starlight.Info.Blurred'))
    person.setProperty('Starlight.Person.Tab', 'library')
    person.setProperty('Starlight.Person.Request', str(time.monotonic_ns()))
    person.setProperty('Starlight.Person.Hub', info.getProperty('Starlight.Info.Hub'))
    # Close the modal info dialog before opening a normal custom window.
    xbmc.executebuiltin('Dialog.Close(movieinformation)')
    xbmc.executebuiltin('ActivateWindow(11103)')


def open_credit():
    media = xbmc.getInfoLabel('Container(700).ListItem.DBTYPE')
    if media not in ('movie', 'tvshow'):
        return
    dbid = library_id(xbmc.getInfoLabel('Container(700).ListItem.DBID'))
    detail = rpc('VideoLibrary.Get' + ('Movie' if media == 'movie' else 'TVShow') + 'Details',
                 {media + 'id': dbid, 'properties': ['title', 'file', 'art']})[media + 'details']
    path = f'videodb://tvshows/titles/{dbid}/' if media == 'tvshow' else detail['file']
    selected = xbmcgui.ListItem(label=detail['title'], path=path)
    selected.setArt(detail.get('art', {}))
    tag = selected.getVideoInfoTag()
    tag.setMediaType(media)
    tag.setDbId(dbid)
    xbmcgui.Dialog().info(selected)


def watched():
    window = xbmcgui.Window(INFO)
    media = window.getProperty('Starlight.Info.Media')
    dbid = library_id(window.getProperty('Starlight.Info.DBID'))
    value = 0 if window.getProperty('Starlight.Info.Watched') else 1
    if media in ('tvshow', 'season'):
        rows = rpc('VideoLibrary.GetEpisodes', {
            'tvshowid': library_id(window.getProperty('Starlight.Info.ShowID')),
            'properties': ['season']}).get('episodes', [])
        for row in rows:
            if media == 'tvshow' or str(row['season']) == window.getProperty('Starlight.Info.Season'):
                rpc('VideoLibrary.SetEpisodeDetails', {'episodeid': row['episodeid'], 'playcount': value})
    elif media in ('movie', 'episode'):
        rpc('VideoLibrary.Set' + ('Movie' if media == 'movie' else 'Episode') + 'Details',
            {media + 'id': dbid, 'playcount': value})
    window.setProperty('Starlight.Info.Watched', 'true' if value else '')
    window.setProperty('Starlight.Info.Revision', str(time.monotonic_ns()))
    clear_home_cache()


def play_episode():
    dbid = library_id(xbmc.getInfoLabel('Container(550).ListItem.DBID'))
    xbmc.executebuiltin('Dialog.Close(movieinformation)', wait=True)
    play('episode', str(dbid))


def shuffle():
    showid = library_id(xbmcgui.Window(INFO).getProperty('Starlight.Info.ShowID'))
    rpc('Playlist.Clear', {'playlistid': 1})
    rpc('Playlist.Add', {'playlistid': 1, 'item': {
        'directory': f'videodb://tvshows/titles/{showid}/', 'recursive': True, 'media': 'video'}})
    xbmc.executebuiltin('Dialog.Close(movieinformation)')
    rpc('Player.Open', {'item': {'playlistid': 1}, 'options': {'shuffled': True}})


def show_more():
    window = xbmcgui.Window(INFO)
    window.setProperty('Starlight.Info.More', 'true')
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 2
    while xbmc.getCondVisibility('Window.IsVisible(movieinformation)') and time.monotonic() < deadline:
        for control in (6, 7, 10, 11, 12, 13, 14, 15, 411):
            if xbmc.getCondVisibility(f'Control.IsVisible({control}) + Control.IsEnabled({control})'):
                window.setFocusId(control)
                return
        if monitor.waitForAbort(.05):
            return


def show_cast():
    window = xbmcgui.Window(INFO)
    window.clearProperty('Starlight.Info.More')
    window.setProperty('Starlight.Info.Cast', 'true')
    monitor = xbmc.Monitor()
    deadline = time.monotonic() + 3
    while xbmc.getCondVisibility('Window.IsVisible(movieinformation)') and time.monotonic() < deadline:
        if xbmc.getCondVisibility('Control.IsVisible(250)'):
            window.setFocusId(250 if int(xbmc.getInfoLabel('Container(250).NumItems') or 0) else 400)
            return
        if monitor.waitForAbort(.05):
            return


def context():
    if xbmcgui.getCurrentWindowDialogId() != 10106:
        return
    dialog = xbmcgui.Window(10106)
    underlying = xbmcgui.Window(xbmcgui.getCurrentWindowId())
    # A page may supply the focused card's screen rectangle before a native menu.
    raw = underlying.getProperty('Starlight.Context.CardRect')
    underlying.clearProperty('Starlight.Context.CardRect')
    count = 0
    while count < 100 and xbmc.getInfoLabel(f'Control.GetLabel({1001 + count})'):
        count += 1
    height = min(704, max(62, count * 64)) + 28
    width = 760
    x, y = (1920 - width) // 2, (1080 - height) // 2
    modal = any(xbmc.getCondVisibility(f'Window.IsVisible({window_id})')
                for window_id in (10100, 10101, 10103, 10147, 12000, 12002, INFO))
    if not raw and not modal:
        rect = context_anchor(underlying)
        raw = ','.join(map(str, rect)) if rect else ''
    if raw:
        try:
            left, top, cardwidth, cardheight = [int(value) for value in raw.split(',')]
            if min(left, top, cardwidth, cardheight) < 0 or not cardwidth or not cardheight:
                raise ValueError('Invalid card rectangle')
            width = 480
            x = left + cardwidth + 28 if left + cardwidth + 28 + width <= 1880 else left - width - 28
            x = min(1880 - width, max(40, x))
            y = min(1040 - height, max(40, top + (cardheight - height) // 2))
            dialog.setProperty('Starlight.Context.Card', 'true')
        except ValueError:
            dialog.clearProperty('Starlight.Context.Card')
    else:
        dialog.clearProperty('Starlight.Context.Card')
    dialog.getControl(997).setPosition(x, y)
    dialog.getControl(997).setWidth(width)
    dialog.getControl(998).setWidth(width)
    dialog.getControl(998).setHeight(height)
    for index in range(count):
        dialog.getControl(1001 + index).setWidth(width - 28)
    dialog.setProperty('Starlight.Context.Ready', 'true')


def context_anchor(window):
    focused = window.getFocusId()
    window_id = xbmcgui.getCurrentWindowId()
    home = window_id == 10000 and focused in {510, 511, 512, 520, 521, 522, 530, 531, 532, 540, 541, 542, 570}
    person = window_id == PERSON and focused in {700, 710, 720}
    live = window_id == 11105 and focused in {610, 620}
    if not (home or person or live):
        return None
    directory = Path(__file__).resolve().parents[1] / '1080i'
    includes, constants = {}, {}
    for path in directory.glob('Includes*.xml'):
        tree = ET.parse(path)
        includes.update({node.get('name'): node for node in tree.iter('include') if node.get('name')})
        constants.update({node.get('name'): node.text for node in tree.iter('constant')})

    def condition(expression):
        # The native context dialog holds focus now. Evaluate Home's card focus
        # against the retained Home control, while skin settings stay global.
        expression = re.sub(r'Control.HasFocus\((\d+)\)',
                            lambda match: 'true' if int(match[1]) == focused else 'false', expression)
        expression = expression.replace('Window.Property(', f'Window({window_id}).Property(')
        return xbmc.getCondVisibility(expression)

    tree = expand(ET.parse(directory / ('Home.xml' if home else 'Custom_1105.xml' if live else 'Custom_1103.xml')).getroot(), includes, condition)
    scroll = int(window.getControl(5501).getLabel().split('/')[0] or 0) if home else 0
    cursor = int(window.getControl(5502).getLabel() or 0) if home or live else 0
    return card_rect(tree, focused, cursor, scroll, constants, condition)


if __name__ == '__main__':
    actions = {'initialize': initialize, 'person': open_person, 'credit': open_credit,
               'watched': watched, 'shuffle': shuffle, 'context': context,
               'more': show_more, 'cast': show_cast, 'play-episode': play_episode}
    try:
        if len(sys.argv) == 2 and sys.argv[1] in actions:
            actions[sys.argv[1]]()
    except (RuntimeError, ValueError) as error:
        xbmc.log('Starlight info action: ' + str(error), xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Starlight', xbmc.getLocalizedString(31063))
