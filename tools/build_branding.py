#!/usr/bin/env python3
"""Render approved event-horizon SVG drafts with system librsvg and Cairo.

Pillow supplies the rounded icon mask and the Manrope Light wordmark.
No network access occurs during a build.
"""
import ctypes as C
from ctypes.util import find_library
import io
from pathlib import Path
import random
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]

def stars(n, w, h, seed, maxr=1.6, avoid=None):
    rnd = random.Random(seed); out = []
    for _ in range(n):
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        if avoid and (x - avoid[0]) ** 2 + (y - avoid[1]) ** 2 < avoid[2] ** 2: continue
        r = rnd.choice([.6, .7, .8, 1, 1.2, maxr]); o = rnd.uniform(.25, .9)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#f4f7fb" opacity="{o:.2f}"/>')
    return "".join(out)

DEFS = ('<defs><radialGradient id="glow"><stop offset=".42" stop-color="#f5c27a" stop-opacity="0"/><stop offset=".5" stop-color="#f5c27a" stop-opacity=".55"/>'
        '<stop offset=".62" stop-color="#f5c27a" stop-opacity=".12"/><stop offset="1" stop-color="#f5c27a" stop-opacity="0"/></radialGradient>'
        '<linearGradient id="disk" x1="0" x2="1"><stop offset="0" stop-color="#fff6e4"/><stop offset=".3" stop-color="#f5c27a"/>'
        '<stop offset=".7" stop-color="#b8743a"/><stop offset="1" stop-color="#f5c27a" stop-opacity=".5"/></linearGradient>'
        '<filter id="bl" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="6"/></filter>'
        '<filter id="bl2" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="2"/></filter>'
        '<clipPath id="front"><rect x="-2000" y="0" width="4000" height="2000"/></clipPath>'
        '<clipPath id="back"><rect x="-2000" y="-2000" width="4000" height="2000"/></clipPath>'
        '<linearGradient id="arc" x1="0" x2="1"><stop offset="0" stop-color="#fff6e4"/><stop offset=".45" stop-color="#f5c27a"/><stop offset="1" stop-color="#a8632e"/></linearGradient>'
        '<linearGradient id="fadeg" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".25" stop-color="#fff"/><stop offset=".75" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<mask id="dfade" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="url(#fadeg)"/></mask></defs>')

def eh(cx, cy, r, tilt=-8):
    """Event horizon: lensed glow, the far side of the disk bent over the top and under the bottom of the core, black core, photon ring, near side of the disk in front."""
    disk = (f'<ellipse rx="{r*2.6}" ry="{r*.3}" fill="none" stroke="#f5c27a" stroke-width="{r*.36}" opacity=".25" filter="url(#bl)" mask="url(#dfade)"/>'
            f'<ellipse rx="{r*2.6}" ry="{r*.3}" fill="none" stroke="url(#disk)" stroke-width="{r*.14}" filter="url(#bl2)" mask="url(#dfade)"/>'
            f'<ellipse rx="{r*2.6}" ry="{r*.3}" fill="none" stroke="#fff6e4" stroke-width="{r*.03}" opacity=".8" mask="url(#dfade)"/>')
    top = f'M{-r*1.42} 0 A{r*1.42} {r*1.42} 0 0 1 {r*1.42} 0'
    bot = f'M{-r*1.16} 0 A{r*1.16} {r*1.16} 0 0 0 {r*1.16} 0'
    return (f'<g transform="translate({cx} {cy}) rotate({tilt})">'
            f'<circle r="{r*2.4}" fill="url(#glow)"/>'
            f'<g clip-path="url(#back)">{disk}</g>'
            f'<path d="{top}" fill="none" stroke="#f5c27a" stroke-width="{r*.5}" opacity=".28" filter="url(#bl)"/>'
            f'<path d="{top}" fill="none" stroke="url(#arc)" stroke-width="{r*.2}" opacity=".85" filter="url(#bl2)"/>'
            f'<path d="{top}" fill="none" stroke="#fff6e4" stroke-width="{r*.035}" opacity=".85"/>'
            f'<path d="{bot}" fill="none" stroke="#f5c27a" stroke-width="{r*.09}" opacity=".6" filter="url(#bl2)"/>'
            f'<circle r="{r*1.06}" fill="none" stroke="#fff6e4" stroke-width="{r*.035}" opacity=".95" filter="url(#bl2)"/>'
            f'<circle r="{r}" fill="#010204"/>'
            f'<g clip-path="url(#front)">{disk}</g>'
            f'<circle cx="{-r*2.1}" cy="{r*.06}" r="{r*.1}" fill="#fff6e4" filter="url(#bl2)" opacity=".85"/></g>')

