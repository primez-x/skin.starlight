"""Step 6 boundary checks for native windows, settings and provider hooks.

Failure cases: absent native IDs, wrong control types, missing setting options,
obsolete placeholders, automatic dependency installation, blocked startup,
invalid navigation targets, and synthetic YouTube schedule fields.
"""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = ['SkinSettings', 'Settings', 'SettingsCategory', 'SettingsSystemInfo',
           'SettingsProfile', 'DialogSettings', 'DialogAddonSettings', 'FileBrowser',
           'DialogButtonMenu', 'DialogAddonInfo', 'AddonBrowser', 'MyPVRGuide',
           'MyPVRChannels', 'MyPVRRecordings', 'MyPVRTimers', 'DialogPVRInfo',
           'DialogPVRChannelsOSD', 'DialogPVRChannelGuide', 'Startup', 'Pointer',
           'Custom_1102', 'Custom_1106', 'Custom_1107', 'FileManager', 'DialogNumeric', 'DialogSlider']


def expanded(name):
    import sys
    sys.path.insert(0, str(ROOT / 'resources/lib'))
    from skin_xml import expand
    includes = {node.get('name'): node for path in (ROOT / '1080i').glob('Includes*.xml')
                for node in ET.parse(path).iter('include') if node.get('name')}
    return expand(ET.parse(ROOT / '1080i' / (name + '.xml')).getroot(), includes, lambda _: True)


