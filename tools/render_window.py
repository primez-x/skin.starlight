#!/usr/bin/env python3
"""Render step 3 XML with sample records. Kodi timing, input and APIs need a box."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

from render_home import HomePreview, ROOT
from home_content import blurred_art, duration_label


WINDOWS = {
    'movie-info': 'DialogVideoInfo.xml', 'tvshow-info': 'DialogVideoInfo.xml',
    'person': 'Custom_1103.xml', 'context': 'DialogContextMenu.xml',
    'options': 'DialogSelect.xml', 'yesno': 'DialogConfirm.xml',
    'toast-volume': 'DialogNotification.xml', 'busy': 'DialogBusy.xml',
    'keyboard': 'DialogKeyboard.xml',
}


class WindowPreview(HomePreview):
    def __init__(self, art, name, settings=None):
        self.art = art
        self.name = name
        self.properties = {}
        self.active = set()
        self.selected = {550: 1, 560: 3}
        self.native_labels = {}
        super().__init__(art, settings=settings)
        self.strings['117'] = 'Delete'
        self.containers.update({50: [], 250: [], 550: [], 560: [], 700: [], 710: [], 720: [], 3: [], 6: []})
        self.seed(art)
        self.home = self.document(WINDOWS[name])
        self.groups = {int(node.get('id')): {int(c.get('id')) for c in node.iter('control') if c.get('id')}
                       for node in self.home.iter('control') if node.get('id')}
        self.configure_native(self.home)

    def document(self, name):
        return self.expand(ET.parse(ROOT / '1080i' / name).getroot())

    def seed(self, art):
        movie = deepcopy(self.samples['continue'][0])
        movie.update({'Title': 'Blade Runner', 'DBTYPE': 'movie', 'DBID': '7',
                      'Genre': 'Science fiction, thriller', 'Director': 'Ridley Scott',
                      'AudioLanguage': 'English', 'AudioChannels': '7.1', 'SubtitleLanguage': 'English +4',
                      'Plot': 'In the smog-choked Los Angeles of 2019, blade runner Rick Deckard is called out of retirement '
                              'to hunt down four replicants who escaped to Earth.'})
        self.hero = movie
        self.focus = {'movie-info':9, 'tvshow-info':550, 'person':700, 'context':1001,
                      'options':3, 'yesno':10, 'keyboard':165}.get(self.name, 0)
        self.properties.update({'Starlight.Info.Ready':'true', 'Starlight.Info.Resume':'true',
                                'Starlight.Info.Duration':'1 h 57 m', 'Starlight.Info.Time':'1 h 54 m',
                                'Starlight.Info.Progress':'3', 'Starlight.Info.Playhead':'163',
                                'Starlight.Info.Blurred':blurred_art(movie['art'].get('fanart', ''))})
        if self.name == 'tvshow-info':
            self.hero = dict(movie, Title='The Expanse', DBTYPE='tvshow', Mpaa='TV-14', Year='2015',
                             Genre='Science fiction, drama',
                             Plot="Two hundred years from now, a detective and a rogue ship's crew uncover a conspiracy "
                                  'that threatens the fragile peace between Earth, Mars and the Belt.',
                             art={key: str(art / 'expanse' / ('show-' + key + ('.png' if key=='clearlogo' else '.jpg')))
                                  for key in ('fanart','poster','clearlogo')}, properties={'TotalSeasons':'6','EndYear':'2022'})
            records = json.loads((art / 'expanse/episodes.json').read_text())
            episodes = []
            for row in records:
                if str(row['season']) != '4' or not 3 <= int(row['ep']) <= 6:
                    continue
                number = int(row['ep'])
                runtime = duration_label(int(row['runtime'])//60)
                episodes.append({'Label':f"{number}. {row['title']}", 'DBTYPE':'episode', 'PlayCount':'1' if number==3 else '0',
                                 'PercentPlayed':'0', 'art':{'thumb':str(art / f'expanse/s4e{number}-landscape.jpg')},
                                 'properties':{'Starlight.Action':'Play', 'Starlight.Time':runtime,
                                               'Starlight.Detail':runtime, 'Starlight.Next':'true' if number==4 else ''}})
            self.containers[550] = episodes
            self.containers[560] = [{'Label':f'Season {n}', 'properties':{'Starlight.Season':str(n)}} for n in range(1,7)]
            self.properties['Starlight.Info.Season'] = '4'
            self.properties['Starlight.Info.Blurred'] = blurred_art(self.hero['art']['fanart'])
        if self.name == 'person':
            self.properties.update({'Starlight.Person.Name':'Harrison Ford', 'Starlight.Person.Meta':'Actor · Born July 13, 1942 (84) · Chicago, Illinois',
                                    'Starlight.Person.Thumb':str(art / 'ford/ford-thumb.jpg'),
                                    'Starlight.Person.Biography':'Harrison Ford is an American actor. He is best known as Han Solo in Star Wars, Indiana Jones, '
                                     'and Rick Deckard in Blade Runner. He also played Jack Ryan in Patriot Games and Clear and Present Danger, '
                                     'and he received an Academy Award nomination for Witness (1985).',
                                    'Starlight.Person.Blurred':blurred_art(str(art / 'ford/Blade_Runner-fanart.jpg')),
                                    'Starlight.Person.Tab':'library', 'Starlight.Person.Hub':'movies'})
            films = [('Captain_America_Brave_New_World','Captain America: Brave New World','President Ross · 2025'),
                     ('Blade_Runner_2049','Blade Runner 2049','Rick Deckard · 2017'),
                     ('Star_Wars_Episode_VII_The_Force_Awakens','The Force Awakens','Han Solo · 2015'),
                     ('Ender_s_Game',"Ender's Game",'Colonel Graff · 2013'),
                     ('Star_Wars_Episode_VI_Return_of_the_Jedi','Return of the Jedi','Han Solo · 1983'),
                     ('Blade_Runner','Blade Runner','Deckard · 1982'),('Apocalypse_Now','Apocalypse Now','Colonel · 1979')]
            self.containers[700] = [{'Label':title, 'art':{'poster':str(art / f'ford/{key}-poster.jpg')},
                                     'properties':{'Starlight.RoleYear':role}} for key,title,role in films]
        self.containers[250] = [{'Label':name, 'Label2':role, 'art':{'thumb':str(art/'ford/ford-thumb.jpg') if index==0 else str(ROOT/'media/person_placeholder.png')}}
                                for index,(name,role) in enumerate([('Harrison Ford','Rick Deckard'),('Rutger Hauer','Roy Batty'),
                                                                   ('Sean Young','Rachael'),('Edward James Olmos','Gaff'),('Daryl Hannah','Pris')])]
        self.containers[3] = [{'Label':name} for name in ['Resume','Play from beginning','Mark watched','Information','Remove from Continue watching']]
        self.native_labels.update({1:'Options', 2:'5', 10:'Cancel', 11:'Remove', 12:'',
                                   30:'Updating library',31:'Scanning The Expanse · 62%',
                                   401:'Library updated',402:'3 new episodes of The Expanse',
                                   311:'Search',312:'blade ru'})
        if self.name == 'yesno':
            self.native_labels[1] = 'Remove from Continue watching?'
            self.native_labels[9] = 'The Expanse S4 E4 leaves this row. Your watch progress stays.'
        allowed = {'options':{1,2,5,7,8}, 'yesno':{1,9,10,11,12},
                   'toast-volume':{30,31,401,402}, 'keyboard':{311,312}}.get(self.name,set())
        self.native_labels = {key:value for key,value in self.native_labels.items() if key in allowed}
        for row,letters in enumerate(['1234567890','qwertyuiop',"asdfghjkl'",'zxcvbnm,.-']):
            self.native_labels.update({100+row*20+n:letter for n,letter in enumerate(letters)})
        if self.name == 'context':
            self.properties.update({'Starlight.Context.Card':'true','Starlight.Context.Ready':'true'})
        if self.name == 'toast-volume': self.active.update({'volumebar','notification','extendedprogressdialog'})
        self.item = self.hero

    def configure_native(self, root):
        for node in root.iter('control'):
            identity = int(node.get('id', '0'))
            if identity in self.native_labels:
                label = node.find('label')
                if label is None: label = ET.SubElement(node, 'label')
                label.text = self.native_labels[identity]
            if self.name in ('yesno','options') and identity in ((12,20) if self.name=='yesno' else (5,6,8)):
                ET.SubElement(node, 'visible').text = 'false'
            if self.name == 'keyboard' and node.get('type') == 'group':
                button = node.find("control[@type='button']")
                if button is not None and 100 <= int(button.get('id',0)) < 180 and int(button.get('id')) % 20 >= 10:
                    ET.SubElement(node, 'visible').text = 'false'
        if self.name == 'context':
            group = root.find(".//control[@id='996']")
            template = group.find("control[@id='1000']")
            for index,row in enumerate(self.containers[3]):
                button = deepcopy(template); button.set('id',str(1001+index)); button.find('label').text=row['Label']; group.append(button)
            ET.SubElement(template,'visible').text='false'
            root.find(".//control[@id='997']/left").text = '455'
            root.find(".//control[@id='997']/top").text = '173'
            root.find(".//control[@id='998']/width").text = '480'
            root.find(".//control[@id='998']/height").text = '348'
            for button in group.findall("control[@type='button']"): button.find('width').text='452'

    def info(self, text):
        match = re.fullmatch(r'Window(?:\(home\))?\.Property\(([^)]+)\)', text.strip())
        if match: return self.properties.get(match[1], '')
        match = re.fullmatch(r'Control.GetLabel\((\d+)\)', text.strip())
        if match:
            identity = int(match[1])
            if identity == 20 and self.name == 'toast-volume': return '64'
            return self.native_labels.get(identity, '' if 100<=identity<180 else 'Button')
        if text == 'Player.Volume': return '64'
        if text == 'Preview.Progress': return '62'
        return super().info(text)

    def condition(self, expression):
        expression = expression.strip()
        if expression == 'Player.Muted': return False
        if expression == 'ListItem.IsResumable': return bool(self.item.get('PercentPlayed', '0') != '0')
        if expression == 'ListItem.IsSelected': return False
        match = re.fullmatch(r'Window.Is(?:Visible|Active)\(([^)]+)\)', expression)
        if match: return match[1] in self.active
        return super().condition(expression)

    def draw(self, raw, origin=(0,0), parent=(1920,1080), opacity=1):
        node = deepcopy(raw)
        identity = int(node.get('id','0'))
        if identity in self.native_labels and node.get('type') in ('label','button','textbox','edit','fadelabel'):
            label = node.find('label')
            if label is None: label=ET.SubElement(node,'label')
            label.text=self.native_labels[identity]
        if identity == 32 and node.get('type') == 'progress': ET.SubElement(node,'info').text='Preview.Progress'
        super().draw(node,origin,parent,opacity)

    def save(self, output):
        if self.name == 'keyboard':
            # Search arrives in step 5. Reuse the real widget row as the context
            # fixture, with the native keyboard edit above the actual sheet.
            controls = ET.Element('controls')
            for name,params in [('InfoBackground',{}),('InfoClock',{}),
                                ('HubRail',{'current':'search','return':'902'})]:
                include = ET.SubElement(controls,'include',content=name)
                for key,value in params.items(): ET.SubElement(include,'param',name=key,value=value)
            for node in self.expand(controls): self.draw(node)
            include = ET.Element('controls')
            widget = ET.SubElement(include,'include',content='HomeWidget')
            params = {'source':'movies','setting':'Home.Movies.Layout','layout':'landscape',
                      'label':'Top results','group':'1520','feature':'520','tiles':'521',
                      'row':'522','empty':'523','up':'9000','down':'9000','x':'196'}
            for key,value in params.items(): ET.SubElement(widget,'param',name=key,value=value)
            for node in self.expand(include): self.draw(node,origin=(0,233))
        elif self.name in ('context','options','yesno','toast-volume','busy'):
            background = HomePreview(self.art, settings=self.settings)
            if self.name == 'context': background.focus = 511
            for node in background.home.findall('controls/control'): background.draw(node)
            self.canvas = background.canvas
        if self.name == 'toast-volume':
            for name in ('DialogVolumeBar.xml','DialogExtendedProgressBar.xml'):
                for node in self.document(name).findall('controls/control'): self.draw(node)
        for node in self.home.findall('controls/control'): self.draw(node)
        output.parent.mkdir(parents=True,exist_ok=True)
        self.canvas.convert('RGB').save(output)
        print(f'{self.name}: {output} (1920x1080, actual expanded XML, sample data)')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/tmp/starlight-step3'))
    parser.add_argument('--window',choices=WINDOWS)
    parser.add_argument('--focus',type=int)
    parser.add_argument('--property',action='append',default=[],metavar='KEY=VALUE')
    parser.add_argument('--setting',action='append',default=[],metavar='KEY=VALUE')
    args=parser.parse_args()
    for name in [args.window] if args.window else WINDOWS:
        preview=WindowPreview(args.art,name,dict(value.split('=',1) for value in args.setting))
        if args.focus is not None: preview.focus=args.focus
        preview.properties.update(dict(value.split('=',1) for value in args.property))
        preview.save(args.output / (name+'.png'))
