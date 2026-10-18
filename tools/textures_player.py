"""Original player textures. No spectrum simulation ships in the skin."""
import math
from PIL import Image, ImageDraw, ImageFilter
from build_branding import rasterize


def player_textures():
    textures = {}
    size, scale = 600, 3
    ring = Image.new('RGBA', (size * scale, size * scale))
    draw = ImageDraw.Draw(ring)
    for n in range(160):
        angle = n * math.tau / 160
        x, y = 300 + 180 * math.cos(angle), 300 + 180 * math.sin(angle)
        draw.ellipse(((x-1.7)*scale, (y-1.7)*scale, (x+1.7)*scale, (y+1.7)*scale), fill=(245,194,122,140))
    textures['player/dotted_ring.png'] = ring.resize((size,size),Image.Resampling.LANCZOS)
    halo = Image.new('RGBA',(600,600))
    ImageDraw.Draw(halo).ellipse((125,125,475,475),outline=(245,194,122,60),width=12)
    textures['player/halo.png'] = halo.filter(ImageFilter.GaussianBlur(22))
    rim = Image.new('RGBA',(972,972))
    ImageDraw.Draw(rim).ellipse((3,3,968,968),outline=(245,194,122,155),width=5)
    textures['player/cover_rim.png'] = rim.resize((324,324),Image.Resampling.LANCZOS)
    shade = Image.new('RGBA',(4,270))
    for y in range(270):
        alpha = max(.6 * max(0,1-y/65), .92 * max(0,(y-140)/130))
        ImageDraw.Draw(shade).line((0,y,4,y),fill=(3,5,10,round(255*alpha)))
    textures['player/video_shade.png'] = shade
    paths = {
        'pause':'<path d="M8 5v14M16 5v14" stroke-width="4"/>',
        'previous':'<path d="M19 20 9 12l10-8ZM5 19V5"/>',
        'next':'<path d="m5 4 10 8-10 8ZM19 5v14"/>',
        'repeat':'<path d="m17 2 4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3"/>',
        'repeat_one':'<path d="m17 2 4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3M11 10l2-1v6"/>',
        'heart':'<path d="M12 20S3 15 3 9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 11-9 11Z"/>',
        'heart_filled':'<path d="M12 20S3 15 3 9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 6-9 11-9 11Z" fill="#f4f7fb"/>',
        'down':'<path d="m6 9 6 6 6-6"/>',
        'rewind':'<path d="M4 9a8 8 0 1 1 0 6M4 3v6h6"/>',
        'forward':'<path d="M20 9a8 8 0 1 0 0 6M20 3v6h-6"/>',
        'subtitles':'<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M7 12h4m2 0h4M7 16h10"/>',
        'chapters':'<path d="M4 6h16M4 12h16M4 18h10"/>',
        'album':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
        'playlist':'<path d="M3 6h12M3 12h12M3 18h7M18 13v8M14 17h8"/>',
        'radio':'<circle cx="12" cy="12" r="2"/><path d="M8 16a6 6 0 0 1 0-8m8 0a6 6 0 0 1 0 8M5 19a10 10 0 0 1 0-14m14 0a10 10 0 0 1 0 14"/>',
        'artist':'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
        'follow':'<circle cx="10" cy="8" r="4"/><path d="M2 21a8 8 0 0 1 13-6M19 14v6M16 17h6"/>',
    }
    for name, path in paths.items():
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="#f4f7fb" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + path + '</svg>'
        textures['player/' + name + '.png'] = rasterize(svg,96,96).resize((48,48),Image.Resampling.LANCZOS)
    album = Image.new('RGBA',(320,320),(12,18,28,255))
    icon = textures['player/album.png'].resize((160,160),Image.Resampling.LANCZOS)
    album.alpha_composite(icon,(80,80))
    textures['player/album_placeholder.png'] = album
    textures['DefaultAlbumCover.png'] = album.copy()
    textures['player/slider_track.png'] = Image.new('RGBA', (132,64))
    for name, color in [('on',(245,194,122,255)),('off',(154,166,184,255))]:
        toggle=Image.new('RGBA',(32,32))
        ImageDraw.Draw(toggle).ellipse((4,4,28,28),outline=color,width=2)
        if name=='on': ImageDraw.Draw(toggle).ellipse((10,10,22,22),fill=color)
        textures['player/toggle_'+name+'.png']=toggle
    return textures
