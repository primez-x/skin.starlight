#!/usr/bin/env python3
"""Render Home XML with local sample art. Approximation only; no Kodi runtime."""
import argparse
from copy import deepcopy
import math
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, quote, unquote, urlsplit
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'resources/lib'))
from home_content import duration_label
from skin_xml import expand


def nine_slice(image, size, border):
    values = [int(value) for value in border.split(',')]
    left, top, right, bottom = values * 4 if len(values) == 1 else values
    sx, sy = (0, left, image.width - right, image.width), (0, top, image.height - bottom, image.height)
    tx, ty = (0, left, size[0] - right, size[0]), (0, top, size[1] - bottom, size[1])
    result = Image.new('RGBA', size)
    for row in range(3):
        for col in range(3):
            box = (tx[col], ty[row], tx[col + 1], ty[row + 1])
            if box[2] > box[0] and box[3] > box[1]:
                tile = image.crop((sx[col], sy[row], sx[col + 1], sy[row + 1])).resize(
                    (box[2] - box[0], box[3] - box[1]), Image.Resampling.BILINEAR)
                result.alpha_composite(tile, box[:2])
    return result


class HomePreview:
    def __init__(self, art, rail=False, settings=None):
        self.focus = 902 if rail else 510
        self.settings = settings or {}
        self.item = {}
        self.includes, self.defaults, self.constants, self.variables = {}, {}, {}, {}
        for path in (ROOT / '1080i').glob('Includes*.xml'):
            tree = ET.parse(path)
            self.includes.update({n.get('name'): n for n in tree.iter('include') if n.get('name')})
            self.defaults.update({n.get('type'): n for n in tree.iter('default')})
            self.constants.update({n.get('name'): n.text for n in tree.iter('constant')})
            self.variables.update({n.get('name'): n for n in tree.iter('variable')})
        self.colors = {n.get('name'): n.text for n in ET.parse(ROOT / 'colors/defaults.xml').iter('color')}
        self.fonts = {n.findtext('name'): n for n in ET.parse(ROOT / '1080i/Font.xml').iter('font')}
        source = (ROOT / 'language/resource.language.en_gb/strings.po').read_text()
        self.strings = dict(re.findall(r'msgctxt "#(\d+)"\s+msgid "([^"\n]*)"', source))
        self.canvas = Image.new('RGBA', (1920, 1080))
        self.groups, self.containers = {}, {}
        self.samples = self.sample_rows(art)
        self.home = self.expand(ET.parse(ROOT / '1080i/Home.xml').getroot())
        for node in self.home.iter('control'):
            if node.get('id'):
                self.groups[int(node.get('id'))] = {int(c.get('id')) for c in node.iter('control') if c.get('id')}
            if node.find('content') is not None:
                args = parse_qs(urlsplit(node.findtext('content')).query)
                if 'source' not in args:
                    self.containers[int(node.get('id'))] = []
                    continue
                rows = self.samples[args['source'][0]]
                part = args.get('part', ['row'])[0]
                self.containers[int(node.get('id'))] = rows[:1] if part == 'feature' else rows[1:5] if part == 'tiles' else rows

    def sample_rows(self, art):
        def row(key, title, progress=0, minutes=117, base='disc'):
            prefix = art / base / key if base else art / key
            arts = {kind: str(prefix) + '-' + kind + ('.png' if kind == 'clearlogo' else '.jpg')
                    for kind in ('fanart', 'landscape', 'poster', 'clearlogo')}
            arts = {k: v for k, v in arts.items() if Path(v).exists()}
            time = duration_label(minutes, self.strings['31039'], self.strings['31019'])
            detail = self.strings['31018'] % time if progress else time
            return {'Label': title, 'Year': '1982' if title == 'Blade Runner' else '2024', 'Mpaa': 'R', 'PercentPlayed': str(progress),
                    'VideoResolution': '2160', 'HdrType': 'dolbyvision',
                    'Duration': '1 h 57 m', 'art': arts,
                    'properties': {'Starlight.Progress': str(progress), 'Starlight.Resume': 'true' if progress else '',
                                   'Starlight.Action': 'Resume' if progress else 'Play',
                                   'Starlight.Duration': duration_label(117, self.strings['31039'], self.strings['31019']),
                                   'Starlight.Time': time, 'Starlight.Detail': 'S4 E4 · ' + detail if title == 'The Expanse' else detail,
                                   'Starlight.Blurred': 'image://' + quote(arts.get('fanart', str(ROOT / 'fanart.jpg')), safe='') + '/?width=16&height=9'}}
        rows = [row('Blade_Runner', 'Blade Runner', 3, 114, ''),
                row('expanse/s4e4', 'The Expanse', 52, 21, ''),
                row('Dune_Part_Two', 'Dune: Part Two', 46, 91),
                row('Interstellar', 'Interstellar', 71, 48),
                row('Ad_Astra', 'Ad Astra', 22, 90)]
        posters = [row(k, title) for k, title in [('Dune','Dune'),('Inception','Inception'),('Avatar','Avatar'),
                   ('Tron_Legacy','Tron: Legacy'),('Edge_of_Tomorrow','Edge of Tomorrow'),
                   ('Interstellar','Interstellar'),('Ad_Astra','Ad Astra'),('Blade_Runner_2049','Blade Runner 2049')]]
        return {'continue': rows, 'movies': posters, 'next': rows[1:2], 'episodes': rows[1:2]}

    def expand(self, raw, parameters=None):
        return expand(raw, self.includes, self.condition, parameters)

    @staticmethod
    def split(value, delimiter):
        depth, start, parts = 0, 0, []
        for index, char in enumerate(value):
            if char in '[(': depth += 1
            elif char in '])': depth -= 1
            elif char == delimiter and depth == 0:
                parts.append(value[start:index]); start = index + 1
        return parts + [value[start:]]

    def info(self, text):
        parts = self.split(text, ',')
        if len(parts) == 3:
            value = self.info(parts[0])
            return parts[1] + value + parts[2] if value else ''
        text = text.strip()
        if text.startswith('$'): return self.resolve(text)
        if text == 'System.Time': return '1:01 PM'
        if text == 'Weather.Temperature': return '64°'
        if text == 'Weather.Conditions': return 'Clear'
        if text == 'Window(home).Property(Starlight.Container)': return '510'
        if text == 'Window(home).Property(Starlight.Hub)': return 'home'
        match = re.fullmatch(r'Skin.String\(([^,)]+)\)', text)
        if match: return self.settings.get(match[1], '')
        match = re.fullmatch(r'Container\((\d+)\)\.(.*)', text)
        item = self.item
        if match:
            rows = self.containers.get(int(match[1]), [])
            if match[2] == 'NumItems': return str(len(rows))
            item = rows[0] if rows else {}; text = match[2]
        if text.startswith('ListItem.'):
            text = text[9:]
            for kind, key in [('Art', 'art'), ('Property', 'properties')]:
                if text.startswith(kind + '('): return item.get(key, {}).get(text[len(kind) + 1:-1], '')
            return item.get(text, '')
        return text

    def resolve(self, text):
        text = re.sub(r'\$VAR\[([^]]+)\]', lambda m: self.variable(m[1]), text)
        text = re.sub(r'\$INFO\[([^]]+)\]', lambda m: self.info(m[1]), text)
        return re.sub(r'\$LOCALIZE\[(\d+)\]', lambda m: self.strings[m[1]], text)

    def variable(self, name):
        for value in self.variables[name]:
            if self.condition(value.get('condition', 'true')): return self.resolve(value.text or '')
        return ''

    def condition(self, expression):
        expression = expression.strip()
        for op in ('|', '+'):
            parts = self.split(expression, op)
            if len(parts) > 1:
                values = [self.condition(p) for p in parts]
                return any(values) if op == '|' else all(values)
        if expression.startswith('!'): return not self.condition(expression[1:])
        if expression.startswith('[') and expression.endswith(']'): return self.condition(expression[1:-1])
        if expression in ('true', 'false'): return expression == 'true'
        match = re.fullmatch(r'Control.HasFocus\((\d+)\)', expression)
        if match: return self.focus == int(match[1])
        match = re.fullmatch(r'ControlGroup\((\d+)\).HasFocus', expression)
        if match: return self.focus in self.groups.get(int(match[1]), set())
        if expression.startswith('System.Time('): return expression == 'System.Time(12:00,18:00)'
        match = re.fullmatch(r'Skin.HasSetting\(([^)]+)\)', expression)
        if match: return self.settings.get(match[1]) == 'true'
        match = re.fullmatch(r'Skin.String\(([^,]+),([^)]+)\)', expression)
        if match: return self.settings.get(match[1], '') == match[2]
        match = re.fullmatch(r'(String.IsEmpty|String.IsEqual|Integer.IsEqual|Integer.IsGreater|Integer.IsGreaterOrEqual)\((.*)\)', expression)
        if match:
            args = [self.info(a) for a in self.split(match[2], ',')]
            if match[1] == 'String.IsEmpty': return not args[0]
            if match[1] == 'String.IsEqual': return args[0] == args[1]
            a, b = [float(v or 0) for v in args]
            if match[1] == 'Integer.IsEqual': return a == b
            return a >= b if match[1] == 'Integer.IsGreaterOrEqual' else a > b
        raise ValueError('Unsupported preview condition: ' + expression)

    def number(self, value): return round(float(self.resolve(self.constants.get(value, value)) or 0))

    def label_style(self, node):
        text = re.sub(r'\[/?(?:COLOR[^\]]*|B|I)\]', '', self.resolve(node.findtext('label', '')))
        spec = self.fonts[node.findtext('font', 'font_body')]
        if 'uppercase' in spec.findtext('style', '').split():
            text = text.upper()
        font = ImageFont.truetype(str(ROOT / 'fonts' / spec.findtext('filename')), int(spec.findtext('size')))
        return text, font, float(spec.findtext('aspect', '1'))

    def extent(self, node, key, fallback):
        value = node.find(key)
        if value is not None and value.text == 'auto':
            text, font, aspect = self.label_style(node)
            return math.ceil(min(float(value.get('max', fallback)),
                                 max(float(value.get('min', '1')), font.getlength(text) * aspect)))
        return self.number(node.findtext(key, str(fallback)))

    def color(self, value):
        value = self.resolve(value)
        value = self.colors.get(value, value)
        a, r, g, b = (int(value[n:n + 2], 16) for n in (0, 2, 4, 6))
        return r, g, b, a

    def texture(self, name):
        lowres = False
        if name.startswith('image://'):
            name = unquote(name[8:].split('/')[0]); lowres = True
        path = ROOT / name[15:] if name.startswith('special://skin/') else Path(name) if Path(name).is_absolute() else ROOT / 'media' / name
        image = Image.open(path).convert('RGBA')
        if lowres: image = image.resize((16, 9), Image.Resampling.LANCZOS)
        return image

    def draw(self, raw, origin=(0, 0), parent=(1920, 1080), opacity=1):
        node = deepcopy(raw); kind = node.get('type')
        for default in self.defaults.get(kind, []):
            if node.find(default.tag) is None: node.append(deepcopy(default))
        if not self.condition(node.findtext('visible', 'true')): return
        x, y = (self.number(node.findtext(key, '0')) for key in ('left', 'top'))
        x += origin[0]; y += origin[1]
        w, h = [self.extent(node, key, parent[i]) for i, key in enumerate(('width', 'height'))]
        if node.find('right') is not None: w = origin[0] + parent[0] - x - self.number(node.findtext('right'))
        zooms = []
        for anim in node.findall('animation'):
            if anim.text != 'Conditional' or not self.condition(anim.get('condition', 'true')): continue
            if anim.get('effect') == 'fade': opacity *= float(anim.get('end')) / 100
            if anim.get('effect') == 'slide':
                dx, dy = map(float, anim.get('end').split(',')); x += round(dx); y += round(dy)
            if anim.get('effect') == 'zoom': zooms.append(anim)
        background = self.canvas
        # Retain edge pixels until the group transform places those pixels onscreen.
        if zooms: self.canvas = Image.new('RGBA', (background.width + 256, background.height + 256))
        if kind in ('group', 'grouplist'):
            offset = 0
            horizontal = node.findtext('orientation') == 'horizontal'
            if kind == 'grouplist' and horizontal and node.findtext('align') == 'center':
                children = [child for child in node.findall('control') if self.condition(child.findtext('visible', 'true'))]
                total = sum(self.extent(child,'width',0) for child in children)
                total += max(0,len(children)-1) * self.number(node.findtext('itemgap','5'))
                offset = max(0, (w-total)//2)
            for child in node.findall('control'):
                self.draw(child, (x + offset if horizontal else x, y if horizontal else y + offset), (w, h), opacity)
                if kind == 'grouplist' and self.condition(child.findtext('visible', 'true')):
                    axis = 'width' if horizontal else 'height'
                    offset += self.extent(child, axis, 0) + self.number(node.findtext('itemgap', '5'))
        elif kind in ('list', 'fixedlist', 'panel'):
            old = self.item; rows = self.containers[int(node.get('id'))]
            for index, item in enumerate(rows):
                self.item = item
                selected = getattr(self, 'selected', {}).get(int(node.get('id')), 0)
                layout = node.find('focusedlayout' if index == selected else 'itemlayout')
                lw, lh = self.number(layout.get('width')), self.number(layout.get('height'))
                columns = max(1, w // lw) if kind == 'panel' else 1 if node.findtext('orientation') == 'vertical' else len(rows)
                xx, yy = x + (index % columns) * lw, y + (index // columns) * lh
                for child in layout.findall('control'): self.draw(child, (xx, yy), (lw, lh), opacity)
            self.item = old
        else:
            tex = node.find('texture')
            if kind in ('button', 'edit'): tex = node.find('texturefocus' if self.focus == int(node.get('id', '0')) else 'texturenofocus')
            if kind == 'progress': tex = node.find('texturebg')
            name = self.resolve(tex.text) if tex is not None and tex.text else ''
            if name:
                image = self.texture(name)
                if tex.get('border'): image = nine_slice(image, (w, h), self.constants[tex.get('border')])
                else: image = ImageOps.fit(image, (w, h), Image.Resampling.BILINEAR) if node.findtext('aspectratio') == 'scale' else ImageOps.contain(image, (w, h), Image.Resampling.LANCZOS) if node.findtext('aspectratio') == 'keep' else image.resize((w, h), Image.Resampling.BILINEAR)
                if tex.get('diffuse'):
                    mask = self.texture(self.resolve(tex.get('diffuse'))).resize(image.size, Image.Resampling.LANCZOS)
                    image.putalpha(ImageChops.multiply(image.getchannel('A'), mask.getchannel('A')))
                tint = self.color(node.findtext('colordiffuse', 'FFFFFFFF'))
                image = ImageChops.multiply(image, Image.new('RGBA', image.size, tint))
                image.putalpha(image.getchannel('A').point(lambda a: round(a * opacity)))
                self.canvas.alpha_composite(image, (x, y))
                if kind == 'progress':
                    value = float(self.info(node.findtext('info')) or 0)
                    if value:
                        fill = self.texture(node.findtext('midtexture')).resize((max(1, round(w*value/100)), h))
                        self.canvas.alpha_composite(fill, (x,y))
            if kind in ('label', 'button', 'edit', 'fadelabel', 'textbox'):
                text, font, aspect = self.label_style(node)
                color = self.color(node.findtext('textcolor', 'frost')); color = (*color[:3], round(color[3]*opacity))
                align = node.findtext('align', 'left'); anchor = {'left':'lm','center':'mm','right':'rm'}[align]
                if kind != 'textbox' and font.getlength(text) * aspect > w:
                    while text and font.getlength(text + '…') * aspect > w:
                        text = text[:-1]
                    text += '…'
                layer = Image.new('RGBA', (max(1, round(w / aspect)), h))
                tx = {'left':0,'center':layer.width/2,'right':layer.width}[align]
                if kind == 'textbox':
                    words = text.split(); lines = []; line = ''
                    for word in words:
                        candidate = (line + ' ' + word).strip()
                        if line and font.getlength(candidate) * aspect > w:
                            lines.append(line); line = word
                        else: line = candidate
                    if line: lines.append(line)
                    spacing = round(font.size * 1.5)
                    for index, line in enumerate(lines[:max(1, h // spacing)]):
                        ImageDraw.Draw(layer).text((0,index*spacing),line,font=font,fill=color,anchor='lt')
                else:
                    ImageDraw.Draw(layer).text((tx,h/2),text,font=font,fill=color,anchor=anchor)
                self.canvas.alpha_composite(layer.resize((w,h), Image.Resampling.BICUBIC), (x,y))
        for anim in zooms:
            end = [float(a)/100 for a in anim.get('end').split(',')]; zx,zy = end if len(end)==2 else end*2
            cx,cy = map(float,anim.get('center','0,0').split(',')); cx+=x;cy+=y
            self.canvas=self.canvas.transform(self.canvas.size,Image.Transform.AFFINE,
                (1/zx,0,cx*(1-1/zx),0,1/zy,cy*(1-1/zy)),Image.Resampling.BICUBIC)
        if zooms:self.canvas=Image.alpha_composite(background,self.canvas.crop((0,0,*background.size)))

    def save(self, output):
        for node in self.home.findall('controls/control'): self.draw(node)
        output.parent.mkdir(parents=True,exist_ok=True)
        self.canvas.convert('RGB').save(output)
        print(f'Rendered Home XML to {output} (1920x1080, focus {self.focus}; sample data, static animation endpoints)')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('/tmp/starlight-step2/home.png'))
    parser.add_argument('--art',type=Path,required=True)
    parser.add_argument('--rail-open',action='store_true')
    parser.add_argument('--setting',action='append',default=[],metavar='KEY=VALUE')
    args=parser.parse_args()
    HomePreview(args.art,args.rail_open,dict(s.split('=',1) for s in args.setting)).save(args.output)
