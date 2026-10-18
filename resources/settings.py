"""Apply the native Guide action required by the Starlight programme menu."""
import json
import sys

import xbmc
import xbmcgui


def guide():
    # EPG grid clicks bypass XML onclick. Kodi owns the select action.
    # Kodi 21.3: GUIWindowPVRGuide.cpp:437; system/settings/settings.xml.
    def request(method, **params):
        response = json.loads(xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc':'2.0','id':1,'method':method,'params':params})))
        if 'error' in response:
            raise RuntimeError('Kodi rejected the Guide action setting')
        return response.get('result')
    try:
        current = request('Settings.GetSettingValue', setting='epg.selectaction')
        if not isinstance(current, dict) or 'value' not in current:
            raise RuntimeError('Kodi returned no Guide action setting')
        if current['value'] != 0:
            if request('Settings.SetSettingValue', setting='epg.selectaction', value=0) is not True:
                raise RuntimeError('Kodi did not save the Guide action setting')
    except (RuntimeError, ValueError, TypeError) as error:
        xbmc.log('Starlight Guide: '+str(error),xbmc.LOGERROR)
        xbmcgui.Dialog().notification(xbmc.getLocalizedString(31665),xbmc.getLocalizedString(31686))


if __name__=='__main__' and sys.argv[1:] == ['guide']:
    guide()