class Step6Tests(unittest.TestCase):
    def test_all_windows_parse_and_expand(self):
        for name in WINDOWS:
            with self.subTest(window=name):
                tree = expanded(name)
                self.assertGreater(len(list(tree.iter('control'))), 0)

    def test_native_settings_templates_cover_every_type(self):
        types = {3:'grouplist',5:'grouplist',7:'button',8:'radiobutton',9:'spincontrolex',
                 10:'togglebutton',11:'image',12:'edit',13:'sliderex',14:'label',15:'colorbutton'}
        for name in ['SettingsCategory','DialogSettings','DialogAddonSettings']:
            controls = {int(n.get('id')):n for n in expanded(name).iter('control') if n.get('id')}
            for identity, kind in types.items():
                self.assertEqual(controls[identity].get('type'),kind,(name,identity))
            self.assertEqual(controls[3].findtext('orientation'),'horizontal')
            self.assertEqual(controls[5].findtext('orientation'),'vertical')
            for identity in [2,6,20,28,29,30]: self.assertIn(identity,controls)

    def test_skin_options_have_complete_native_actions(self):
        text = (ROOT / '1080i/Custom_1106.xml').read_text()
        for key, values in {'Hub.Navigation':['rail','icons','top_left','top_centre'],
                            'Home.Art.Mode':['blurred','bound']}.items():
            for value in values: self.assertIn(f'Skin.SetString({key},{value})',text)
        for key in ['Continue','Movies','Next','Episodes']:
            for value in ['board','hero','landscape','poster','square']:
                self.assertIn(f'Skin.SetString(Home.{key}.Layout,{value})',text)
        self.assertIn('ReloadSkin()',text)
        skin = ET.tostring(expanded('SkinSettings'),encoding='unicode')
        self.assertIn('!Skin.HasSetting(AmbientEffects.Disabled)',skin)
        self.assertIn('Skin.ToggleSetting(AmbientEffects.Disabled)',skin)
        self.assertIn('Addon.Default.Set(xbmc.ui.screensaver)',skin)
        self.assertIn('Player.Visualiser.Disabled',skin)
        self.assertNotIn('InstallAddon',skin)

    def test_settings_placeholder_becomes_the_real_home(self):
        tree = expanded('Custom_1102')
        self.assertEqual(tree.findtext('defaultcontrol'),'510')
        self.assertIn('SetProperty(Starlight.Hub,settings,home)',[n.text for n in tree.findall('onload')])
        self.assertTrue(any(n.get('id')=='9000' for n in tree.iter('control')))
        self.assertTrue(any(n.get('type')=='panel' and n.get('id')=='510' for n in tree.iter('control')))

    def test_file_and_addon_native_ids(self):
        for name, ids in {'FileBrowser':{411,412,413,414,415,416,450,451},
                          'DialogAddonInfo':{6,7,8,9,10,12,13,14,50},
                          'SettingsProfile':{2,4,5},'SettingsSystemInfo':set(range(2,14))|set(range(94,101)),
                          'FileManager':{20,21,101,102,12,13},'DialogNumeric':{1,4}|set(range(10,24)),
                          'DialogSlider':{10,11,12},'AddonBrowser':{50}}.items():
            controls={int(n.get('id')) for n in expanded(name).iter('control') if n.get('id')}
            self.assertLessEqual(ids,controls,name)

    def test_guide_uses_native_grid_and_half_hour_ruler(self):
        grid=expanded('MyPVRGuide').find(".//control[@type='epggrid']")
        self.assertIsNotNone(grid)
        self.assertEqual(grid.get('id'),'50')
        self.assertEqual(grid.findtext('rulerunit'),'6')
        for tag in ['rulerlayout','channellayout','focusedchannellayout','itemlayout','focusedlayout','progresstexture']:
            self.assertIsNotNone(grid.find(tag),tag)
        self.assertIsNone(grid.find('content'))
        for name in ['DialogPVRChannelsOSD','DialogPVRChannelGuide']:
            self.assertIsNotNone(expanded(name).find(".//control[@type='list'][@id='11']"))
        info=expanded('DialogPVRInfo')
        ids={int(n.get('id')) for n in info.iter('control') if n.get('id')}
        self.assertLessEqual(set(range(4,12)),ids)

    def test_recent_channels_and_youtube_contract(self):
        tree=expanded('Custom_1107')
        contents=[n.text for n in tree.iter('content')]
        self.assertIn('pvr://channels/tv/All channels/?view=lastplayed',contents)
        self.assertIn('plugin://plugin.video.smarttube/live_now',contents)
        text=ET.tostring(tree,encoding='unicode')
        self.assertIn('System.HasAddon(plugin.video.smarttube)',text)
        self.assertIn('ListItem.Property(Starlight.Source)',text)
        self.assertIn('ListItem.ChannelNumberLabel',text)
        home=(ROOT / '1080i/Home.xml').read_text()
        self.assertIn('LiveTVHomeWidget',home)
        rail=(ROOT / '1080i/Includes_Home.xml').read_text()
        self.assertIn('ActivateWindow(11107)',rail)

    def test_live_tile_context_uses_the_actual_lifted_card_bounds(self):
        import sys
        sys.path.insert(0,str(ROOT/'resources/lib'))
        from skin_xml import card_rect
        constants={n.get('name'):n.text for n in ET.parse(ROOT/'1080i/Includes_Constants.xml').iter('constant')}
        tree=expanded('Custom_1107')
        def condition(expression):
            return not any(value in expression for value in ['top_left','top_centre','ControlGroup(9000)'])
        self.assertEqual(card_rect(tree,610,1,0,constants,condition),(515,369,330,186))
        self.assertIsNotNone(tree.find(".//control[@id='5502']"))
        helper=(ROOT/'resources/info.py').read_text()
        self.assertIn('11107',helper)
        self.assertIn('570',helper)

    def test_splash_is_nonblocking_and_pointer_states_exist(self):
        tree=expanded('Startup')
        text=ET.tostring(tree,encoding='unicode')
        self.assertIn('AlarmClock(StarlightStartup,ReplaceWindow(Home),00:00:01,silent)',text)
        self.assertNotIn('Sleep(',text)
        self.assertNotIn('RunScript(',text)
        self.assertIn('CancelAlarm(StarlightStartup,true)',text)
        ids={int(n.get('id')) for n in expanded('Pointer').iter('control') if n.get('id')}
        self.assertLessEqual(set(range(1,5)),ids)


if __name__=='__main__': unittest.main()
