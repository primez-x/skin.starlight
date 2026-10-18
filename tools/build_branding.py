#!/usr/bin/env python3
"""Render the approved D1 brand with Pillow and the system SVG engine."""
import ctypes as C
from ctypes.util import find_library
from functools import lru_cache
import io
import math
from pathlib import Path
import random
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]

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


def smoothstep(low, high, value):
    fraction = max(0, min(1, (value-low)/(high-low)))
    return fraction*fraction*(3-2*fraction)


@lru_cache(maxsize=8)
def horizon(size, radius, tilt=-8):
    """D1: an eight-degree near disk, two lens images and a black shadow.

    Sample each radial filament across a narrow Gaussian band. Pillow rotates
    the oversampled field and supplies the same quantized glow as the draft.
    """
    width, height = size
    count = width*height
    near, upper, lower = ([0.0]*count for _ in range(3))
    elevation = math.sin(math.radians(8))
    line_width, lens_width = .018, .030
    step = (3.03-1.24)/127
    for column in range(width):
        x = (column-(width-1)/2)/radius
        for ring in range(128):
            r = 1.24+ring*step
            weight = smoothstep(1.24, 1.38, r)*(1-smoothstep(2.36, 3.03, r))
            weight *= math.exp(-(r-1.24)/.63)*(1+.095*math.sin(45*r)+.035*math.sin(93*r))
            if not weight or abs(x) >= r:
                continue
            upper_r = 1.16+.32*(r-1.24)
            lower_r = 1.075+.29*(r-1.24)
            join_upper = math.sqrt(r*r-upper_r*upper_r)*elevation
            join_lower = math.sqrt(r*r-lower_r*lower_r)*elevation
            curves = [(near, math.sqrt(r*r-x*x)*elevation, line_width,
                       smoothstep(0, .07, r-abs(x)))]
            if abs(x) < upper_r:
                curves.append((upper, join_upper-(1.13+.10*(r-1.24)+join_upper)*math.sqrt(1-(x/upper_r)**2),
                               lens_width, smoothstep(0, .045, upper_r-abs(x))))
            if abs(x) < lower_r:
                curves.append((lower, join_lower+(1.045+.15*(r-1.24)-join_lower)*math.sqrt(1-(x/lower_r)**2),
                               lens_width, smoothstep(0, .045, lower_r-abs(x))))
            for field, centre, sigma, valid in curves:
                centre = centre*radius+(height-1)/2
                spread = sigma*radius
                amplitude = weight*valid*step/.055
                for row in range(max(0, math.floor(centre-6*spread)), min(height, math.ceil(centre+6*spread)+1)):
                    field[row*width+column] += amplitude*math.exp(-.5*((row-centre)/spread)**2)
    back_raw, near_raw = bytearray(count), bytearray(count)
    photons = [0.0]*count
    for row in range(height):
        y = (row-(height-1)/2)/radius
        for column in range(width):
            index = row*width+column
            x = (column-(width-1)/2)/radius
            approach = 1/(1+math.exp(max(-30, min(30, x*2))))
            beaming = .40+1.40*approach
            near[index] *= beaming*.88
            photon = math.exp(-.5*((math.hypot(x, y)-1.015)/.012)**2)*(.75+.35*approach)
            photons[index] = photon
            back = upper[index]*beaming*.55+lower[index]*beaming*.105+photon*1.65
            upper[index] = 1-math.exp(-back)
            lower[index] = 1-math.exp(-near[index])
            back_raw[index] = int(upper[index]*255)
            near_raw[index] = int(lower[index]*255)
    def blur(data, extent):
        return Image.frombytes('L', size, bytes(data)).filter(ImageFilter.GaussianBlur(extent)).tobytes()
    back_soft, back_wide = blur(back_raw, radius*.10), blur(back_raw, radius*.32)
    near_soft, near_wide = blur(near_raw, radius*.055), blur(near_raw, radius*.21)
    pixels = bytearray(count*4)
    gold, frost = (245/255, 194/255, 122/255), (244/255, 247/255, 251/255)
    for row in range(height):
        y = (row-(height-1)/2)/radius
        for column in range(width):
            index = row*width+column
            x = (column-(width-1)/2)/radius
            distance = math.hypot(x, y)
            outside = smoothstep(.995, 1.005, distance)
            back = (upper[index]+back_soft[index]/255*.42+back_wide[index]/255*.26)*outside
            glow = near_soft[index]/255*.26+near_wide[index]/255*.15
            if distance < .995:
                glow *= smoothstep(.002, .035, near[index])
            energy = min(1, back+lower[index]+glow)
            approach = 1/(1+math.exp(max(-30, min(30, x*2))))
            white = min(.95, .10+.55*approach+.19*lower[index]+.15*photons[index])
            rgb = [energy*(a*(1-white)+b*white) for a,b in zip(gold, frost)]
            alpha = max(max(rgb), 1-outside)
            offset = index*4
            for channel, value in enumerate(rgb):
                pixels[offset+channel] = round(max(0, min(1, value/max(alpha, 1e-6)))*255)
            pixels[offset+3] = round(max(0, min(1, alpha))*255)
    # Pillow's positive angle is counter-clockwise; the draft uses screen axes.
    return Image.frombytes('RGBA', size, bytes(pixels)).rotate(-tilt, Image.Resampling.BICUBIC)


