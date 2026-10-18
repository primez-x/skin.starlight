"""Run inside Kodi with RunScript(PATH,probe). Use only a cleared test device.

Probes open native dialogs. No media files or database records change.
Copy this file to /tmp on the test device. Capture each dialog through fb0.
"""
import json
from pathlib import Path
import sys

import xbmc
import xbmcgui


def rpc(method, params):
    response = json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    if 'error' in response:
        raise RuntimeError(response['error']['message'])
    return response['result']


def library_info(media):
    kind = {'movie': 'Movie', 'tvshow': 'TVShow', 'episode': 'Episode'}[media]
    key = media + 'id'
    if len(sys.argv) > 2:
        dbid = int(sys.argv[2])
    else:
        result = rpc('VideoLibrary.Get' + kind + 's', {'limits': {'end': 1}})
        dbid = result['movies' if media == 'movie' else 'tvshows'][0][key]
    fields = ['title', 'file', 'art', 'plot', 'cast']
    if media != 'episode':
        fields += ['year', 'genre']
    detail = rpc('VideoLibrary.Get' + kind + 'Details',
                 {key: dbid, 'properties': fields})[media + 'details']
    path = f'videodb://tvshows/titles/{dbid}/' if media == 'tvshow' else detail['file']
    item = xbmcgui.ListItem(label=detail['title'], path=path)
    item.setArt(detail['art'])
    tag = item.getVideoInfoTag()
    tag.setDbId(dbid)
    tag.setMediaType(media)
    tag.setTitle(detail['title'])
    tag.setPlot(detail['plot'])
    tag.setYear(detail.get('year', 0))
    tag.setGenres(detail.get('genre', []))
    xbmcgui.Dialog().info(item)


probe = sys.argv[1]
dialog = xbmcgui.Dialog()
if probe in ('movie', 'tvshow', 'episode'):
    library_info(probe)
elif probe == 'select':
    dialog.select('Choose a source', ['Library', 'Recently added', 'Continue watching', 'Next up'])
elif probe == 'yesno':
    dialog.yesno('Remove from this list?', 'The video stays in your library.', nolabel='Cancel', yeslabel='Remove')
elif probe == 'keyboard':
    keyboard = xbmc.Keyboard('Starlight', 'Search your library')
    keyboard.doModal()
elif probe == 'textviewer':
    dialog.textviewer('About Starlight', 'Starlight uses smoked glass, warm gold focus, and clear type.\n\n'
                      'The Home board combines a featured video with four smaller cards.\n\n'
                      'Continue watching resumes from the saved position. Next up selects an unwatched episode.')
elif probe == 'busy':
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    xbmc.sleep(15000)
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
elif probe == 'background':
    progress = xbmcgui.DialogProgressBG()
    progress.create('Refresh library', 'Read video details')
    progress.update(73)
    xbmc.sleep(15000)
    progress.close()
elif probe == 'progress':
    directory = Path('/tmp/starlight-probe/resources/skins/Default/1080i')
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'RuntimeProgress.xml').write_text('''<window>
      <defaultcontrol>1</defaultcontrol><controls>
      <control type="image"><width>1920</width><height>1080</height><texture>background_void.png</texture></control>
      <control type="label"><left>700</left><top>420</top><width>520</width><height>60</height><font>font_heading</font><textcolor>frost</textcolor><label>73% resume progress</label></control>
      <control type="list" id="1"><left>700</left><top>500</top><width>520</width><height>100</height>
      <itemlayout width="520" height="100"><control type="label"><width>520</width><height>50</height><label>Resume probe</label></control></itemlayout>
      <focusedlayout width="520" height="100"><include content="HomePlayCapsule"><param name="id" value="1"/><param name="x" value="0"/><param name="y" value="0"/><param name="selected" value="true"/></include></focusedlayout>
      <content><item id="1"><label>Resume probe</label><property name="Starlight.Action">Resume</property><property name="Starlight.Resume">true</property><property name="Starlight.Time">27 m</property><property name="Starlight.Progress">$NUMBER[73]</property></item></content>
      </control>
      </controls></window>''')
    window = xbmcgui.WindowXMLDialog('RuntimeProgress.xml', '/tmp/starlight-probe', 'Default', '1080i')
    window.show()
    xbmc.sleep(15000)
    window.close()
