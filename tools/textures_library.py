"""Create library masks at final card sizes and round person focus surfaces."""
from PIL import Image


def build_library_textures(textures, mask, surface, glow):
    sizes = {'square': (230, 230), 'landscape': (380, 214),
             'poster': (189, 283), 'circle': (210, 210),
             'board': (520, 293), 'expanded': (736, 312),
             'row-landscape': (416, 232), 'row-board': (488, 275),
             'row-poster': (216, 312), 'search': (240, 240),
             'search-poster': (160, 240), 'list-thumb': (96, 54),
             'list-album': (56, 56), 'list-expanded': (284, 160),
             'list-large': (336, 189), 'preview-poster': (430, 645),
             'preview-album': (430, 430)}
    for name, size in sizes.items():
        radius = 105 if name == 'circle' else 8 if name.startswith('list-') else 16
        image = Image.new('RGBA', size, (255, 255, 255, 255))
        image.putalpha(mask(size, radius).resize(size, Image.Resampling.LANCZOS))
        textures[f'library/{name}_mask.png'] = image
    textures['library/key_focus.png'] = surface((42, 64), 21, focus=True)
    textures['library/key_fill.png'] = surface((42, 64), 21, selected=True)
    textures['library/key_glow.png'] = glow((42, 64), 21)
    textures['library/circle_focus.png'] = surface((210, 210), 105, focus=True)
    textures['library/circle_glow.png'] = glow((210, 210), 105)
