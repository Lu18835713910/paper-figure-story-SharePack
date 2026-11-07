"""Evidence-first, variable-composition vertical slides.

No scientific content is inferred here. The planner accepts reviewed story/asset IDs,
calculates geometry and chooses a composition from available content. It never
crops image bytes or silently suppresses metrics, claims, or evidence limits.
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from .common import ContractError, within
from . import render as R

W,H=7.5,10.0
L,RIGHT=.48,7.02
CONTENT_W=RIGHT-L
FOOT_Y=9.30

# Shared typography / color, deliberately NOT a set of fixed card boxes.
def length(s): return R._cell_len(str(s))

def lines(s,w,sz):
    cap=max(1, w*72/(sz*1.1))
    return sum(max(1,math.ceil(length(p)/cap)) for p in str(s).split('\n'))

def text_h(s,w,sz, min_h=.22):
    return max(min_h,lines(s,w,sz)*sz*1.23/72+.055)

def put(sl,s,x,y,w,sz=11,color='navy',bold=False, *,max_h=None,part='text',align=PP_ALIGN.LEFT):
    if not str(s).strip():return y
    h=text_h(s,w,sz)
    if max_h is not None and h>max_h+.01:
        raise ContractError(f'FREEFORM_TEXT_OVERFLOW:{part}:needed_{h:.2f}:available_{max_h:.2f}')
    R._checked_text(sl,s,x,y,w,h,sz,color,bold,align,label=part)
    return y+h

def line(sl,x,y,w,color='border',height=.012): R.rect(sl,x,y,w,height,color)

def stripe(sl,y,color='royal'): R.rect(sl,L,y,.055,.35,color)

def intro(sl,card,idx,total):
    R.rect(sl,0,0,W,H,'bg')
    R.rect(sl,0,0,W,.055,'navy')
    put(sl,'PFS / RESEARCH NOTES',L,.21,4.8,12.3,'royal',True,part='masthead')
    put(sl,f'{idx:02d} / {total:02d}',6.10,.21,.9,10.4,'muted',part='counter',align=PP_ALIGN.RIGHT)
    line(sl,L,.62,CONTENT_W)
    stage=str(card['stage'])
    R.rect(sl,L,.79,.06,.26,'royal')
    put(sl,stage,.65,.79,5.45,9.6,'royal',True,part='stage')
    title=str(card['title']);sz=19.6 if length(title)>30 else 22
    y=put(sl,title,L,1.21,CONTENT_W,sz,'navy',True,part='title')
    y=put(sl,card['intro'],L,y+.15,CONTENT_W,10.5,'muted',part='intro')
    if y>2.42:raise ContractError(f'FREEFORM_HEADER_TOO_TALL:{idx}:{y:.2f}')
    return max(2.30,y+.16)

def footer(sl,story,i,n):
    line(sl,L,FOOT_Y,CONTENT_W)
    p=story['paper']
    cite=f"{p['authors_short']} | {p.get('journal','')} | DOI: {p['doi']}"
    put(sl,cite,L,9.39,CONTENT_W,8.0,'muted',part='citation')
    put(sl,'科研内容整理：PFS SharePack  |  github.com/Lu18835713910/paper-figure-story',L,9.64,CONTENT_W,7.9,'royal',part='github')

def heading(sl,label,y, *,rule=True):
    put(sl,label,L,y,CONTENT_W,11.0,'royal',True,part='heading')
    if rule: line(sl,L,y+.33,CONTENT_W)
    return y+.45

def statement(sl,label,body,y,width=CONTENT_W):
    put(sl,label,L,y,1.03,10.0,'royal',True,part=label+'_label')
    h=text_h(body,width-1.14,10.4)
    put(sl,body,L+1.16,y,width-1.16,10.4,'navy',part=label+'_body')
    return y+max(.35,h)+.10

def figure_meta(sl,a,x,y,w):
    # Page/specific Figure ID remain visible; full provenance is sidecar.
    caption=f"论文原图 {a['figure']} · PDF p.{a.get('pdf_page','?')}"
    if a.get('panel_labels'):caption+=' · '+','.join(a['panel_labels'])
    put(sl,caption,x,y,w,8.1,'muted',part='figure_caption')

def draw_image(sl,a,root,x,y,w,h,*,min_pixel_h=1.18):
    p=within(root,Path(root)/a['path'])
    with Image.open(p) as im:ratio=im.width/im.height
    maxh=max(.25,h-.31)
    wi=min(w,maxh*ratio);hi=wi/ratio
    xx=x+(w-wi)/2; yy=y+(maxh-hi)/2
    sl.shapes.add_picture(str(p),Inches(xx),Inches(yy),width=Inches(wi),height=Inches(hi))
    figure_meta(sl,a,x,y+h-.24,w)
    return {'asset_id':a['id'],'draw_width_in':round(wi,3),'draw_height_in':round(hi,3),
            'slot':[round(x,3),round(y,3),round(w,3),round(h,3)],
            'mobile_size_review_required':hi<min_pixel_h,
            'review_status':a.get('review_status','PENDING')}

def narrative_sizes(c,metrics,limits):
    obs=text_h(c['observation'],CONTENT_W-1.15,10.4)
    take=text_h(c['takeaway'],CONTENT_W-1.15,10.4)
    lim=text_h('；'.join(limits),CONTENT_W-1.15,9.2)
    metric_heights=[text_h(f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}",CONTENT_W-.20,9.5) for m in metrics]
    if any(h>.90 for h in metric_heights):
        raise ContractError('LAYOUT_TEXT_CAPACITY_EXCEEDED:METRIC_LONG_FORM_NEEDS_REPLAN')
    mets=sum(h+.12 for h in metric_heights)
    return obs,take,lim,mets

def summary(sl,c,metrics,limits,y, *,include_observation=True):
    if include_observation:
        y=statement(sl,'观察与发现',c['observation'],y)
    for i,m in enumerate(metrics):
        val=f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}"
        hh=text_h(val,CONTENT_W-.22,9.5)
        # Underline implies a reported numeric reading, not a decorative container.
        R.rect(sl,L,y+.05,.055,hh,'green')
        put(sl,val,L+.14,y,CONTENT_W-.18,9.5,'navy',part=f'metric{i}')
        y+=hh+.12
    y=statement(sl,'因此发现',c['takeaway'],y)
    if limits:
        y=statement(sl,'证据边界','；'.join(limits),y)
    if y>FOOT_Y-.065:raise ContractError(f'LAYOUT_TEXT_CAPACITY_EXCEEDED:FREEFORM_PAGE_CAPACITY_EXCEEDED:needed_{y:.2f}:limit_{FOOT_Y-.065:.2f}')
    return y

def baseline_freeform(sl,c,claims,start):
    question=c.get('question') or (claims[0]['question'] if claims else c['observation'])
    y=statement(sl,'研究问题',question,max(2.30,start))
    y=statement(sl,'作者怎么做',c['method'],y)
    return y+.06

def choose_composition(c,assets,root):
    forced=c.get('composition')
    valid={'logic','figure_hero','figure_split','figure_pair','figure_stack','text_synthesis'}
    if forced and forced not in valid:raise ContractError('FREEFORM_COMPOSITION_UNKNOWN:'+str(forced))
    ids=c.get('figure_asset_ids',[]);role=c.get('narrative_role','')
    if forced:
        if forced.startswith('figure') and not ids:raise ContractError('FREEFORM_COMPOSITION_REQUIRES_FIGURE')
        if forced in ('figure_pair','figure_stack') and len(ids)!=2:
            raise ContractError('FREEFORM_COMPOSITION_REQUIRES_TWO_FIGURES')
        if forced in ('figure_hero','figure_split') and len(ids)!=1:
            raise ContractError('FREEFORM_COMPOSITION_REQUIRES_ONE_FIGURE')
        if forced in ('logic','text_synthesis') and ids:
            raise ContractError('FREEFORM_COMPOSITION_WOULD_HIDE_FIGURES')
        return forced
    if not ids:return 'text_synthesis' if role in ('synthesis','limits') else 'logic'
    ratios=[]
    for aid in ids:
        a=assets[aid]
        with Image.open(within(root,Path(root)/a['path'])) as im:ratios.append(im.width/im.height)
    if len(ids)==1:
        return 'figure_split' if ratios[0]<.91 and role in ('method','finding','comparison') else 'figure_hero'
    # Select the composition which gives the smaller panel the best *readable*
    # physical height. Moderately wide figures tend to benefit from side-by-side;
    # extremely wide plots from full-width vertical stacking.
    assumed_h=3.5
    pair_min=min((CONTENT_W-.20)/2/r for r in ratios)
    stack_min=min(min(CONTENT_W/r,(assumed_h-.09)/2-.30) for r in ratios)
    if min(ratios)<1.10 and max(ratios)>2.15:
        return 'figure_pair'  # retain portrait panel; still warn on tiny wide panel
    return 'figure_stack' if stack_min>pair_min+.10 else 'figure_pair'

def navigation(sl,c,y,claims,metrics,limits):
    # Full research roadmap without forcing fixed 1:1 RSU-to-card structure.
    question=c.get('question') or claims[0]['question']
    y=statement(sl,'核心问题',question,y)
    y=heading(sl,'科研逻辑 · 阅读导航',y+.08)
    steps=c.get('flow_steps') or [c['method'],c['observation']]
    n=len(steps)
    if n>6:raise ContractError('FREEFORM_FLOW_TOO_MANY_NODES')
    # Flexible two-row layout: each independent step is a reading node, not experimental order.
    cols=2 if n>3 else min(n,3);rows=math.ceil(n/cols)
    cellw=(CONTENT_W-(cols-1)*.20)/cols
    cellh=1.09 if rows>1 else 1.25
    for i,v in enumerate(steps):
        col=i%cols;row=i//cols
        x=L+col*(cellw+.20);ny=y+row*(cellh+.15)
        R.rect(sl,x,ny,cellw,cellh,['light','mint','peach'][i%3],rounded=True)
        put(sl,f'{i+1:02}',x+.13,ny+.10,.41,11.3,'royal',True,part=f'step{i}number')
        put(sl,v,x+.59,ny+.12,cellw-.72,11.6,'navy',True,max_h=cellh-.14,part=f'step{i}')
    y+=rows*(cellh+.15)+.04
    put(sl,'注：节点用于阅读组织，不代表实验真实先后或因果关系。',L,y,CONTENT_W,8.3,'muted',part='logic_disclaimer')
    y+=.40
    y=statement(sl,'研究路径',c['method'],y)
    return summary(sl,c,metrics,limits,y)

def draw_story_visual(sl,c,aa,root,y,metrics,limits):
    images=c.get('figure_asset_ids',[])
    mode=choose_composition(c,aa,root)
    meta=[]
    if mode in ('logic','text_synthesis'):
        y2=navigation(sl,c,y,[{'question':c.get('question') or ''}],metrics,limits)
        return y2,meta,mode
    # Fit the entire scientific explanation FIRST, give the remaining (bounded)
    # space to genuine figures. An impossible page is refused; no hidden truncation.
    obs_h,take_h,lim_h,mets_h=narrative_sizes(c,metrics,limits)
    lower=sum(max(.35,h) for h in (obs_h,take_h,lim_h)) + mets_h + .30 + .46
    upper=baseline_freeform(sl,c,[{'question':c.get('question') or c['observation']}],y)
    if upper>3.85:raise ContractError('FREEFORM_METHOD_TOO_LONG')
    figure_y=upper+.12
    figure_h=FOOT_Y-.12-lower-figure_y
    if figure_h<1.65:raise ContractError(f'LAYOUT_TEXT_CAPACITY_EXCEEDED:FREEFORM_NOT_ENOUGH_FIGURE_SPACE:{figure_h:.2f}')
    max_figure_h={'high':4.70,'balanced':4.12,'low':3.35}.get(c.get('figure_priority','balanced'))
    if max_figure_h is None:raise ContractError('FREEFORM_FIGURE_PRIORITY_UNKNOWN')
    if figure_h>max_figure_h:figure_h=max_figure_h
    ids=images
    if mode=='figure_hero':
        a=aa[ids[0]];meta.append(draw_image(sl,a,root,L,figure_y,CONTENT_W,figure_h))
    elif mode=='figure_split':
        # Portrait/vertical panel retains height. Method/explanation stand alongside it.
        a=aa[ids[0]]
        h=figure_h;leftw=min(3.50,CONTENT_W*.54)
        meta.append(draw_image(sl,a,root,L,figure_y,leftw,h))
        x=L+leftw+.22;tw=CONTENT_W-leftw-.22
        put(sl,'怎样解读这幅图？',x,figure_y+.15,tw,10.6,'royal',True,part='image_explain_title')
        put(sl,c['interpretation'],x,figure_y+.58,tw,10.4,'navy',max_h=max(.1,h-.90),part='image_explain')
    elif mode=='figure_pair':
        # Each asset is separately scaled without stretching; no scientific editing.
        gap=.20;w=(CONTENT_W-gap)/2
        for j,aid in enumerate(ids):meta.append(draw_image(sl,aa[aid],root,L+j*(w+gap),figure_y,w,figure_h))
    elif mode=='figure_stack':
        h=(figure_h-.09)/2
        for j,aid in enumerate(ids):meta.append(draw_image(sl,aa[aid],root,L,figure_y+j*(h+.09),CONTENT_W,h))
    # The geometry report explicitly measures pixel visibility; it never asserts pass.
    y2=summary(sl,c,metrics,limits,figure_y+figure_h+.18)
    return y2,meta,mode

def slides_freeform(story,assets,root):
    prs=Presentation();prs.slide_width=Inches(W);prs.slide_height=Inches(H)
    layout=prs.slide_layouts[6]
    aa={a['id']:a for a in assets['assets']}
    claims={x['id']:x for x in story['claims']}
    geometry=[]
    for idx,c in enumerate(story['cards'],1):
        s=prs.slides.add_slide(layout)
        top=intro(s,c,idx,len(story['cards']))
        cl=[claims[x] for x in c['claim_ids']]
        metrics=[m for x in cl for m in x.get('metrics',[])]
        limits=list(dict.fromkeys(x['limit'] for x in cl if x.get('limit')))
        mode=choose_composition(c,aa,root)
        try:
            if mode in ('logic','text_synthesis'):
                end= navigation(s,c,top,cl,metrics,limits)
                im=[]
            else:
                end,im,mode=draw_story_visual(s,c,aa,root,top,metrics,limits)
        except ContractError as ex:
            raise ContractError(f'CARD_{idx}:{ex}') from ex
        footer(s,story,idx,len(story['cards']))
        geometry.append({'card':idx,'layout_type':mode,'content_end':round(end,3),
            'evidence_figure_slots':im,'visible_metric_count':len(metrics),
            'visible_limit_count':len(limits),'planned_figure_policy':c.get('figure_policy','AUTO_SOURCE_RATIO'),
            'mobile_review_required':any(x['mobile_size_review_required'] for x in im)})
    return prs,geometry
