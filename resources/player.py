"""Skin-owned music presentation. Kodi and providers own playback."""
import json
from pathlib import Path
import sys
import time

import xbmc
import xbmcgui

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / 'lib'))
from home import cached_blurred_art, rpc
from home_content import duration_label
from player_content import audio_state, queue_snapshot, play_queue_item, pill_geometry

VISUALISATION = 12006
QUEUE = 11104


def monitor_stage():
    home = xbmcgui.Window(10000)
    token = str(time.monotonic_ns())
    home.setProperty('Starlight.Player.Monitor', token)
    monitor = xbmc.Monitor()
    previous_art = None
    previous_geometry = None
    while not monitor.abortRequested() and home.getProperty('Starlight.Player.Monitor') == token:
        if not any(xbmc.getCondVisibility(f'Window.IsActive({identity})') for identity in (VISUALISATION, QUEUE)):
            break
        art = xbmc.getInfoLabel('MusicPlayer.Cover')
        if not art or art == 'DefaultAlbumCover.png':
            art = 'special://skin/media/DefaultAlbumCover.png'
        if art != previous_art:
            home.setProperty('Starlight.Player.Blurred', cached_blurred_art(art))
            previous_art = art
        if xbmc.getCondVisibility('Window.IsActive(visualisation)'):
            # Fresh wrappers read the native auto-width label after GUI text layout.
            window = xbmcgui.Window(VISUALISATION)
            title_width = min(1000, window.getControl(601).getWidth())
            artist = window.getControl(604)
            left, width = pill_geometry(title_width + artist.getWidth())
            if (left, width) != previous_geometry:
                window.getControl(600).setPosition(left, 972)
                window.getControl(602).setWidth(width)
                window.getControl(603).setWidth(width - 144)
                previous_geometry = left, width
        if monitor.waitForAbort(.25):
            break
    if home.getProperty('Starlight.Player.Monitor') == token:
        home.clearProperty('Starlight.Player.Monitor')


def populate_queue(window, snapshot):
    window.setProperty('Starlight.Queue.Items', json.dumps(snapshot or {}))
    window.setProperty('Starlight.Queue.Revision', str(time.monotonic_ns()))
    window.setProperty('Starlight.Queue.Count', str(snapshot['total']) if snapshot else '0')
    window.setProperty('Starlight.Queue.NextCount', str(len(snapshot['next'])) if snapshot else '0')
    window.setProperty('Starlight.Queue.Ready', 'true')


def queue_listing(handle, args):
    import xbmcplugin
    key = args.get('row', ['next'])[0]
    if key not in ('next', 'played'):
        xbmcplugin.endOfDirectory(handle, succeeded=False)
        return
    snapshot = json.loads(xbmcgui.Window(QUEUE).getProperty('Starlight.Queue.Items') or '{}')
    for row in snapshot.get(key, []):
        item = xbmcgui.ListItem(label=row.get('title') or row.get('label', ''),
                               label2=' / '.join(row.get('artist', [])), path=row.get('file', ''))
        art = row.get('art', {})
        item.setArt({'thumb': art.get('thumb') or art.get('poster') or 'special://skin/media/player/album_placeholder.png'})
        item.setProperty('Starlight.Action', xbmc.getLocalizedString(31201))
        if row.get('duration'):
            item.setProperty('Starlight.Time', duration_label(row['duration'] / 60, xbmc.getLocalizedString(31039), xbmc.getLocalizedString(31019)))
        item.setProperty('Starlight.Queue.Position', str(row['position']))
        item.setProperty('Starlight.Queue.File', row.get('file', ''))
        xbmcplugin.addDirectoryItem(handle, '', item, isFolder=False)
    xbmcplugin.endOfDirectory(handle, cacheToDisc=False)


class QueueMonitor(xbmc.Monitor):
    revision = 0

    def onNotification(self, sender, method, data):
        if method.startswith(('Playlist.', 'Player.OnPlay', 'Player.OnAVStart', 'Player.OnStop', 'Player.OnPropertyChanged')):
            self.revision += 1


def monitor_queue():
    window = xbmcgui.Window(QUEUE)
    token = str(time.monotonic_ns())
    window.setProperty('Starlight.Queue.Request', token)
    window.clearProperty('Starlight.Queue.Ready')
    monitor = QueueMonitor()
    previous = None
    first = True
    while xbmc.getCondVisibility(f'Window.IsActive({QUEUE})') and window.getProperty('Starlight.Queue.Request') == token:
        try:
            state = audio_state(rpc)
            current = state, monitor.revision
            if current != previous:
                snapshot = queue_snapshot(rpc) if state else None
                if not xbmc.getCondVisibility(f'Window.IsActive({QUEUE})') or window.getProperty('Starlight.Queue.Request') != token:
                    break
                window.clearProperty('Starlight.Queue.Error')
                populate_queue(window, snapshot)
                previous = current
                if first or not snapshot or not snapshot['next']:
                    window.setFocusId(510 if snapshot and snapshot['next'] else 900)
                first = False
        except (RuntimeError, ValueError, KeyError):
            if not xbmc.getCondVisibility(f'Window.IsActive({QUEUE})') or window.getProperty('Starlight.Queue.Request') != token:
                break
            populate_queue(window, None)
            window.setProperty('Starlight.Queue.Error', 'true')
            window.setFocusId(900)
            previous = None
        if monitor.waitForAbort(1):
            break


def queue_play(identity):
    if identity not in ('510', '520') or not xbmc.getCondVisibility(f'Window.IsActive({QUEUE})'):
        return
    window = xbmcgui.Window(QUEUE)
    request = window.getProperty('Starlight.Queue.Request')
    prefix = f'Container({identity}).ListItem.Property(Starlight.Queue.'
    position = xbmc.getInfoLabel(prefix + 'Position)')
    path = xbmc.getInfoLabel(prefix + 'File)')
    if play_queue_item(position, path, rpc):
        if (xbmc.getCondVisibility(f'Window.IsActive({QUEUE})')
                and window.getProperty('Starlight.Queue.Request') == request):
            xbmc.executebuiltin('ActivateWindow(visualisation)')
    else:
        xbmcgui.Dialog().notification('Starlight', xbmc.getLocalizedString(31218))


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['open-queue']:
            xbmc.executebuiltin('Dialog.Close(musicosd)')
            xbmc.executebuiltin('ActivateWindow(11104)')
        elif sys.argv[1:] == ['monitor']:
            monitor_stage()
        elif sys.argv[1:] == ['queue']:
            monitor_queue()
        elif len(sys.argv) == 3 and sys.argv[1] == 'queue-play':
            queue_play(sys.argv[2])
    except (RuntimeError, ValueError, KeyError) as error:
        xbmc.log('Starlight player: ' + str(error), xbmc.LOGERROR)
