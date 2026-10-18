"""Procedural step 6 controls and the approved startup mark."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from build_branding import horizon, rasterize, splash_stars


def build(output):
    target = Path(output) / 'settings'
    target.mkdir(parents=True, exist_ok=True)
    for enabled in (False, True):
        canvas = Image.new('RGBA', (272, 152))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((0, 0, 271, 151), radius=76,
                               fill='#f4f7fb' if enabled else (244,247,251,46))
        left = 132 if enabled else 16
        draw.ellipse((left,16,left+119,135),fill='#05070c' if enabled else '#abb3c0')
        canvas.resize((68,38),Image.Resampling.LANCZOS).save(target / ('toggle_on.png' if enabled else 'toggle_off.png'))
    for direction in ('left','right'):
        path='M15 5 7 12 15 19' if direction=='left' else 'M9 5 17 12 9 19'
        rasterize(f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><path d="{path}" fill="none" stroke="#f4f7fb" stroke-width="2"/></svg>',48,48).save(target / ('arrow_'+direction+'.png'))
    rasterize('<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="13" rx="2" fill="none" stroke="#f4f7fb" stroke-width="1.7"/><path d="m8 2 4 4 4-4M8 22h8" fill="none" stroke="#f4f7fb" stroke-width="1.7"/></svg>',48,48).save(Path(output)/'icons/livetv.png')
    native_paths = {
        'DefaultFolder': '<path d="M3 6h7l2 3h17v19H3Z"/>',
        'DefaultFolderBack': '<path d="M3 6h7l2 3h17v19H3Z M20 15l-5 4 5 4 M15 19h10"/>',
        'DefaultFile': '<path d="M8 3h11l7 7v20H8Z M19 3v8h7 M12 17h10 M12 22h10"/>',
        'DefaultPicture': '<rect x="3" y="4" width="26" height="24" rx="3"/><circle cx="11" cy="12" r="3"/><path d="m4 26 9-8 5 4 5-7 6 7"/>',
        'DefaultUser': '<circle cx="16" cy="10" r="6"/><path d="M4 30a12 12 0 0 1 24 0"/>',
    }
    for name, path in native_paths.items():
        source='<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 32 32" fill="none" stroke="#f4f7fb" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'+path+'</svg>'
        rasterize(source,96,96).save(Path(output)/(name+'.png'))
    for name, icon in {'DefaultTVShows':'tv','DefaultVideo':'movies','DefaultVideoDeleted':'movies',
                       'DefaultAudio':'music','DefaultMusicSongs':'music','DefaultPlaylist':'music',
                       'DefaultScript':'settings','DefaultFavourites':'watched',
                       'DefaultAddon':'discover'}.items():
        Image.open(Path(output)/'icons'/(icon+'.png')).save(Path(output)/(name+'.png'))
    for state in range(1,5):
        fill='#f5c27a' if state in (2,3,4) else '#f4f7fb'
        source=f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="48"><path d="M4 3 4 36 13 28 20 43 27 39 20 25 32 25Z" fill="{fill}" stroke="#03050a" stroke-width="2"/></svg>'
        rasterize(source,40,48).save(target / f'pointer_{state}.png')
    # EPG stretches the progress texture from the ruler origin to the current time.
    # A transparent centre and a fixed right border leave a line at the current time.
    progress=Image.new('RGBA',(64,64))
    draw=ImageDraw.Draw(progress)
    draw.line((62,0,62,63),fill='#f5c27a',width=2)
    draw.ellipse((57,0,63,6),fill='#fff6e4')
    progress.save(target / 'guide_now.png')
    for name, alpha in [('guide_cell',13),('guide_airing',26)]:
        canvas=Image.new('RGBA',(64,64))
        ImageDraw.Draw(canvas).rounded_rectangle((0,0,63,63),radius=16,fill=(244,247,251,alpha),outline=(255,255,255,18),width=1)
        canvas.save(target / (name+'.png'))
    horizon((960,720),120).save(target / 'splash_horizon.png')
    splash_stars().save(target / 'splash_stars.png')
    canvas=Image.new('RGBA',(680,80))
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(str(Path(__file__).resolve().parents[1]/'fonts/manrope-light.ttf'),40)
    widths=[draw.textlength(c,font=font) for c in 'STARLIGHT']
    x=(680-sum(widths)-8*20)/2
    for character,width in zip('STARLIGHT',widths):
        draw.text((x,16),character,font=font,fill=(244,247,251,217),anchor='lt')
        x+=width+20
    canvas.save(target / 'splash_wordmark.png')
