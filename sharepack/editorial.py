"""Editable editorial composition from an explicit Agent-authored page plan."""
from math import isfinite
from pathlib import Path

from PIL import Image
import json
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.util import Inches, Pt
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.oxml.xmlchemy import OxmlElement

from .logic_ab import PFS_EDGE_STYLE

from .common import ContractError, within
from . import render as R

WIDTH, HEIGHT = 7.5, 10


def box(element):
    values = element.get('box', [])
    if len(values) != 4 or any(type(v) not in (int, float) or not isfinite(v) for v in values):
        raise ContractError('EDITORIAL_INVALID_BOX')
    x, y, w, h = values
    if min(values) < 0 or min(w, h) <= 0 or x + w > WIDTH + 1e-7 or y + h > HEIGHT + 1e-7:
        raise ContractError('EDITORIAL_BOX_OUTSIDE_CANVAS')
    return values


def draw(slide, element, assets, root):
    x, y, w, h = box(element)
    kind = element.get('kind')
    color = element.get('color', 'ink')
    if kind == 'text':
        size = element.get('size', 18)
        if type(size) not in (int, float) or not 10 <= size <= 84:
            raise ContractError('EDITORIAL_INVALID_FONT_SIZE')
        shape = R.text(slide, element['text'], x, y, w, h, size, color, element.get('bold', False))
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.name = 'Arial' if run.text.isascii() else 'Microsoft YaHei'
                for child in run._r.get_or_add_rPr():
                    if child.tag.endswith('}ea'):
                        child.set('typeface', 'Microsoft YaHei')
    elif kind == 'rect':
        R.rect(slide, x, y, w, h, color)
    elif kind == 'ellipse':
        shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, *map(Inches, (x, y, w, h)))
        if element.get('outline'):
            shape.fill.background()
            shape.line.color.rgb = R.rgb(color)
            shape.line.width = Pt(1)
        else:
            shape.fill.solid()
            shape.fill.fore_color.rgb = R.rgb(color)
            shape.line.fill.background()
    elif kind == 'figure':
        aid = element['asset_id']
        asset = assets[aid]
        path = within(root, Path(root) / asset['path'])
        crop = element.get('crop', [0, 0, 1, 1])
        if (len(crop) != 4 or any(type(v) not in (int, float) or not isfinite(v) for v in crop)
                or not (0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1)):
            raise ContractError('EDITORIAL_INVALID_FIGURE_CROP')
        x0, y0, x1, y1 = crop
        with Image.open(path) as im:
            ratio = im.width * (x1 - x0) / (im.height * (y1 - y0))
        dw = min(w, h * ratio)
        dh = dw / ratio
        shape = slide.shapes.add_picture(str(path), Inches(x + (w-dw)/2), Inches(y + (h-dh)/2), Inches(dw), Inches(dh))
        shape.crop_left, shape.crop_top, shape.crop_right, shape.crop_bottom = x0, y0, 1-x1, 1-y1
        shape.name = aid
        return {'asset_id': aid, 'crop_xyxy': crop, 'draw_width_in': round(dw, 3), 'draw_height_in': round(dh, 3),
                'mobile_size_review_required': min(dw, dh) < 1.30}
    else:
        raise ContractError('EDITORIAL_UNKNOWN_ELEMENT')


def slides_editorial(story, assets, root):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(WIDTH), Inches(HEIGHT)
    index = {asset['id']: asset for asset in assets['assets']}
    from .logic_editorial import validate_handoff
    validate_handoff(story, assets)
    geometry = []
    for card in story['cards']:
        plan = card.get('editorial', {})
        elements = plan.get('elements', [])
        declared = card['figure_asset_ids']
        used = [e.get('asset_id') for e in elements if e.get('kind') == 'figure']
        if not elements or len(used) != len(set(used)) or set(used) != set(declared):
            raise ContractError(f"EDITORIAL_FIGURE_BINDING_MISMATCH:{card['order']}")
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        notes = slide.notes_slide.notes_text_frame
        notes.text = '\n'.join([f"DOI {story['paper']['doi']}", *(
            f"{aid}: {index[aid]['figure']}, PDF p.{index[aid]['pdf_page']}" for aid in used)])
        slots = []
        logic_boxes = {e['node_id']:box(e) for e in elements if e['kind']=='logic_node'}
        if logic_boxes and not story.get('research_logic'):
            raise ContractError('EDITORIAL_LOGIC_BINDING_REQUIRED')
        for element in elements:
            if element['kind'] == 'logic_edge':
                j, k = element['source'], element['target']
                if j not in logic_boxes or k not in logic_boxes:
                    raise ContractError('EDITORIAL_LOGIC_DRAW_ENDPOINT_MISSING')
                sx, sy, sw, sh = logic_boxes[j]
                tx, ty, tw, th = logic_boxes[k]
                connector = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                    *map(Inches,(sx+sw/2,sy+sh,tx+tw/2,ty)))
                _,color,dash,arrow = PFS_EDGE_STYLE[element['relation_type']]
                connector.name = element['relation_id']
                connector.line.color.rgb = R.rgb(color)
                connector.line.width = Pt(1.6)
                if dash:
                    connector.line.dash_style = MSO_LINE_DASH_STYLE.DASH
                if arrow:
                    tip=OxmlElement('a:tailEnd')
                    tip.set('type','triangle')
                    connector.get_or_add_ln().append(tip)
                continue
            if element['kind'] == 'logic_node':
                x,y,w,h=box(element)
                R.rect(slide,x,y,w,h,element.get('color','mint'))
                element=dict(element,kind='text',text=element.get('display',element['source_text']),
                             box=[x+.10,y+.10,w-.20,h-.11],color='navy',bold=True)
            result = draw(slide, element, index, root)
            if result:
                slots.append(result)
        if story.get('research_logic'):
            notes.text += '\n' + json.dumps(card['logic_sources'], ensure_ascii=False)
        geometry.append({'card': card['order'], 'layout_type': plan['intent'], 'content_end': HEIGHT,
                         'evidence_figure_slots': slots, 'visible_metric_count': None,
                         'visible_limit_count': None,
                         'mobile_review_required': any(s['mobile_size_review_required'] for s in slots)})
    return prs, geometry
