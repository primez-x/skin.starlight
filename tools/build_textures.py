#!/usr/bin/env python3
"""Render foundation PNGs with Pillow. Geometry comes from Includes_Constants.xml."""
import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from build_branding import horizon, rasterize
from textures_library import build_library_textures

ROOT = Path(__file__).resolve().parents[1]
SCALE = 4
FROST = (244, 247, 251)
GOLD = (245, 194, 122)
CONSTANTS = {node.get('name'): int(node.text) for node in
             ET.parse(ROOT / '1080i/Includes_Constants.xml').iter('constant')}


def rgba(rgb, alpha):
    return (*rgb, round(alpha * 255))


def mask(size, radius, inset=0):
    canvas = Image.new('L', (size[0] * SCALE, size[1] * SCALE))
    ImageDraw.Draw(canvas).rounded_rectangle(
        (inset * SCALE, inset * SCALE,
         (size[0] - inset) * SCALE - 1, (size[1] - inset) * SCALE - 1),
        radius=max(0, radius - inset) * SCALE, fill=255)
    return canvas


def gradient(size, stops):
    canvas = Image.new('RGBA', (size[0] * SCALE, size[1] * SCALE))
    draw = ImageDraw.Draw(canvas)
    for y in range(canvas.height):
        pos = y / (canvas.height - 1)
        left, right = next((a, b) for a, b in zip(stops, stops[1:]) if a[0] <= pos <= b[0])
        blend = (pos - left[0]) / (right[0] - left[0])
        color = tuple(round(a + (b - a) * blend) for a, b in zip(left[1], right[1]))
        draw.line((0, y, canvas.width, y), fill=color)
    return canvas


def surface(size, radius, focus=False, selected=False):
    if selected:
        canvas = Image.new('RGBA', (size[0] * SCALE, size[1] * SCALE), rgba(FROST, .16))
    elif focus:
        canvas = gradient(size, [(0, rgba((255, 255, 255), .36)),
                                 (.7, rgba((255, 255, 255), .14)), (1, rgba(GOLD, .18))])
    else:
        canvas = Image.new('RGBA', (size[0] * SCALE, size[1] * SCALE), rgba((8, 12, 20), .42))
        canvas = Image.alpha_composite(canvas, gradient(size, [
            (0, rgba((255, 255, 255), .13)), (1, rgba((255, 255, 255), .05))]))
    shape = mask(size, radius)
    canvas.putalpha(ImageChops.multiply(canvas.getchannel('A'), shape))
    edge = ImageChops.subtract(shape, mask(size, radius, 1))
    rim = Image.new('RGBA', canvas.size, (255, 255, 255, 0))
    rim.putalpha(edge.point(lambda a: round(a * (.3 if focus else .16 if selected else .08))))
    canvas = Image.alpha_composite(canvas, rim)
    if not selected:
        # Shifted masks leave a one-pixel curved top rim and the warm focus foot.
        band = ImageChops.subtract(shape, mask(size, radius, 1.5 if focus else 1))
        rim = Image.new('RGBA', canvas.size)
        draw = ImageDraw.Draw(rim)
        draw.rectangle((0, 0, rim.width, round(radius * SCALE)),
                       fill=rgba((255, 255, 255), .85 if focus else .35))
        if focus:
            draw.rectangle((0, (size[1] - radius) * SCALE, rim.width, rim.height), fill=rgba(GOLD, .85))
        rim.putalpha(ImageChops.multiply(rim.getchannel('A'), band))
        canvas = Image.alpha_composite(canvas, rim)
    return canvas.resize(size, Image.Resampling.LANCZOS)


def glow(size, radius):
    padding = CONSTANTS['glow_padding']
    full = (size[0] + padding * 2, size[1] + padding * 2)
    silhouette = Image.new('L', (full[0] * SCALE, full[1] * SCALE))
    silhouette.paste(mask(size, radius), (padding * SCALE, (padding + 14) * SCALE))
    silhouette = silhouette.filter(ImageFilter.GaussianBlur(16 * SCALE))
    cutout = Image.new('L', silhouette.size)
    cutout.paste(mask(size, radius), (padding * SCALE, padding * SCALE))
    silhouette = ImageChops.subtract(silhouette, cutout).point(lambda a: round(a * .7))
    canvas = Image.new('RGBA', silhouette.size, (*GOLD, 0))
    canvas.putalpha(silhouette)
    return canvas.resize(full, Image.Resampling.LANCZOS)


