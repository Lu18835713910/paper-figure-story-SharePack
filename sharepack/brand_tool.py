#!/usr/bin/env python3
"""SharePack private-brand placement / read-only audit helper (not part of released Skill).

Hard boundaries:
- Only reviewed layout maps can be applied; input deck and logo SHA-256 must match.
- Original scientific shapes and Figure bytes must be preserved.
- PRIVATE editorial review only; publication/trademark clearance is not provided.
- For new deck layouts use 'draft' and manually inspect/approve each placement.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

EMU_PER_IN=914400
CONTRACT='sharepack-private-brand-placement-v1'
PREFIX='SP_PRIV_BRAND_'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for blk in iter(lambda: f.read(1024*1024),b''):h.update(blk)
    return h.hexdigest()

def dump(obj, path):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def box(s):
    return {'x':round(s.left/EMU_PER_IN,3),'y':round(s.top/EMU_PER_IN,3),'w':round(s.width/EMU_PER_IN,3),'h':round(s.height/EMU_PER_IN,3)}

def read_deck(path):
    p=Path(path)
    if not p.is_file():raise ValueError('DECK_UNAVAILABLE')
    deck=Presentation(p)
    return deck

def find_named(slide, name):
    found=[s for s in slide.shapes if s.name==name]
    if len(found)!=1:raise ValueError(f'SHAPE_NAME_AMBIGUOUS:{name}:{len(found)}')
    return found[0]

def inspect(path):
    prs=read_deck(path)
    records=[]
    for i,s in enumerate(prs.slides,1):
        header=[]
        for sh in s.shapes:
            if sh.top/EMU_PER_IN<1.35:
                text=sh.text[:120].replace('\n',' / ') if sh.has_text_frame else ''
                header.append({'name':sh.name,'type':str(sh.shape_type),'box':box(sh),'text':text})
        records.append({'slide':i,'count':len(s.shapes),'header':header})
    return {'file':str(path),'sha256':sha(path),'pages':len(prs.slides),
        'size_in':[round(prs.slide_width/EMU_PER_IN,3),round(prs.slide_height/EMU_PER_IN,3)],'slides':records}

def draft(path,logo_path):
    meta=inspect(path); w,h=meta['size_in']
    if abs(w-7.5)>0.03 or abs(h-10.0)>0.03:raise ValueError('DRAFT_ONLY_7p5x10_SUPPORTED')
    layouts=[]
    for page in meta['slides']:
        is_cover=page['slide']==1
        # Proposal only. The reviewer MUST check every header for collisions before approval.
        layouts.append({'slide':page['slide'],
            'image':{'x':.65 if is_cover else 5.07, 'y':.29 if is_cover else .34,
                     'w':3.40 if is_cover else 1.81},
            'plate':{'x':.50,'y':.18,'w':3.72,'h':.79} if is_cover else None,
            'adjust':[],
            'review_notes':'NOT_APPROVED: inspect every existing header element, figure/section and text. Configure adjustments/plate for this specific deck.'})
    return {'contract':CONTRACT,'layout_approved':False,'distribution_scope':'private_review_only',
        'rights_clearance':'PENDING','deck_sha256':meta['sha256'],
        'logo_sha256':sha(logo_path),'slides':layouts}

def assert_cfg(cfg,src,logo,prs):
    if cfg.get('contract')!=CONTRACT:raise ValueError('CONTRACT_INVALID')
    if cfg.get('layout_approved') is not True:raise ValueError('LAYOUT_NOT_APPROVED')
    if cfg.get('distribution_scope')!='private_review_only':raise ValueError('PUBLIC_OR_UNKNOWN_DISTRIBUTION_BLOCKED')
    if cfg.get('rights_clearance') not in ('PENDING','PRIVATE_ONLY'):
        raise ValueError('INVALID_RIGHTS_SCOPE')
    if cfg.get('deck_sha256')!=sha(src):raise ValueError('SOURCE_DECK_SHA_MISMATCH')
    if cfg.get('logo_sha256')!=sha(logo):raise ValueError('LOGO_SHA_MISMATCH')
    if not isinstance(cfg.get('slides'),list) or len(cfg['slides'])!=len(prs.slides):raise ValueError('SLIDE_COUNT_MISMATCH')
    if set(x.get('slide') for x in cfg['slides'])!=set(range(1,len(prs.slides)+1)):
        raise ValueError('SLIDE_NUMBERS_INVALID')
    for slide in prs.slides:
        if any(s.name.startswith(PREFIX) for s in slide.shapes):raise ValueError('BRAND_ALREADY_PRESENT')

def place_shape(sh,changes):
    for attr,key in [('left','x'),('top','y'),('width','w'),('height','h')]:
        if key in changes:setattr(sh,attr,Inches(float(changes[key])))
    if 'font_pt' in changes:
        if not sh.has_text_frame:raise ValueError('FONT_ADJUST_NON_TEXT')
        for paragraph in sh.text_frame.paragraphs:
            for run in paragraph.runs:run.font.size=Pt(float(changes['font_pt']))

def safe_bounds(prs, slide, element):
    x=float(element['x']);y=float(element['y']);w=float(element['w']);h=float(element['h'])
    if not(0<=x and 0<=y and 0<w and 0<h and x+w <= prs.slide_width/EMU_PER_IN+.0001 and y+h <= prs.slide_height/EMU_PER_IN+.0001):
        raise ValueError(f'PLACEMENT_OUT_OF_BOUNDS:{slide}:{element}')

def overlap(a,b):
    return min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+.01 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+.01

def apply(src,logo,cfg_path,out,audit_path):
    src=Path(src).resolve();logo=Path(logo).resolve();out=Path(out).resolve()
    if src==out:raise ValueError('OVERWRITE_SOURCE_FORBIDDEN')
    if out.exists():raise ValueError('OUTPUT_EXISTS_FORBIDDEN')
    cfg=json.loads(Path(cfg_path).read_text(encoding='utf-8'))
    prs=read_deck(src);assert_cfg(cfg,src,logo,prs)
    order={item['slide']:item for item in cfg['slides']}
    touched={}
    for index,slide in enumerate(prs.slides,1):
        cfgslide=order[index];before=list(slide.shapes);changed=set()
        for req in cfgslide.get('adjust',[]):
            name=req.get('name');old=find_named(slide,name)
            if name in changed:raise ValueError('ADJUST_DUPLICATE:'+name)
            changed.add(name);place_shape(old,req)
        im=cfgslide['image']
        if not all(k in im for k in ('x','y','w')):raise ValueError('IMAGE_COORDS_MISSING')
        # Non-square actual image sizing: independently measured from original source.
        from PIL import Image
        with Image.open(logo) as I:ratio=I.height/I.width
        imagebox={**im,'h':float(im['w'])*ratio}
        safe_bounds(prs,index,imagebox)
        plate=cfgslide.get('plate')
        if plate:safe_bounds(prs,index,plate)
        # Reject new logo collision with any unrelated preexisting foreground object.
        # Background (full-slide shapes) are exempt; science objects are not.
        for s in before:
            b=box(s)
            if s.name in changed:continue
            if b['w']>prs.slide_width/EMU_PER_IN*.90 and b['h']>prs.slide_height/EMU_PER_IN*.90:continue
            if overlap(b,imagebox):
                raise ValueError(f'LOGO_COLLIDES_WITH_ORIGINAL:{index}:{s.name}:{b}')
            if plate and overlap(b,plate):
                raise ValueError(f'PLATE_COLLIDES_WITH_ORIGINAL:{index}:{s.name}:{b}')
        if plate:
            p=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(plate['x']),Inches(plate['y']),Inches(plate['w']),Inches(plate['h']))
            p.name=f'{PREFIX}PLATE_{index:02}'
            p.fill.solid();p.fill.fore_color.rgb=RGBColor(255,255,255);p.line.fill.background()
        pic=slide.shapes.add_picture(str(logo),Inches(imagebox['x']),Inches(imagebox['y']),width=Inches(imagebox['w']))
        pic.name=f'{PREFIX}IMAGE_{index:02}'
        touched[index]={'adjusted_names':sorted(changed),'logo_placement':imagebox,'plate':plate}
    prs.core_properties.subject='PRIVATE REVIEW ONLY: historical journal brand specimen; public logo/figure rights NOT cleared.'
    out.parent.mkdir(parents=True,exist_ok=True);prs.save(out)
    result=verify(src,out,logo,cfg_path)
    if audit_path:dump(result,audit_path)
    return result

def verify(src,out,logo,cfg_path):
    src=Path(src);out=Path(out);logo=Path(logo)
    cfg=json.loads(Path(cfg_path).read_text(encoding='utf-8'))
    before=read_deck(src);after=read_deck(out)
    assert_cfg(cfg,src,logo,before)
    if len(before.slides)!=len(after.slides):raise ValueError('SAVED_SLIDE_COUNT_DRIFT')
    c={x['slide']:x for x in cfg['slides']}
    picture_count=0
    for ix,(old,new) in enumerate(zip(before.slides,after.slides),1):
        oldsh=list(old.shapes);newsh=list(new.shapes)
        expected=1+int(bool(c[ix].get('plate')))
        if len(newsh)!=len(oldsh)+expected:raise ValueError(f'SHAPE_COUNT_DRIFT:{ix}')
        adjusted={x['name'] for x in c[ix].get('adjust',[])}
        for i,sh in enumerate(oldsh):
            oth=newsh[i]
            if sh.name!=oth.name or sh.shape_type!=oth.shape_type:raise ValueError(f'ORIGINAL_SHAPE_IDENTITY_DRIFT:{ix}:{i}')
            t0=(sh.text if sh.has_text_frame else None);t1=(oth.text if oth.has_text_frame else None)
            if t0!=t1:raise ValueError(f'SCIENTIFIC_TEXT_CHANGED:{ix}:{i}')
            if sh.shape_type==13:
                picture_count+=1
                if sh.image.blob!=oth.image.blob:raise ValueError(f'ORIGINAL_FIGURE_IMAGE_DRIFT:{ix}:{i}')
            if sh.name not in adjusted and sh._element.xml!=oth._element.xml:
                raise ValueError(f'UNAPPROVED_OOXML_SHAPE_CHANGE:{ix}:{i}:{sh.name}')
        for brand in newsh[len(oldsh):]:
            if not brand.name.startswith(PREFIX):raise ValueError('UNEXPECTED_NEW_SHAPE')
    return {'status':'PASS_PRIVATE_BRANDING_ONLY','slides':len(before.slides),
        'original_figure_objects_preserved':picture_count,'all_original_text_preserved':True,
        'all_unapproved_existing_shapes_byte_stable_xml':True,
        'source_deck_sha256':sha(src),'output_deck_sha256':sha(out),
        'logo_file_sha256':sha(logo),'layout_sha256':sha(cfg_path),
        'publication_ready':False,'logo_rights_clearance':'NOT_GRANTED_BY_THIS_TOOL'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sp=parser.add_subparsers(dest='command',required=True)
    i=sp.add_parser('inspect');i.add_argument('--deck',required=True);i.add_argument('--out',required=True)
    d=sp.add_parser('draft');d.add_argument('--deck',required=True);d.add_argument('--logo',required=True);d.add_argument('--out',required=True)
    a=sp.add_parser('apply');a.add_argument('--deck',required=True);a.add_argument('--logo',required=True);a.add_argument('--layout',required=True);a.add_argument('--out',required=True);a.add_argument('--audit',required=True);a.add_argument('--private-only',action='store_true')
    v=sp.add_parser('verify');v.add_argument('--deck',required=True);v.add_argument('--logo',required=True);v.add_argument('--layout',required=True);v.add_argument('--out',required=True);v.add_argument('--audit',required=True)
    args=parser.parse_args()
    try:
        if args.command=='inspect':result=inspect(args.deck);dump(result,args.out)
        elif args.command=='draft':result=draft(args.deck,args.logo);dump(result,args.out)
        elif args.command=='apply':
            if not args.private_only:raise ValueError('MUST_EXPLICITLY_OPT_IN_PRIVATE_ONLY')
            result=apply(args.deck,args.logo,args.layout,args.out,args.audit)
        else:
            result=verify(args.deck,args.out,args.logo,args.layout);dump(result,args.audit)
        print(json.dumps(result if args.command in ('apply','verify') else {'status':'OK','output':args.out},ensure_ascii=False,indent=2))
        return 0
    except Exception as e:
        print(json.dumps({'status':'STOP','error':type(e).__name__,'message':str(e)},ensure_ascii=False),file=sys.stderr)
        return 2
if __name__=='__main__':raise SystemExit(main())
