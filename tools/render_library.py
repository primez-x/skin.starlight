#!/usr/bin/env python3
"""Render step 5 XML at 1920×1080. Native input and provider actions need Kodi."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

from render_home import HomePreview, ROOT
from render_window import WindowPreview
from home_content import blurred_art

VIEW_IDS = tuple(range(4200, 4226))


class LibraryPreview(WindowPreview):
    def __init__(self, art, name, view=4212, rail=False, empty=False):
        super().__init__(art, 'movie-info')
        self.name, self.view, self.empty = name, view, empty
        self.native_labels = {}
        self.properties.update({'Starlight.Hub': 'search' if name.startswith('search') else 'discover' if name=='discover' else 'music' if name=='music' else 'movies',
                                'Starlight.Library.Container':str(view), 'Starlight.Discover.Hub':'trending',
                                'Starlight.Search.Source':'movies' if name=='search-wall' else 'top',
                                'Starlight.Search.Query':'' if empty and name.startswith('search') else 'a',
                                'Starlight.Search.Keyboard':'true' if name=='search-keyboard' else '',
                                'Starlight.Library.Blurred':blurred_art(str(art/'Blade_Runner-fanart.jpg'))})
        self.active = {'musicnav' if name=='music' else 'videos' if name=='video' else '11100' if name.startswith('search') else '11101'}
        self.focus = 901 if rail else 165 if name=='search-keyboard' else 40 if name=='search' else 620 if name=='search-wall' else 510 if name=='discover' else view
        movies = deepcopy(self.samples['continue'] + self.samples['movies'])
        movies[0].update({'Label':'Blade Runner', 'Year':'1982', 'Genre':'Science fiction, thriller', 'DBTYPE':'movie',
                          'Plot':'In the smog-choked Los Angeles of 2019, blade runner Rick Deckard is called out of retirement to hunt down four replicants.'})
        for index, row in enumerate(movies):
            row.setdefault('Plot', 'A journey beyond the familiar reveals a world of possibility.')
            row.update({'DBTYPE':'movie','Label2':row.get('Year',''), 'Artist':'','Album':'', 'Comment':row.get('Plot','')})
        music = json.loads((art/'indie.json').read_text())['tracks']
        albums = [{'Label':row['title'], 'Label2':row['artist'], 'Artist':row['artist'], 'Album':row['album'],
                   'Duration':f"{row['ms']//60000}:{row['ms']//1000%60:02d}", 'Year':'2014', 'DBTYPE':'song',
                   'art':{'thumb':str(art/f'sp-{index}-poster.jpg'), 'poster':str(art/f'sp-{index}-poster.jpg')}, 'properties':{}}
                  for index,row in enumerate(music[:18])]
        for identity in VIEW_IDS:
            self.containers[identity] = [] if empty else deepcopy(albums if name=='music' else movies)
        if name in ('video','music'):
            self.selected[view] = 4 if view in (4212,4213,4214) else 0
        categories = [{'Label':label,'properties':{}} for label in ['Action','Animation','Comedy','Drama','Horror','Science fiction','Thriller']]
        self.containers[700] = self.containers[701] = categories
        top = [deepcopy(movies[7]), deepcopy(movies[1]), deepcopy(albums[5]), deepcopy(movies[6]), deepcopy(albums[12]), deepcopy(movies[2]), deepcopy(albums[4])]
        for index,row in enumerate(top):
            shape='circle' if index==6 else 'square' if index in (2,4) else 'poster'
            row.setdefault('properties',{}).update({'Starlight.Search.Shape':shape,'Starlight.Search.Type':'artist' if index==6 else 'song' if shape=='square' else 'movie'})
            row['Label2']='Spotify · '+row.get('Artist','') if shape!='poster' else 'Movie · '+row.get('Year','')
        for index,source in enumerate(('top','movies','tvshows','episodes','music','spotify','people','collections','genres','plex')):
            rows=deepcopy(top if index==0 else albums if source in ('music','spotify') else movies[:6])
            for row in rows:
                row.setdefault('properties',{}).setdefault('Starlight.Search.Shape','square' if source in ('music','spotify') else 'circle' if source=='people' else 'poster')
                row['Label2']=row.get('Label2') or 'Movie · '+row.get('Year','')
            self.containers[610+index]=[] if empty else rows
            self.properties['Starlight.Search.Count.'+source]=str(len(self.containers[610+index]))
        self.containers[620]=self.containers[611]
        self.containers[40]=[{'Label':char,'properties':{'Key':char}} for char in 'abcdefghijklmnopqrstuvwxyz1234567890']
        self.containers[50]=[{'Label':label} for label in ['blade runner','The Expanse','Tycho']]
        if name=='discover':
            self.containers[510]=[] if empty else movies[2:3]
            self.containers[511]=[] if empty else [movies[12],movies[3],movies[4],movies[10]]
            self.containers[512]=[] if empty else self.samples['movies']
            self.properties['Starlight.Library.Blurred']=blurred_art(movies[2]['art'].get('fanart',''))
            for identity in (510,511,512):
                for row in self.containers[identity]:
                    row['properties']={'Starlight.Duration':row.get('Duration','')}
        self.containers[600]=[{'Label':title} for title in (['Trending','Movies','TV shows','Coming soon','Top rated'] if name=='discover' else ['All','Movies 12','TV shows 6','Music 9','Spotify 20','People 2'])]
        filename='MyMusicNav.xml' if name=='music' else 'MyVideoNav.xml' if name=='video' else 'Custom_1101.xml' if name=='discover' else 'Custom_1100.xml'
        self.home=self.document(filename)
        self.groups={int(node.get('id')):{int(child.get('id')) for child in node.iter('control') if child.get('id')}
                     for node in self.home.iter('control') if node.get('id')}
        self.item=movies[0] if name!='music' else albums[4]
        if name in ('video','music') and self.containers.get(view):
            self.item=self.containers[view][self.selected.get(view,0)]
            self.properties['Starlight.Library.Blurred']=blurred_art(self.item.get('art',{}).get('fanart') or self.item.get('art',{}).get('thumb',''))
        self.selected[40]=17

    def info(self, text):
        match=re.fullmatch(r'Container\((\d+)\)\.ListItem\.(.*)',text)
        if match:
            rows=self.containers.get(int(match[1]),[])
            index=self.selected.get(int(match[1]),0)
            previous=self.item
            self.item=rows[min(index,len(rows)-1)] if rows else {}
            value=HomePreview.info(self,'ListItem.'+match[2])
            self.item=previous
            return value
        if text=='Container.FolderName':return 'Indie Pop 2010s' if self.name=='music' else 'Movies'
        if text=='Container.NumItems':return str(len(self.containers.get(self.view,[])))
        if text.startswith('Container.ListItem.'):text=text.replace('Container.ListItem.','ListItem.')
        return super().info(text)

    def condition(self, expression):
        expression=expression.strip()
        match=re.fullmatch(r'Control.IsVisible\((\d+)\)',expression)
        if match:return int(match[1])==self.view if int(match[1]) in VIEW_IDS and self.name in ('video','music') else True
        if expression.startswith('System.HasAddon('):return True
        return super().condition(expression)

    def draw(self, raw, origin=(0,0), parent=(1920,1080), opacity=1):
        identity=int(raw.get('id','0'))
        if self.name in ('video','music') and identity in VIEW_IDS and identity!=self.view:return
        if raw.get('type') not in ('list','fixedlist','panel'):
            return super().draw(raw,origin,parent,opacity)
        if not self.condition(raw.findtext('visible','true')):return
        node=deepcopy(raw)
        x=origin[0]+self.number(node.findtext('left','0'));y=origin[1]+self.number(node.findtext('top','0'))
        w=self.number(node.findtext('width',str(parent[0])));h=self.number(node.findtext('height',str(parent[1])))
        saved=self.canvas.copy();previous=self.item;cursor=0;selected=self.selected.get(identity,0)
        for index,row in enumerate(self.containers.get(identity,[])):
            self.item=row
            layouts=node.findall('focusedlayout' if index==selected else 'itemlayout')
            layout=next(candidate for candidate in layouts if self.condition(candidate.get('condition','true')))
            lw,lh=self.number(layout.get('width')),self.number(layout.get('height'))
            vertical=node.findtext('orientation')=='vertical';columns=max(1,w//lw) if node.get('type')=='panel' else 1
            xx,yy=(x+(index%columns)*lw,y+(index//columns)*lh) if node.get('type')=='panel' else (x,y+cursor) if vertical else (x+cursor,y)
            if xx>x+w or yy>y+h:break
            for child in layout.findall('control'):self.draw(child,(xx,yy),(lw,lh),opacity)
            cursor+=lh if vertical else lw
        self.item=previous
        bounds=(max(0,x),max(0,y),min(1920,x+w),min(1080,y+h))
        if bounds[2]>bounds[0] and bounds[3]>bounds[1]:
            clip=self.canvas.crop(bounds)
            self.canvas=saved;self.canvas.alpha_composite(clip,bounds[:2])
        else:
            self.canvas=saved

    def save(self, output):
        for node in self.home.findall('controls/control'):self.draw(node)
        if self.name=='search-keyboard':
            keyboard=WindowPreview(self.art,'keyboard')
            keyboard.properties.update(self.properties)
            keyboard.native_labels[311]=''
            keyboard.native_labels[312]='a'
            keyboard.home=keyboard.document('DialogKeyboard.xml')
            for field in keyboard.home.findall("controls/control[@id='312']"):
                field.find('top').text='46';field.find('width').text='1424'
            keyboard.canvas=self.canvas
            for node in keyboard.home.findall('controls/control'):keyboard.draw(node)
            self.canvas=keyboard.canvas
        output.parent.mkdir(parents=True,exist_ok=True);self.canvas.convert('RGB').save(output)
        print(f'{output.name}: 1920×1080, actual XML, sample data')


def render_info_and_menu(art, output):
    for media in ('movie', 'tvshow'):
        preview=WindowPreview(art,'movie-info')
        preview.hero.update({'DBTYPE':media,'PercentPlayed':'0'})
        preview.item=preview.hero;preview.focus=418
        preview.properties.update({'Starlight.Info.Provider':'true', 'Starlight.Info.ProviderKey':'sample', 'Starlight.Info.ProviderType':'movie',
                                   'Starlight.Info.Resume':'', 'Starlight.Info.Duration':'1 h 57 m'})
        preview.save(output/f'provider-{media}-info.png')
    preview=WindowPreview(art,'options')
    source=ET.parse(ROOT/'1080i/Includes_Library.xml')
    labels={int(node.get('id')):node.find('viewtype').get('label')
            for node in source.findall("include[@name='LibraryViews']/definition/control")
            if node.find('viewtype') is not None}
    names=[labels[identity] for identity in VIEW_IDS]
    preview.containers[3]=[{'Label':preview.resolve(name)} for name in names]
    preview.native_labels[1]='View';preview.native_labels[2]=str(len(names))
    preview.save(output/'view-menu.png')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/tmp/starlight-step5'))
    parser.add_argument('--window',choices=('video','music','search','search-wall','search-keyboard','discover'))
    parser.add_argument('--view',type=int,choices=VIEW_IDS,default=4212)
    parser.add_argument('--rail-open',action='store_true')
    parser.add_argument('--empty',action='store_true')
    args=parser.parse_args()
    if args.window:
        LibraryPreview(args.art,args.window,args.view,rail=args.rail_open,empty=args.empty).save(args.output/f'{args.window}-{args.view}.png')
        raise SystemExit(0)
    for identity in VIEW_IDS:
        name='music' if identity in (4206,4213,4200,4214,4217) else 'video'
        LibraryPreview(args.art,name,identity).save(args.output/f'view-{identity}.png')
    for name in ('search','search-wall','search-keyboard','discover'):
        LibraryPreview(args.art,name).save(args.output/f'{name}.png')
    for name in ('search','discover'):
        LibraryPreview(args.art,name,empty=True).save(args.output/f'{name}-empty.png')
    LibraryPreview(args.art,'discover',rail=True).save(args.output/'discover-rail.png')

    render_info_and_menu(args.art,args.output)
