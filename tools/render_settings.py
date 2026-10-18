#!/usr/bin/env python3
"""Render step 6 XML at 1080p with explicit native-control fixtures.

The renderer expands the shipped XML. Native EPG geometry and template clones
use sample data. Kodi input, PVR backends and actions require the integration box.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image

from render_home import HomePreview, ROOT

WINDOWS = ['SkinSettings','Settings','SettingsCategory','SettingsSystemInfo','SettingsProfile',
           'DialogSettings','DialogAddonSettings','FileBrowser','DialogButtonMenu','DialogAddonInfo',
           'AddonBrowser','MyPVRGuide','MyPVRChannels','MyPVRRecordings','MyPVRTimers',
           'DialogPVRInfo','DialogPVRChannelsOSD','DialogPVRChannelGuide','Startup','Pointer',
           'Custom_1102','Custom_1106','Custom_1107','FileManager','DialogNumeric','DialogSlider']


class SettingsPreview(HomePreview):
    def __init__(self, art, name, settings=None, section='Appearance', empty=False):
        self.art=art
        self.name=name
        self.properties={'Starlight.Settings.Section':section,
                         'Starlight.Settings.Title':'Hub navigation','Starlight.Settings.Key':'Hub.Navigation',
                         'Starlight.Settings.Help':'Disable Ambient effects to stop the arrival glint and background twinkles. Progress feedback stays visible.'}
        self.native_labels={}
        self.selected={}
        self.installed=True
        self.empty=empty
        super().__init__(art,settings=settings)
        self.focus={'SkinSettings':716,'Settings':510,'Custom_1102':510,'SettingsCategory':-178,
                    'DialogSettings':-180,'DialogAddonSettings':-180,'SettingsSystemInfo':95,
                    'SettingsProfile':2,'FileBrowser':450,'DialogButtonMenu':910,
                    'DialogAddonInfo':9,'AddonBrowser':50,'MyPVRGuide':50,'MyPVRChannels':50,
                    'MyPVRRecordings':50,'MyPVRTimers':50,'DialogPVRInfo':5,
                    'DialogPVRChannelsOSD':11,'DialogPVRChannelGuide':11,
                    'Custom_1106':610,'Custom_1107':610,'FileManager':20,'DialogNumeric':11,'DialogSlider':11}.get(name,0)
        if name=='SkinSettings':self.focus={'Hub':710,'Widgets':711,'Appearance':716,'Music':717,'Screensaver':718}[section]
        self.guide=json.loads((art/'pvr/guide.json').read_text())
        self.channels=[self.channel(row) for row in self.guide['channels']]
        self.item=self.channels[0]
        self.hero=self.item
        self.home=self.expand(ET.parse(ROOT/'1080i'/(name+'.xml')).getroot())
        self.seed()
        if name=='SkinSettings':
            focused=self.home.find(f".//control[@id='{self.focus}']")
            for action in focused.findall('onfocus'):
                if (action.text or '').startswith('SetProperty(Starlight.Settings.Help,'):
                    self.properties['Starlight.Settings.Help']=self.resolve(action.text[len('SetProperty(Starlight.Settings.Help,'):-1])
        self.groups={int(n.get('id')):{int(c.get('id')) for c in n.iter('control') if c.get('id')}
                     for n in self.home.iter('control') if n.get('id')}

    def channel(self, row):
        tag=row['tags'][0]
        clock=lambda value:datetime.fromtimestamp(value,tz=timezone.utc).strftime('%H:%M')
        return {'Label':tag['title'],'Label2':f"{clock(tag['start'])} – {clock(tag['end'])}",
                'ChannelName':row['name'],'ChannelNumberLabel':str(row['num']),
                'Icon':str(self.art/row['icon']),'EpgEventIcon':str(self.art/(row.get('prog') or row['icon'])),
                'EpgEventTitle':tag['title'],'StartTime':clock(tag['start']),'EndTime':clock(tag['end']),
                'StartDate':'26 Feb 2026','Genre':tag['genre'],'EpisodeName':tag['ep'],'Plot':tag['plot'],
                'Progress':'57','NextTitle':row['tags'][1]['title'],'NextStartTime':clock(row['tags'][1]['start']),
                'art':{'thumb':str(self.art/(row.get('prog') or row['icon']))}}

    def seed(self):
        for node in self.home.iter('control'):
            if node.get('type') in ('list','panel','fixedlist'):
                identity=int(node.get('id'))
                content=node.find('content')
                if content is not None and list(content):
                    self.containers[identity]=[{'Label':self.resolve(n.findtext('label','')),
                                               'Label2':self.resolve(n.findtext('label2','')),
                                               'Icon':n.findtext('icon','')}
                                              for n in content.findall('item')]
                else:self.containers[identity]=[]
        if self.name in ('Settings','Custom_1102'):self.selected[510]=5
        if self.name in ('SettingsCategory','DialogSettings','DialogAddonSettings'):
            self.native_settings()
        if self.name in ('MyPVRGuide','MyPVRChannels','Custom_1107','DialogPVRChannelsOSD','DialogPVRChannelGuide','MyPVRRecordings','MyPVRTimers'):
            self.containers[50]=self.channels[:6]
            self.containers[610]=[] if self.empty else self.channels[:5]
            self.containers[11]=self.channels[:5] if self.name.startswith('Dialog') else [{'Label':n} for n in ['All channels','Favourites']]
            self.containers[620]=[] if self.empty else [{'Label':f'Live channel {n+1}','art':{'thumb':str(ROOT/'fanart.jpg')},'properties':{'Starlight.Source':'YouTube'}} for n in range(5)]
        if self.name=='Custom_1106':self.selected[610]=0
        if self.name=='SettingsSystemInfo':
            self.native_labels.update({2:'Kodi 21.3 · Starlight',3:'System uptime: 3 hours',4:'Display: 1920 × 1080',
                                       5:'CPU usage: 8%',6:'Memory: 812 MB used',7:'Storage: 19 GB free',
                                       8:'Network: connected',9:'PVR backend: connected'})
            for n in range(10,14):self.native_labels[n]=''
            node=self.home.find(".//control[@id='30']");ET.SubElement(node,'visible').text='false'
        if self.name=='FileBrowser':
            self.native_labels.update({411:'Select a folder',412:'Home / Videos'})
            self.containers[450]=[{'Label':n,'Label2':'Folder','Icon':'DefaultFolder.png'} for n in ['..','Movies','TV shows','Recordings','Downloads']]
        if self.name=='SettingsProfile':self.containers[2]=[{'Label':'Master user','Label2':'Default profile','Icon':'DefaultUser.png'},{'Label':'Add profile…','Icon':'icons/settings.png'}]
        if self.name=='AddonBrowser':self.containers[50]=[{'Label':n,'Label2':d,'Icon':str(ROOT/'icon.png')} for n,d in [('My add-ons','Installed add-ons'),('Install from repository','Browse add-on repositories'),('Install from zip file','Choose an add-on package'),('Check for updates','Refresh installed add-ons')]]
        if self.name=='DialogAddonInfo':
            self.item={'Label':'Starlight','Icon':str(ROOT/'icon.png'),'AddonVersion':'2.0.0',
                       'AddonDescription':'Starlight brings smoked glass, warm gold focus, and Manrope type to Kodi. Home presents a library board and a shared hub rail.'}
            self.hero=self.item
            self.containers[50]=[]
        if self.name=='Pointer':self.focus=2
        if self.name=='FileManager':
            self.native_labels.update({101:'Home / Videos',102:'Home / Downloads',12:'4 folders',13:'4 folders'})
            for identity in (20,21):self.containers[identity]=[{'Label':n,'Label2':'Folder','Icon':'DefaultFolder.png'} for n in ['..','Movies','TV shows','Recordings']]
        if self.name=='DialogNumeric':self.native_labels.update({1:'Enter a number',4:'192'})
        if self.name=='DialogSlider':self.native_labels.update({10:'Zoom',12:'1.00'})

    def native_settings(self):
        title='Interface' if self.name=='SettingsCategory' else 'Add-on settings' if self.name=='DialogAddonSettings' else 'Playback settings'
        self.native_labels[2]=title
        self.native_labels[6]='Choose where the hub navigation appears. The rail opens when the rail has focus.'
        self.native_labels[20]='Standard'
        categories=['Skin','Regional','Screensaver','Master lock','Startup'] if self.name=='SettingsCategory' else ['General','Playback','Advanced']
        rows=[('Skin','Starlight',7),('Theme','Default',9),('Hub navigation','Left rail',9),('Ambient effects','On',8),('Visualiser','On',8),('Zoom','0%',13)]
        if self.name=='DialogAddonSettings':rows=[('Enabled','On',8),('Video quality','1080p',9),('Language','English',9),('Channel IDs','',12),('Reset defaults','',7)]
        if self.name=='DialogSettings':rows=[('View mode','Normal',9),('Zoom','1.00',13),('Audio stream','English · Stereo',9),('Subtitles','Off',8)]
        for group_id,template_id,records in [(3,10,[(t,'',10) for t in categories]),(5,7,rows)]:
            group=self.home.find(f".//control[@id='{group_id}']")
            for index,(title,value,kind) in enumerate(records):
                template=deepcopy(self.home.find(f".//control[@id='{kind}']"))
                template.set('id',str((-200 if group_id==3 else -180)+index))
                for old in template.findall('visible'):template.remove(old)
                ET.SubElement(template,'label').text=title
                ET.SubElement(template,'label2').text=value
                if kind==8:ET.SubElement(template,'selected').text='true' if value=='On' else 'false'
                group.append(template)

    def info(self,text):
        match=re.fullmatch(r'Window(?:\(home\))?\.Property\(([^)]+)\)',text.strip())
        if match:
            if match[1]=='Starlight.Hub':return 'livetv' if self.name.startswith(('MyPVR','DialogPVR')) or self.name=='Custom_1107' else 'settings'
            return self.properties.get(match[1],'')
        if text=='Container.FolderPath':return 'Add-ons'
        if text in ('Container(450).ListItem.Size','Container(450).ListItem.Date'):return ''
        if text=='ListItem.Progress':return self.item.get('Progress','0')
        if text.startswith('Control.GetLabel('):return self.native_labels.get(int(text[17:-1]),'')
        return super().info(text)

    def condition(self,expression):
        expression=expression.strip()
        if expression=='Player.HasVideo':return False
        if expression=='ListItem.InProgress':return True
        if expression=='ListItem.IsSelected':return self.item.get('Label')=='All channels'
        if re.fullmatch(r'System.HasAddon\([^)]+\)',expression):return self.installed
        if expression.startswith('System.Can'):return expression in ('System.CanPowerDown','System.CanReboot','System.CanSuspend')
        if expression=='System.ShowExitButton':return True
        return super().condition(expression)

    def draw(self,raw,origin=(0,0),parent=(1920,1080),opacity=1):
        node=deepcopy(raw)
        identity=int(node.get('id','0'))
        kind=node.get('type')
        if not self.condition(node.findtext('visible','true')):return
        if self.name=='Pointer' and identity!=self.focus:return
        if identity in self.native_labels:
            label=node.find('label')
            if label is None:label=ET.SubElement(node,'label')
            label.text=self.native_labels[identity]
        if kind=='epggrid':
            self.draw_guide(node,origin,opacity)
            return
        if kind in ('radiobutton','spincontrolex','sliderex','colorbutton','togglebutton'):
            node.set('type','button')
        if kind in ('radiobutton','spincontrolex','sliderex','colorbutton','togglebutton','button'):
            text=node.findtext('label','')
            label=node.find('label')
            if label is None:label=ET.SubElement(node,'label')
            label.text=''
            super().draw(node,origin,parent,opacity)
            x=origin[0]+self.number(node.findtext('left','0'));y=origin[1]+self.number(node.findtext('top','0'))
            w=self.number(node.findtext('width','1644'));h=self.number(node.findtext('height','64'))
            offset=self.number(node.findtext('textoffsetx','0'))
            self.draw(self.control('label',offset,0,w-2*offset,h,label=text,font=node.findtext('font','font_label_large'),align=node.findtext('align','center'),textcolor=node.findtext('textcolor','frost')), (x,y),(w,h),opacity)
            if kind=='radiobutton':
                enabled=self.condition(node.findtext('selected','true'))
                self.draw(self.control('image',w-112,(h-38)//2,68,38,texture='settings/toggle_'+('on' if enabled else 'off')+'.png'),(x,y),(w,h),opacity)
            elif node.findtext('label2'):
                self.draw(self.control('label',w-580,0,540,h,label=node.findtext('label2'),align='right',font='font_body',textcolor='mist'),(x,y),(w,h),opacity)
            return
        if kind=='slider':
            x=origin[0]+self.number(node.findtext('left','0'));y=origin[1]+self.number(node.findtext('top','0'))
            w=self.number(node.findtext('width','864'))
            self.draw(self.control('image',x,y+8,w,8,texture='progress_track.png'))
            self.draw(self.control('image',x+w//2-12,y,24,24,texture='palette_frost.png'))
            return
        super().draw(node,origin,parent,opacity)

    @staticmethod
    def control(kind,x,y,w,h,**fields):
        node=ET.Element('control',type=kind)
        for key,value in dict(left=x,top=y,width=w,height=h,**fields).items():ET.SubElement(node,key).text=str(value)
        return node

    def draw_guide(self,node,origin,opacity):
        x=origin[0]+self.number(node.findtext('left'));y=origin[1]+self.number(node.findtext('top'))
        w=self.number(node.findtext('width'));h=self.number(node.findtext('height'))
        channelw=int(node.find('channellayout').get('width'));rowh=int(node.find('channellayout').get('height'))
        rulerh=int(node.find('rulerlayout').get('height'));gridw=w-channelw
        t0=self.guide['t0'];span=int(node.findtext('timeblocks'))*300
        old=self.item
        self.item={'Label':'Thu 26 Feb'}
        for child in node.find('rulerdatelayout'):self.draw(child,(x,y),(channelw,rulerh),opacity)
        for n in range(span//1800):
            self.item={'Label':datetime.fromtimestamp(t0+n*1800,tz=timezone.utc).strftime('%H:%M')}
            for child in node.find('rulerlayout'):self.draw(child,(x+channelw+round(n*1800*gridw/span),y),(230,rulerh),opacity)
        for n,row in enumerate(self.guide['channels'][:(h-rulerh)//rowh]):
            self.item=self.channel(row)
            for child in node.find('channellayout'):self.draw(child,(x,y+rulerh+n*rowh),(channelw,rowh),opacity)
            for index,tag in enumerate(row['tags']):
                start=max(t0,tag['start']);end=min(t0+span,tag['end'])
                if end<=start:continue
                left=round((start-t0)*gridw/span);width=round((end-start)*gridw/span)
                self.item=dict(self.item,Label=tag['title'],EpisodeName=tag['ep'],StartTime=datetime.fromtimestamp(tag['start'],tz=timezone.utc).strftime('%H:%M'))
                layout=deepcopy(node.find('focusedlayout' if n==0 and index==0 else 'itemlayout'))
                # Kodi GUIListItemLayout::SetWidth enlarges each cell's child widths.
                delta=width-int(layout.get('width'))
                for child in layout:
                    extent=child.find('width')
                    if extent is not None:extent.text=str(max(1,int(extent.text)+delta))
                    self.draw(child,(x+channelw+left,y+rulerh+n*rowh),(width,rowh),opacity)
        now=x+channelw+round(1020*gridw/span)
        self.draw(self.control('image',now,y,2,h,texture='progress_gold.png'))
        self.draw(self.control('image',now-14,y-10,30,30,texture='playhead_glow.png'))
        self.item=old

    def save(self,output):
        for control in self.home.findall('controls/control'):self.draw(control)
        output.parent.mkdir(parents=True,exist_ok=True)
        self.canvas.convert('RGB').save(output)
        print(f'{self.name}: {output} (1920x1080; expanded XML, native fixtures)')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--art',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/tmp/starlight-step6'))
    parser.add_argument('--window',choices=WINDOWS)
    parser.add_argument('--section',default='Appearance',choices=['Hub','Widgets','Appearance','Music','Screensaver'])
    parser.add_argument('--empty',action='store_true')
    parser.add_argument('--setting',action='append',default=[])
    args=parser.parse_args()
    for name in [args.window] if args.window else WINDOWS:
        preview=SettingsPreview(args.art,name,dict(s.split('=',1) for s in args.setting),args.section,args.empty)
        preview.save(args.output/(name+'.png'))