def point_sprite(twinkle=False):
    size = 64
    canvas = Image.new('RGBA', (size * SCALE, size * SCALE))
    halo = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(halo)
    draw.ellipse((20 * SCALE, 20 * SCALE, 44 * SCALE, 44 * SCALE), fill=rgba(GOLD, .65))
    canvas = Image.alpha_composite(canvas, halo.filter(ImageFilter.GaussianBlur(7 * SCALE)))
    draw = ImageDraw.Draw(canvas)
    if twinkle:
        points = [(32, 12), (34, 29), (48, 32), (34, 34), (32, 52), (30, 34), (16, 32), (30, 29)]
        draw.polygon([(x * SCALE, y * SCALE) for x, y in points], fill=rgba(FROST, .95))
    else:
        draw.ellipse((28 * SCALE, 28 * SCALE, 36 * SCALE, 36 * SCALE), fill=(255, 246, 228, 255))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def busy_frame(frame, orbit=True):
    size = 96
    canvas = horizon((size*SCALE,size*SCALE), 13*SCALE).copy()
    if orbit:
        angle = 2 * math.pi * frame / 24
        x, y = 48 + 20 * math.cos(angle), 48 + 23 * math.sin(angle)
        point = point_sprite().resize((40 * SCALE, 40 * SCALE), Image.Resampling.LANCZOS)
        canvas.alpha_composite(point, (round((x - 20) * SCALE), round((y - 20) * SCALE)))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


ICON_PATHS = {
    'search': '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>',
    'home': '<path d="m3 10 9-7 9 7M5 9v12h5v-7h4v7h5V9"/>',
    'movies': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4m-4 6h4m10-6h4m-4 6h4"/>',
    'tv': '<rect x="3" y="5" width="18" height="13" rx="2"/><path d="M8 22h8m-4-4v4"/>',
    'music': '<path d="M9 18V5l11-2v13M9 9l11-2"/><ellipse cx="6" cy="18" rx="3" ry="2.5"/><ellipse cx="17" cy="16" rx="3" ry="2.5"/>',
    'discover': '<circle cx="12" cy="12" r="9"/><path d="m16 8-2.5 5.5L8 16l2.5-5.5Z"/>',
    'settings': '<circle cx="12" cy="12" r="3.3"/><path d="m10 2-.6 3-2 .9-2.7-1.1-2 3.5L5 10v3l-2.3 1.7 2 3.5 2.7-1.1 2 .9.6 3h4l.6-3 2-.9 2.7 1.1 2-3.5L19 13v-3l2.3-1.7-2-3.5-2.7 1.1-2-.9L14 2Z"/>',
    'play': '<path d="m7 4 13 8-13 8Z" fill="#f4f7fb" stroke="none"/>',
    'restart': '<path d="M4 9a8 8 0 1 1 0 6M4 3v6h6"/>',
    'watched': '<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
    'check': '<path d="m5 12 4 4L19 6"/>',
    'more': '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    'shuffle': '<path d="m16 3 5 0v5M3 21 21 3M21 16v5h-5M14 14l7 7M3 3l6 6"/>',
    'speaker': '<path d="M3 9v6h4l5 4V5L7 9ZM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>',
    'muted': '<path d="M3 9v6h4l5 4V5L7 9ZM16 9l6 6M22 9l-6 6"/>',
    'notification': '<path d="M6 8a6 6 0 0 1 12 0c0 6 3 9 3 9H3s3-3 3-9M10 21h4"/>',
    'warning': '<path d="m12 3 10 18H2ZM12 9v5M12 17v.5"/>',
    'error': '<circle cx="12" cy="12" r="9"/><path d="m8 8 8 8M16 8l-8 8"/>',
}


def icon_svg(name):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            'width="48" height="48" fill="none" stroke="#f4f7fb" stroke-width="1.7" '
            'stroke-linecap="round" stroke-linejoin="round">' + ICON_PATHS[name] + '</svg>')


def backdrop_shade():
    canvas = Image.new('RGBA', (480, 270))
    pixels = canvas.load()
    for y in range(270):
        for x in range(480):
            left = .55 * max(0, 1 - x / 336)
            bottom = .85 * max(0, (y / 269 - .55) / .45)
            pixels[x, y] = (3, 5, 10, round((1 - (1 - left) * (1 - bottom)) * 255))
    return canvas


