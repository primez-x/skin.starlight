#!/usr/bin/env python3
"""Compose the actual Home XML as a static PNG. This tool does not execute Kodi."""
import argparse
from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def nine_slice(image, size, border):
    values = [int(value) for value in border.split(',')]
    left, top, right, bottom = values * 4 if len(values) == 1 else values
    source_x = (0, left, image.width - right, image.width)
    source_y = (0, top, image.height - bottom, image.height)
    target_x = (0, left, size[0] - right, size[0])
    target_y = (0, top, size[1] - bottom, size[1])
    result = Image.new('RGBA', size)
    for row in range(3):
        for column in range(3):
            source = (source_x[column], source_y[row], source_x[column + 1], source_y[row + 1])
            target = (target_x[column], target_y[row], target_x[column + 1], target_y[row + 1])
            width, height = target[2] - target[0], target[3] - target[1]
            if width > 0 and height > 0:
                tile = image.crop(source).resize((width, height), Image.Resampling.BILINEAR)
                result.alpha_composite(tile, target[:2])
    return result


class HomePreview:
    def __init__(self, focus):
        self.focus = focus
        self.includes = {}
        self.defaults = {}
        self.constants = {}
        for path in (ROOT / '1080i').glob('Includes*.xml'):
            tree = ET.parse(path)
            self.includes.update({n.get('name'): n for n in tree.iter('include') if n.get('name')})
            self.defaults.update({n.get('type'): n for n in tree.iter('default')})
            self.constants.update({n.get('name'): n.text for n in tree.iter('constant')})
        self.colors = {n.get('name'): n.text for n in ET.parse(ROOT / 'colors/defaults.xml').iter('color')}
        self.fonts = {n.findtext('name'): n for n in ET.parse(ROOT / '1080i/Font.xml').iter('font')}
        source = (ROOT / 'language/resource.language.en_gb/strings.po').read_text()
        self.strings = dict(re.findall(r'msgctxt "#(\d+)"\s+msgid "([^"\n]*)"', source))
        self.canvas = Image.new('RGBA', (1920, 1080))

    def expand(self, node, parameters=None):
        node = deepcopy(node)
        for element in node.iter():
            for key, value in element.attrib.items():
                element.set(key, self.substitute(value, parameters or {}))
            if element.text:
                element.text = self.substitute(element.text, parameters or {})
        children = []
        for child in node:
            if child.tag == 'include':
                definition = self.includes[child.get('content') or child.text]
                params = {p.get('name'): p.get('default') for p in definition.findall('param')}
                params.update({p.get('name'): p.get('value') for p in child.findall('param')})
                body = definition.find('definition')
                children.extend(self.expand(body if body is not None else definition, params))
            else:
                children.append(self.expand(child))
        node[:] = children
        return node

    @staticmethod
    def substitute(value, parameters):
        return re.sub(r'\$PARAM\[([^]]+)\]', lambda m: parameters.get(m[1], m[0]), value)

    def condition(self, expression):
        expression = expression.strip()
        depth = 0
        for operator in ('|', '+'):
            parts, start = [], 0
            for index, char in enumerate(expression):
                if char in '[(': depth += 1
                elif char in '])': depth -= 1
                elif char == operator and depth == 0:
                    parts.append(expression[start:index])
                    start = index + 1
            if parts:
                parts.append(expression[start:])
                values = [self.condition(part) for part in parts]
                return any(values) if operator == '|' else all(values)
        if expression.startswith('!'):
            return not self.condition(expression[1:])
        if expression.startswith('[') and expression.endswith(']'):
            return self.condition(expression[1:-1])
        if expression in ('true', 'false'):
            return expression == 'true'
        match = re.fullmatch(r'Control.HasFocus\((\d+)\)', expression)
        if match:
            return self.focus == int(match[1])
        match = re.fullmatch(r'ControlGroup\((\d+)\).HasFocus', expression)
        if match:
            return match[1] == '9000' and self.focus in (201, 202, 203)
        match = re.fullmatch(r'String.IsEqual\(Window\(home\).Property\(Foundation.Selected\),(\d+)\)', expression)
        if match:
            return int(match[1]) == (201 if self.focus == 204 else self.focus)
        raise ValueError(f'Unsupported preview condition: {expression}')

    def number(self, value):
        return int(self.constants.get(value, value))

    def color(self, name):
        value = self.colors.get(name, name)
        alpha, red, green, blue = (int(value[n:n + 2], 16) for n in (0, 2, 4, 6))
        return red, green, blue, alpha

    def draw(self, raw, origin=(0, 0), parent_size=(1920, 1080), opacity=1):
        kind = raw.get('type')
        node = deepcopy(raw)
        if kind in self.defaults:
            for item in self.defaults[kind]:
                if node.find(item.tag) is None:
                    node.append(deepcopy(item))
        visible = node.findtext('visible', 'true')
        if not self.condition(visible):
            return
        x, y = (self.number(node.findtext(key, '0')) for key in ('left', 'top'))
        width = self.number(node.findtext('width', str(parent_size[0])))
        height = self.number(node.findtext('height', str(parent_size[1])))
        if node.find('right') is not None:
            width = parent_size[0] - x - self.number(node.findtext('right'))
        x += origin[0]
        y += origin[1]
        for animation in node.findall('animation'):
            if animation.get('effect') == 'fade' and self.condition(animation.get('condition', 'true')):
                opacity *= float(animation.get('end')) / 100
        if kind == 'group':
            zooms = [a for a in node.findall('animation') if a.get('effect') == 'zoom'
                     and self.condition(a.get('condition', 'true'))]
            background = self.canvas
            if zooms:
                self.canvas = Image.new('RGBA', background.size)
            for child in node.findall('control'):
                self.draw(child, (x, y), (width, height), opacity)
            for animation in zooms:
                factor = float(animation.get('end')) / 100
                center_x, center_y = map(float, animation.get('center').split(','))
                center_x += x
                center_y += y
                self.canvas = self.canvas.transform(self.canvas.size, Image.Transform.AFFINE,
                    (1 / factor, 0, center_x * (1 - 1 / factor),
                     0, 1 / factor, center_y * (1 - 1 / factor)), Image.Resampling.BICUBIC)
            if zooms:
                self.canvas = Image.alpha_composite(background, self.canvas)
            return
        texture = node.find('texture')
        if kind == 'button':
            texture = node.find('texturefocus' if self.focus == int(node.get('id', '0')) else 'texturenofocus')
        elif kind == 'multiimage':
            texture = ET.Element('texture')
            texture.text = node.findtext('imagepath') + '/frame_00.png'
        if texture is not None and texture.text:
            image = Image.open(ROOT / 'media' / texture.text).convert('RGBA')
            if texture.get('border'):
                image = nine_slice(image, (width, height), self.constants[texture.get('border')])
            elif node.findtext('aspectratio') == 'scale':
                image = ImageOps.fit(image, (width, height), Image.Resampling.BILINEAR)
            else:
                image = image.resize((width, height), Image.Resampling.BILINEAR)
            image.putalpha(image.getchannel('A').point(lambda a: round(a * opacity)))
            self.canvas.alpha_composite(image, (x, y))
        if kind in ('label', 'button'):
            text = node.findtext('label', '')
            text = re.sub(r'\$LOCALIZE\[(\d+)\]', lambda m: self.strings[m[1]], text)
            text = text.replace('$INFO[System.Time]', '13:01')
            if not text:
                return
            spec = self.fonts[node.findtext('font', 'font_body')]
            font = ImageFont.truetype(str(ROOT / 'fonts' / spec.findtext('filename')), int(spec.findtext('size')))
            color = self.color(node.findtext('textcolor', 'frost'))
            color = (*color[:3], round(color[3] * opacity))
            align = node.findtext('align', 'left')
            anchor = {'left': 'lm', 'center': 'mm', 'right': 'rm'}[align]
            text_x = x + {'left': 0, 'center': width / 2, 'right': width}[align]
            layer = Image.new('RGBA', self.canvas.size)
            ImageDraw.Draw(layer).text((text_x, y + height / 2), text, font=font, fill=color, anchor=anchor)
            self.canvas = Image.alpha_composite(self.canvas, layer)

    def save(self, output):
        home = self.expand(ET.parse(ROOT / '1080i/Home.xml').getroot())
        for node in home.findall('controls/control'):
            self.draw(node)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.canvas.convert('RGB').save(output)
        print(f'Rendered Home XML to {output} (1920x1080, focus {self.focus})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/starlight-step1/preview.png'))
    parser.add_argument('--focus', type=int, choices=(201, 202, 203, 204), default=201)
    args = parser.parse_args()
    HomePreview(args.focus).save(args.output)
