#!/usr/bin/env python3
"""Render actual player XML with local records and a sample spectrum.
Native input, auto-width layout, timing and provider actions require Kodi.
"""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont, ImageOps

from render_home import HomePreview, ROOT
from home_content import blurred_art
from player_content import pill_geometry
import xml.etree.ElementTree as ET

STATES = ('music-M1', 'music-M2', 'music-paused', 'music-visualiser-off',
          'music-local', 'music-no-helper', 'music-pill', 'music-pill-osd',
          'music-more', 'music-more-local', 'queue', 'queue-empty',
          'video-osd', 'video-bookmarks', 'video-seek', 'video-info', 'player-process', 'player-buffering')


class PlayerPreview(HomePreview):
    def __init__(self, art, state):
        self.art = art
        self.state = state
        self.properties = {}
        self.active = set()
        self.selected = {510: 0, 520: 0}
        self.labels = {}
        super().__init__(art)
        tracks = json.loads((art / 'indie.json').read_text())['tracks'] if (art / 'indie.json').exists() else []
        self.tracks = tracks
        self.labels = {'MusicPlayer.Cover': str(art / 'sp-5-poster.jpg'),
                       'MusicPlayer.Title': 'Alaska', 'MusicPlayer.Artist': 'Maggie Rogers',
                       'MusicPlayer.Album': 'Heard It In A Past Life',
                       'Player.Time': '1:14', 'Player.Duration': '3:08', 'Player.Progress': '39',
                       'Player.SeekTime': '0:52:10', 'Player.SeekOffset': '+00:30', 'Player.FinishTime': '2:58 PM',
                       'VideoPlayer.Title': 'Blade Runner', 'VideoPlayer.Year': '1982',
                       'VideoPlayer.VideoVersionName': 'Final Cut', 'VideoPlayer.TVShowTitle': '',
                       'VideoPlayer.Genre': 'Science fiction, thriller', 'VideoPlayer.Director': 'Ridley Scott',
                       'VideoPlayer.Plot': 'In the smog-choked Los Angeles of 2019, blade runner Rick Deckard returns to hunt four escaped replicants.',
                       'Player.Art(clearlogo)': str(art / 'Blade_Runner-clearlogo.png'),
                       'Player.Art(tvshow.clearlogo)': '',
                       'Player.Process(videodecoder)': 'am-h265 (HW)', 'Player.Process(videowidth)': '3840',
                       'Player.Process(videoheight)': '2160', 'Player.Process(videofps)': '23.976',
                       'Player.Process(audiodecoder)': 'TrueHD', 'Player.Process(audiochannels)': '7.1',
                       'Player.Process(audiosamplerate)': '48000'}
        self.properties.update({'Starlight.Player.Blurred': blurred_art(self.labels['MusicPlayer.Cover']),
                                'Spotify.CurrentTrackId': 'sample-track', 'Spotify.CurrentTrackLiked': 'true',
                                'Starlight.NextTrack.Title': "Can't Do Without You", 'Starlight.NextTrack.Artist': 'Caribou',
                                'Starlight.NextTrack.Art': str(art / 'sp-6-poster.jpg'),
                                'Starlight.NextTrack.Remaining': '9', 'Starlight.NextTrack.Progress': '60'})
        self.focus = 413
        if state in ('music-local', 'music-more-local'):
            self.properties['Spotify.CurrentTrackId'] = ''
        if state == 'music-visualiser-off': self.settings['Player.Visualiser.Disabled'] = 'true'
        if 'pill' in state:
            self.properties['Starlight.NextTrack.Active'] = 'true'
            self.labels.update({'Player.Time': '2:59', 'Player.Progress': '95'})
        if state in ('music-M2', 'music-paused', 'music-local', 'music-no-helper', 'music-pill-osd', 'music-more', 'music-more-local'):
            self.active.add('musicosd')
        if state in ('music-more','music-more-local'):
            self.focus = 501 if state == 'music-more' else 503
        if state.startswith('queue'):
            self.active.add('11104'); self.focus = 510
            self.properties.update({'Starlight.Queue.Count': '50', 'Starlight.Queue.NextCount': '0' if state == 'queue-empty' else '44', 'Starlight.Queue.Ready': 'true'})
            for identity, indexes in ((510,range(6,13)),(520,range(4,-1,-1))):
                self.containers[identity] = [{'Label':tracks[n]['title'], 'Label2':tracks[n]['artist'],
                    'art':{'thumb':str(art / f'sp-{n}-poster.jpg')}} for n in indexes] if tracks and state != 'queue-empty' else []
            if state == 'queue-empty': self.focus = 900
        else:
            self.active.add('visualisation')
        if state.startswith('video') or state.startswith('player'):
            self.active.discard('visualisation')
            self.labels.update({'Player.Time': '0:52:10', 'Player.Duration': '1:57:00', 'Player.TimeRemaining':'1:04:50', 'Player.Progress': '44.6'})
        if state == 'video-osd': self.active.add('videoosd')
        self.documents = []
        if state.startswith('music'):
            self.documents.append('MusicVisualisation.xml')
            if 'musicosd' in self.active: self.documents.append('MusicOSD.xml')
            if 'more' in state: self.documents.append('Custom_1105.xml')
        elif state.startswith('queue'): self.documents.append('Custom_1104.xml')
        else:
            self.documents.append({'video-osd':'VideoOSD.xml','video-seek':'DialogSeekBar.xml',
                'video-bookmarks':'VideoOSDBookmarks.xml', 'video-info':'DialogFullScreenInfo.xml','player-process':'DialogPlayerProcessInfo.xml',
                'player-buffering':'DialogSeekBar.xml'}[state])
        if state == 'video-bookmarks':
            self.focus = 11
            self.containers[11] = [{'Label':f'Chapter {n+1}', 'Label2':f'0:{n*12:02d}:00'} for n in range(5)]
        for rows in self.containers.values():
            for row in rows:
                row.setdefault('properties', {}).update({'Starlight.Action':'Play', 'Starlight.Time':'4 m'})
        self.home = self.document(self.documents[0])

    def document(self, filename):
        return self.expand(ET.parse(ROOT / '1080i' / filename).getroot())

    def info(self, text):
        parts = self.split(text, ',')
        if len(parts) == 3:
            value = self.info(parts[0])
            return parts[1] + value + parts[2] if value else ''
        match = re.fullmatch(r'Window(?:\(home\))?\.Property\(([^)]+)\)',text.strip())
        if match: return self.properties.get(match[1], '')
        if text == 'Container(510).CurrentItem': return '0' if self.state == 'queue-empty' else '1'
        if text in self.labels: return self.labels[text]
        if text.startswith(('MusicPlayer.','VideoPlayer.','Player.')): return ''
        return super().info(text)

    def condition(self, expression):
        expression = expression.strip()
        match = re.fullmatch(r'Window.Is(?:Visible|Active)\(([^)]+)\)',expression)
        if match: return match[1] in self.active
        if expression == 'ListItem.IsSelected': return False
        if expression == 'System.HasAddon(script.starlight)': return self.state != 'music-no-helper'
        if expression in ('Player.Paused','Player.Caching','Player.Seeking','Player.DisplayAfterSeek',
                          'Player.SeekEnabled','Visualisation.Enabled','Playlist.IsRandom','Playlist.IsRepeat','Playlist.IsRepeatOne'):
            return {'Player.Paused': self.state == 'music-paused',
                    'Player.Caching': self.state == 'player-buffering',
                    'Player.Seeking': self.state == 'video-seek',
                    'Player.DisplayAfterSeek': self.state == 'video-seek',
                    'Player.SeekEnabled': True, 'Visualisation.Enabled': True}.get(expression,False)
        match = re.fullmatch(r'Integer.IsLess\((.*),(\d+)\)',expression)
        if match: return float(self.info(match[1]) or 0) < int(match[2])
        return super().condition(expression)

    def draw(self, raw, origin=(0,0), parent=(1920,1080), opacity=1):
        if any(a.text == 'WindowOpen' and a.get('effect') == 'fade' and a.get('end') == '0' for a in raw.findall('animation')):
            return
        if raw.get('type') == 'visualisation':
            if not self.condition(raw.findtext('visible','true')): return
            # Renderer-only spectrum sample. The binary add-on supplies live bars.
            layer = Image.new('RGBA', self.canvas.size)
            draw = ImageDraw.Draw(layer)
            cx,cy,radius = 960,382,180
            for n in range(160):
                angle = n * math.tau / 160 - math.pi/2
                f = n/160
                energy = .55*math.exp(-((f-.05)/.06)**2) + .45*math.exp(-((f-.32)/.05)**2) + .3*math.exp(-((f-.7)/.04)**2) + .14*(.5+.5*math.sin(n*7))+.06
                length = 5+100*energy
                draw.line((cx+radius*math.cos(angle),cy+radius*math.sin(angle),
                           cx+(radius+length)*math.cos(angle),cy+(radius+length)*math.sin(angle)),
                          fill=(245,205,149,245),width=4)
            self.canvas=Image.alpha_composite(self.canvas,layer)
            return
        if raw.get('type') == 'slider':
            # Match the native playhead position; the gold fill is a real progress control.
            left=self.number(raw.findtext('left','0'))
            top=self.number(raw.findtext('top','0'))
            width=self.number(raw.findtext('width','1000'))
            if raw.find('right') is not None: width=parent[0]-left-self.number(raw.findtext('right'))
            progress=float(self.info(raw.findtext('info','Player.Progress')) or 0)/100
            point=self.texture('playhead_glow.png')
            self.canvas.alpha_composite(point,(round(origin[0]+left+width*progress-32),origin[1]+top))
            return
        if raw.get('id') == '600':
            raw=deepcopy(raw)
            title=self.properties.get('Starlight.NextTrack.Title','')
            artist=self.properties.get('Starlight.NextTrack.Artist','')
            regular=ImageFont.truetype(str(ROOT/'fonts/manrope-regular.ttf'),22)
            bold=ImageFont.truetype(str(ROOT/'fonts/manrope-bold.ttf'),22)
            left,width=pill_geometry(bold.getlength(title)+regular.getlength(' · '+artist))
            raw.find('left').text=str(left)
            raw.find("control[@id='602']/width").text=str(width)
            raw.find("control[@id='603']/width").text=str(width-144)
        if raw.get('type') == 'multiimage':
            raw=deepcopy(raw); raw.set('type','image')
            ET.SubElement(raw,'texture').text=raw.findtext('imagepath')+'/frame_00.png'
        super().draw(raw,origin,parent,opacity)

    def save(self, output):
        if self.state.startswith(('video','player')):
            self.canvas=ImageOps.fit(Image.open(self.art/'Blade_Runner-fanart.jpg').convert('RGBA'),(1920,1080))
        for filename in self.documents:
            document=self.document(filename)
            self.groups.update({int(n.get('id')):{int(c.get('id')) for c in n.iter('control') if c.get('id')}
                                for n in document.iter('control') if n.get('id')})
            for node in document.findall('controls/control'): self.draw(node)
        output.parent.mkdir(parents=True,exist_ok=True)
        self.canvas.convert('RGB').save(output)
        return {'state':self.state,'path':str(output),'size':[1920,1080],
                'windows':self.documents,'spectrum':'sample only; live binary add-on requires Kodi'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/tmp/starlight-step4'))
    parser.add_argument('--state',choices=STATES)
    args=parser.parse_args()
    reports=[PlayerPreview(args.art,state).save(args.output/(state+'.png'))
             for state in ([args.state] if args.state else STATES)]
    (args.output/'previews.json').write_text(json.dumps(reports,indent=2)+'\n')
    print(f'Rendered {len(reports)} player states to {args.output}')