def art_falloff():
    canvas = Image.new('RGBA', (500, 300), (255, 255, 255, 0))
    pixels = canvas.load()
    for y in range(300):
        for x in range(500):
            radius = math.hypot((x / 500 - .72) / .62, (y / 300 - .28) / .70)
            pixels[x, y] = (255, 255, 255, round(255 * min(1, max(0, (1 - radius) / .55))))
    return canvas


def feature_focus():
    canvas = surface((104, 104), 26, focus=True)
    inner = mask((104, 104), 26, 2).resize(canvas.size)
    alpha = canvas.getchannel('A')
    canvas.putalpha(Image.composite(alpha.point(lambda a: round(a * .3)), alpha, inner))
    return canvas


def feature_shade():
    size = (880, 495)
    canvas = Image.new('RGBA', size)
    pixels = canvas.load()
    for y in range(size[1]):
        pos = y / (size[1] - 1)
        bottom = .9 - .35 * pos / .35 if pos <= .35 else .55 * max(0, (.62 - pos) / .27)
        for x in range(size[0]):
            left = .5 * max(0, 1 - x / ((size[0] - 1) * .55))
            pixels[x, size[1] - 1 - y] = (3, 5, 10, round((1 - (1 - left) * (1 - bottom)) * 255))
    shape = mask(size, 26).resize(size, Image.Resampling.LANCZOS)
    canvas.putalpha(ImageChops.multiply(canvas.getchannel('A'), shape))
    return canvas