def svg(w, h, body, bg="#03050a"):
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg"><rect width="{w}" height="{h}" fill="{bg}"/>{DEFS}{body}</svg>'


class Rectangle(C.Structure):
    _fields_ = [('x', C.c_double), ('y', C.c_double),
                ('width', C.c_double), ('height', C.c_double)]


def rasterize(source, width, height):
    """Use the installed SVG engine, including Gaussian filters and masks."""
    svg_library = C.CDLL(find_library('rsvg-2'))
    cairo = C.CDLL(find_library('cairo'))
    objects = C.CDLL(find_library('gobject-2.0'))
    svg_library.rsvg_handle_new_from_data.argtypes = [C.c_char_p, C.c_size_t, C.POINTER(C.c_void_p)]
    svg_library.rsvg_handle_new_from_data.restype = C.c_void_p
    svg_library.rsvg_handle_render_document.argtypes = [C.c_void_p, C.c_void_p, C.POINTER(Rectangle), C.POINTER(C.c_void_p)]
    svg_library.rsvg_handle_render_document.restype = C.c_int
    cairo.cairo_image_surface_create.argtypes = [C.c_int, C.c_int, C.c_int]
    cairo.cairo_image_surface_create.restype = C.c_void_p
    cairo.cairo_create.argtypes = [C.c_void_p]
    cairo.cairo_create.restype = C.c_void_p
    cairo.cairo_surface_write_to_png.argtypes = [C.c_void_p, C.c_char_p]
    cairo.cairo_surface_write_to_png.restype = C.c_int
    cairo.cairo_destroy.argtypes = [C.c_void_p]
    cairo.cairo_surface_destroy.argtypes = [C.c_void_p]
    objects.g_object_unref.argtypes = [C.c_void_p]
    data = source.encode('utf-8')
    error = C.c_void_p()
    handle = svg_library.rsvg_handle_new_from_data(data, len(data), C.byref(error))
    if not handle:
        raise RuntimeError('SVG document could not be parsed')
    surface = cairo.cairo_image_surface_create(0, width, height)
    context = cairo.cairo_create(surface)
    try:
        if not svg_library.rsvg_handle_render_document(handle, context,
                C.byref(Rectangle(0, 0, width, height)), C.byref(error)):
            raise RuntimeError('SVG document could not be rendered')
        with tempfile.TemporaryDirectory(prefix='starlight-brand-') as scratch:
            target = Path(scratch) / 'render.png'
            if cairo.cairo_surface_write_to_png(surface, str(target).encode()):
                raise RuntimeError('PNG could not be written')
            return Image.open(io.BytesIO(target.read_bytes())).convert('RGBA')
    finally:
        cairo.cairo_destroy(context)
        cairo.cairo_surface_destroy(surface)
        objects.g_object_unref(handle)


def build():
    icon_source = svg(512, 512, stars(40, 512, 512, 3, 1.2, (256, 256, 170))
                      + eh(256, 256, 78), 'url(#ibg)').replace(
        '<defs>', '<defs><radialGradient id="ibg" cx=".5" cy=".45" r=".7">'
        '<stop offset="0" stop-color="#14203a"/><stop offset="1" stop-color="#03050a"/>'
        '</radialGradient>', 1)
    icon = rasterize(icon_source, 1024, 1024)
    mask = Image.new('L', icon.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 1023, 1023), radius=225, fill=255)
    icon.putalpha(mask)
    icon.resize((512, 512), Image.Resampling.LANCZOS).save(ROOT / 'icon.png')
    fan_source = svg(1920, 1080, stars(260, 1920, 1080, 7, 1.8, (1300, 520, 420))
                     + eh(1300, 520, 190), 'url(#fbg)').replace(
        '<defs>', '<defs><radialGradient id="fbg" cx=".7" cy=".4" r=".8">'
        '<stop offset="0" stop-color="#0b1424"/><stop offset="1" stop-color="#03050a"/>'
        '</radialGradient>', 1)
    fanart = rasterize(fan_source, 1920, 1080)
    draw = ImageDraw.Draw(fanart)
    font = ImageFont.truetype(str(ROOT / 'fonts/manrope-light.ttf'), 76)
    x = 196
    for character in 'STARLIGHT':
        draw.text((x, 470), character, font=font, fill='#f4f7fb', anchor='lt')
        x += draw.textlength(character, font=font) + 76 * .32
    fanart.convert('RGB').save(ROOT / 'fanart.jpg', quality=95, subsampling=0)
    print('Rendered icon.png (512x512) and fanart.jpg (1920x1080)')


if __name__ == '__main__':
    build()