def starfield(size, count, seed, avoid=None, icon=False, transparent=False):
    """Use the approved seeded starfield and deep-blue radial backdrop."""
    width, height = size
    cx, cy = (.5, .45) if icon else (.70, .4)
    blue, void = ((20,32,58) if icon else (11,20,36)), (3,5,10)
    image = Image.new('RGBA', size)
    if not transparent:
        pixels = bytearray(width*height*3)
        for y in range(height):
            for x in range(width):
                radial = math.exp(-(((x/width-cx)/.52)**2+((y/height-cy)/.62)**2)*1.5)
                offset = (y*width+x)*3
                pixels[offset:offset+3] = bytes(int(a+(b-a)*radial) for a,b in zip(void, blue))
        image = Image.frombytes('RGB', size, bytes(pixels)).convert('RGBA')
    layer = Image.new('RGBA', size)
    draw = ImageDraw.Draw(layer)
    rng = random.Random(seed)
    for _ in range(count):
        x,y = rng.uniform(0,width),rng.uniform(0,height)
        if avoid and (x-avoid[0])**2+(y-avoid[1])**2 < avoid[2]**2:
            continue
        r = rng.choice((.45,.6,.8,1.0,1.2))
        draw.ellipse((x-r,y-r,x+r,y+r),fill=(244,247,251,round(rng.uniform(.18,.7)*255)))
    image.alpha_composite(layer)
    return image


def splash_stars():
    return starfield((1920,1080),120,11,(960,480,360),transparent=True)


def build():
    icon = starfield((1024,1024),40,3,(512,512,340),icon=True)
    icon.alpha_composite(horizon((1024,1024),156))
    mask = Image.new('L',icon.size)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,1023,1023),radius=225,fill=255)
    icon.putalpha(mask)
    icon.resize((512,512),Image.Resampling.LANCZOS).save(ROOT/'icon.png',compress_level=9)
    fanart = starfield((1920,1080),260,7,(1300,520,420))
    fanart.alpha_composite(horizon((1180,940),190),(710,50))
    draw = ImageDraw.Draw(fanart)
    font = ImageFont.truetype(str(ROOT/'fonts/manrope-light.ttf'),76)
    x = 196
    for character in 'STARLIGHT':
        draw.text((x,470),character,font=font,fill='#f4f7fb',anchor='lt')
        x += draw.textlength(character,font=font)+76*.32
    fanart.convert('RGB').save(ROOT/'fanart.jpg',quality=95,subsampling=0)
    print('Rendered icon.png (512x512) and fanart.jpg (1920x1080)')


if __name__ == '__main__':
    build()
