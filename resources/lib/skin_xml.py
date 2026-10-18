"""Shared include expansion and card geometry. No graphics dependency."""
from copy import deepcopy
import math
import re


def expand(raw, includes, condition, parameters=None):
    node = deepcopy(raw)
    params = parameters or {}
    for element in node.iter():
        for key, value in element.attrib.items():
            element.set(key, re.sub(r'\$PARAM\[([^]]+)\]', lambda match: params.get(match[1], match[0]), value))
        if element.text:
            element.text = re.sub(r'\$PARAM\[([^]]+)\]', lambda match: params.get(match[1], match[0]), element.text)
    children = []
    for child in node:
        if child.tag != 'include':
            children.append(expand(child, includes, condition))
            continue
        if not condition(child.get('condition', 'true')):
            continue
        definition = includes[child.get('content') or child.text]
        local = {param.get('name'): param.get('default') for param in definition.findall('param')}
        local.update({param.get('name'): param.get('value') for param in child.findall('param')})
        body = definition.find('definition')
        children.extend(expand(body if body is not None else definition, includes, condition, local))
    node[:] = children
    return node


def card_rect(tree, control_id, position, scroll, constants, condition):
    """Find the focused card through the actual window groups and layouts."""
    def number(value):
        return float(constants.get(value, value))

    def walk(node, origin=(0, 0)):
        x = origin[0] + number(node.findtext('left', '0'))
        y = origin[1] + number(node.findtext('top', '0'))
        for animation in node.findall('animation'):
            if animation.text == 'Conditional' and animation.get('effect') == 'slide' and condition(animation.get('condition', 'true')):
                dx, dy = map(float, animation.get('end').split(','))
                x += dx
                y += dy
        if node.get('id') == str(control_id):
            layout = node.find('focusedlayout')
            if layout is None:
                return None
            width, height = number(layout.get('width')), number(layout.get('height'))
            if node.get('type') == 'panel':
                columns = max(1, int(number(node.findtext('width')) // width))
                x += position % columns * width
                y += position // columns * height
            elif node.get('type') != 'fixedlist':
                if node.findtext('orientation') == 'vertical':
                    y += position * height
                else:
                    x += position * width
            card = layout.find("control[@type='group']")
            if card is None:
                return None
            x += number(card.findtext('left', '0'))
            y += number(card.findtext('top', '0'))
            width, height = number(card.findtext('width')), number(card.findtext('height'))
            for animation in card.findall('animation'):
                if animation.get('effect') == 'zoom' and condition(animation.get('condition', 'true')):
                    scale = float(animation.get('end')) / 100
                    cx, cy = map(float, animation.get('center').split(','))
                    x -= cx * (scale - 1)
                    y -= cy * (scale - 1)
                    width *= scale
                    height *= scale
            return x, y, width, height
        if node.get('id') == '5000':
            y -= scroll
        offset = 0
        horizontal = node.findtext('orientation') == 'horizontal'
        for child in node.findall('control'):
            if not condition(child.findtext('visible', 'true')):
                continue
            found = walk(child, (x + offset if horizontal else x, y if horizontal else y + offset))
            if found:
                for animation in node.findall('animation'):
                    if animation.get('effect') == 'zoom' and condition(animation.get('condition', 'true')):
                        scale = float(animation.get('end')) / 100
                        cx, cy = map(float, animation.get('center', '0,0').split(','))
                        fx, fy, fw, fh = found
                        found = (x + cx + (fx - x - cx) * scale,
                                 y + cy + (fy - y - cy) * scale, fw * scale, fh * scale)
                return found
            if node.get('type') == 'grouplist':
                offset += number(child.findtext('width' if horizontal else 'height', '0'))
                offset += number(node.findtext('itemgap', '5'))
        return None

    found = next((rect for node in tree.findall('controls/control')
                  if (rect := walk(node)) is not None), None)
    if found is None:
        return None
    return (math.floor(round(found[0], 4)), math.floor(round(found[1], 4)),
            math.ceil(round(found[2], 4)), math.ceil(round(found[3], 4)))