def person_art(rim=False):
    size = 396 if rim else 300
    canvas = Image.new('RGBA', (size * SCALE, size * SCALE))
    draw = ImageDraw.Draw(canvas)
    if rim:
        halo = Image.new('RGBA', canvas.size)
        ImageDraw.Draw(halo).ellipse((48*SCALE, 48*SCALE, 348*SCALE, 348*SCALE),
                                     outline=rgba(GOLD, .5), width=8*SCALE)
        canvas = halo.filter(ImageFilter.GaussianBlur(18*SCALE))
        ImageDraw.Draw(canvas).ellipse((48*SCALE, 48*SCALE, 348*SCALE, 348*SCALE),
                                        outline=rgba(GOLD, .55), width=2*SCALE)
    else:
        draw.ellipse((0, 0, size*SCALE-1, size*SCALE-1), fill=(15, 22, 34, 255))
        draw.ellipse((105*SCALE, 60*SCALE, 195*SCALE, 150*SCALE), fill=rgba(FROST, .3))
        draw.ellipse((55*SCALE, 170*SCALE, 245*SCALE, 360*SCALE), fill=rgba(FROST, .3))
    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def corner_shade():
    canvas = Image.new('RGBA', (200, 100))
    for y in range(canvas.height):
        for x in range(canvas.width):
            alpha = max(0, 1-math.hypot(x/200, y/100)) * .8
            canvas.putpixel((x,y), (3,5,10,round(255*alpha)))
    return canvas


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    textures = {
        'glass_panel.png': surface((96, 96), CONSTANTS['panel_border']),
        'glass_capsule.png': surface((132, 68), CONSTANTS['capsule_border']),
        'focus_button.png': surface((132, 68), CONSTANTS['focus_border'], focus=True),
        'focus_glow.png': glow((132, 68), CONSTANTS['focus_border']),
        'focus_card.png': surface((68, 68), CONSTANTS['card_border'], focus=True),
        'focus_card_glow.png': glow((68, 68), CONSTANTS['card_border']),
        'frost_fill.png': surface((132, 68), CONSTANTS['capsule_border'], selected=True),
        'playhead_glow.png': point_sprite(),
        'progress_playhead.png': point_sprite().crop((16, 16, 48, 48)).resize((8, 8), Image.Resampling.LANCZOS),
        'star_soft.png': point_sprite(),
        'star_twinkle.png': point_sprite(twinkle=True),
        'background_void.png': Image.new('RGBA', (1, 1), (3, 5, 10, 255)),
        'dim_soft.png': Image.new('RGBA', (1, 1), (0, 0, 0, 89)),
        'dim_modal.png': Image.new('RGBA', (1, 1), (0, 0, 0, 153)),
        'home_shade.png': backdrop_shade(),
        'art_falloff.png': art_falloff(),
        'card_shade.png': gradient((220, 124), [(0, (3, 5, 10, 0)), (.38, (3, 5, 10, 0)),
                                               (.65, (3, 5, 10, 140)), (1, (3, 5, 10, 230))]).resize((220, 124)),
        'focus_feature.png': feature_focus(),
        'feature_shade.png': feature_shade(),
        'focus_feature_glow.png': glow((104, 104), 26),
        'feature_mask.png': Image.new('RGBA', (880, 495), (255, 255, 255, 255)),
        'landing_glint.png': point_sprite(twinkle=True).resize((96, 16)),
        'play_capsule.png': surface((132, 50), 25, focus=True),
        'glass_rail.png': surface((136, 136), 34),
        'person_rim.png': person_art(rim=True),
        'person_placeholder.png': person_art(),
        'status_corner.png': corner_shade(),
        'keyboard_fade.png': gradient((4, 270), [(0, (3,5,10,0)), (.4, (3,5,10,51)),
                                                 (.62, (3,5,10,191)), (1, (3,5,10,220))]).resize((4,270)),
        'sweep.png': point_sprite().resize((480, 8)),
        'keyboard_done.png': Image.new('RGBA', (132, 68), (*FROST, 255)),
        'busy_horizon.png': busy_frame(0, orbit=False),
    }
    textures['feature_mask.png'].putalpha(mask((880, 495), 26).resize((880, 495)))
    textures['keyboard_done.png'].putalpha(mask((132, 68), 28).resize((132, 68)))
    for name, size in [('landscape', (335, 189)), ('poster', (160, 240)), ('wide', (410, 231)), ('square', (230, 230))]:
        shape = Image.new('RGBA', size, (255, 255, 255, 255))
        shape.putalpha(mask(size, 16).resize(size, Image.Resampling.LANCZOS))
        textures['home_' + name + '_mask.png'] = shape
    for name in ICON_PATHS:
        textures['icons/' + name + '.png'] = rasterize(icon_svg(name), 96, 96).resize((48, 48), Image.Resampling.LANCZOS)
    for kind, icon in [('Info', 'notification'), ('Warning', 'warning'), ('Error', 'error')]:
        textures['DefaultIcon' + kind + '.png'] = textures['icons/' + icon + '.png'].copy()
    for name, size, radius, color in [
            ('card_mask.png', (68, 68), CONSTANTS['card_border'], (255, 255, 255, 255)),
            ('circle_mask.png', (128, 128), 64, (255, 255, 255, 255)),
            ('progress_track.png', (132, 8), CONSTANTS['progress_border'], rgba(FROST, .16)),
            ('progress_frost.png', (132, 8), CONSTANTS['progress_border'], (*FROST, 255)),
            ('progress_gold.png', (132, 8), CONSTANTS['progress_border'], (*GOLD, 255))]:
        canvas = Image.new('RGBA', (size[0] * SCALE, size[1] * SCALE), color)
        canvas.putalpha(ImageChops.multiply(canvas.getchannel('A'), mask(size, radius)))
        textures[name] = canvas.resize(size, Image.Resampling.LANCZOS)
    for name, color in [('void', (3, 5, 10)), ('frost', FROST),
                        ('mist', (154, 166, 184)), ('gold', GOLD)]:
        canvas = Image.new('RGBA', (128 * SCALE, 128 * SCALE), (*color, 255))
        canvas.putalpha(mask((128, 128), 64))
        if name == 'void':
            outline = ImageChops.subtract(mask((128, 128), 64), mask((128, 128), 64, 2))
            rim = Image.new('RGBA', canvas.size, (*FROST, 0))
            rim.putalpha(outline.point(lambda a: round(a * .16)))
            canvas = Image.alpha_composite(canvas, rim)
        textures[f'palette_{name}.png'] = canvas.resize((128, 128), Image.Resampling.LANCZOS)
    card = gradient((300, 168), [(0, (17, 30, 48, 255)), (1, (4, 7, 13, 255))])
    emblem = busy_frame(0).resize((144 * SCALE, 144 * SCALE), Image.Resampling.LANCZOS)
    card.alpha_composite(emblem, (78 * SCALE, 12 * SCALE))
    card.putalpha(mask((300, 168), CONSTANTS['card_border']))
    textures['card_demo.png'] = card.resize((300, 168), Image.Resampling.LANCZOS)
    for frame in range(24):
        textures[f'busy/frame_{frame:02d}.png'] = busy_frame(frame)
    textures.update(__import__('textures_player').player_textures())
    build_library_textures(textures, mask, surface, glow)
    for name, texture in sorted(textures.items()):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        texture.save(target, format='PNG', optimize=False, compress_level=9)
    __import__('textures_settings').build(output)
    print(f'Rendered {len(textures)} PNGs to {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'media')
    build(parser.parse_args().output)
