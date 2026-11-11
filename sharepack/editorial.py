"""Large-type, journal-edition editorial layout for source-linked story cards.

In contrast to freeform, this engine uses a small set of narrative roles rather
than reusing one flowchart. It does not invent claims, crop source figures, hide
metrics, or reduce text size to force a page to pass. It is an opt-in QA engine.
"""
from __future__ import annotations
import math
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Inches
from pptx.enum.text import PP_ALIGN

from .common import ContractError, within
from .publication_styles import current_style
from .brand_assets import current_logo
from . import render as R

W,H = 7.5,10.0
X,RIGHT = .50,7.00
CW=RIGHT-X
BOTTOM=9.18
BODY=17.4
LABEL=17.0

def weight_len(s):
    return R._cell_len(str(s))

def height(s,w,pt,*,line_spacing=1.22):
    if not str(s).strip():
        return .0
    p=max(1.,w*72/(pt*1.16))
    lines=sum(max(1,math.ceil(weight_len(t)/p)) for t in str(s).split("\n"))
    return lines*pt*line_spacing/72+.10

def put(sl,value,x,y,w,pt=BODY,color="navy",bold=False,*,cap=None,where="body",align=PP_ALIGN.LEFT):
    if not str(value).strip():
        return y
    h=height(value,w,pt)
    if cap is not None and h>cap+.01:
        raise ContractError("EDITORIAL_CONTENT_REPLAN:"+where+":"+str(round(h,2))+">"+str(cap))
    R._checked_text(sl,value,x,y,w,h,pt,color,bold,align,label="editorial_"+where)
    return y+h

def rule(sl,y):
    R.rect(sl,X,y,CW,.017,"border")

def top(sl,c,i,n):
    R.rect(sl,0,0,W,H,"bg")
    style=current_style()
    is_plos=style is not None and style.style_id=="journal-plos-computational-biology"
    if is_plos:
        # Based on the real article webpage and the printable PDF, not a generic
        # "academic dark mode": gray site masthead, horizontal blue rule and
        # black-on-white article layout. No imitation/alteration of logo art.
        R.rect(sl,0,0,W,.76,"EFEFEF")
        R.rect(sl,0,0,W,.045,"royal")
    else:
        R.rect(sl,0,0,.085,H,"royal")
    logo=current_logo()
    if logo is not None:
        R.embed_authorized_logo(sl,logo,X,.13,2.34,.51)
        x=3.04;mw=2.58
        masthead="SHAREPACK  |  NOTES" if is_plos else style.masthead
        mastcolor="282B62" if is_plos else "royal"
    else:
        x=X;mw=5.12
        masthead=("PLOS COMPUTATIONAL BIOLOGY" if is_plos
                  else style.masthead if style else "SHAREPACK / RESEARCH NOTES")
        mastcolor="282B62" if is_plos else "royal"
    put(sl,masthead,x,.20,mw,16.2 if is_plos else 12.0,mastcolor,True,cap=.43,where="masthead")
    put(sl,f"{i:02d} / {n:02d}",5.84,.20,1.14,16.2 if is_plos else 12.0,"525A65" if is_plos else "muted",cap=.43,where="counter",align=PP_ALIGN.RIGHT)
    rule(sl,.76)
    stage=str(c["stage"]).upper()
    put(sl,stage,X,.94,CW,16.4,"royal",True,cap=.40,where="stage")
    title=str(c["title"])
    size=27 if weight_len(title)>29 else 30
    y=put(sl,title,X,1.36,CW,size,"navy",True,cap=1.24,where="title")
    y=put(sl,c["intro"],X,y+.14,CW,17.1,"muted",cap=.92,where="intro")
    if y>3.08:
        raise ContractError("EDITORIAL_HEADER_NEEDS_REPLAN")
    return max(2.77,y+.12)

def bottom(sl,story):
    rule(sl,9.17)
    paper=story["paper"]
    cite=f"DOI: {paper['doi']}"
    # Journal is already identified in the masthead; keep short source citation
    # at the bottom rather than squeezing two or three unreadable text lines.
    put(sl,cite,X,9.22,CW,16.2,"muted",cap=.43,where="citation")
    put(sl,"SharePack · 独立论文解读，非期刊官方作品",
        X,9.61,CW,16.2,"royal",cap=.39,where="independence")

def block(sl,label,content,y,*,main=False,pt=BODY,max_h=1.05):
    if not str(content).strip():
        return y
    # Labels are first-class visible text, not tiny captions.
    yy=put(sl,label,X,y,CW,LABEL,"royal",True,cap=.42,where=label+"_label")
    yy+=.10
    sz=21.5 if main else pt
    h=height(content,CW-.10,sz)
    if h>max_h+.01:
        raise ContractError("EDITORIAL_REPLAN_BLOCK:"+label+":"+str(round(h,2)))
    yy=put(sl,content,X+.06,yy,CW-.11,sz,"navy",main,cap=max_h,where=label+"_content")
    return yy+.20

def stacked_blocks(sl,card,limits,metrics,start,role):
    y=start
    q=card.get("question") or card["observation"]
    if role=="cover":
        # Main scientific question = visual anchor, not a four-box diagram.
        y=block(sl,"核心科学问题",q,y,main=True,pt=23.0,max_h=1.55)
        rule(sl,y+.05);y+=.30
        y=block(sl,"研究采用什么方法",card["method"],y,max_h=1.05)
        y=block(sl,"目前观察",card["observation"],y,max_h=1.05)
        y=block(sl,"这篇文章想说明",card["takeaway"],y,main=True,max_h=1.25)
    elif role=="limits":
        y=block(sl,"哪些结论获得支持",card["observation"],y,main=True,max_h=1.50)
        y=block(sl,"目前还不能证明", "；".join(limits) or card["takeaway"],y,main=True,max_h=1.50)
        y=block(sl,"接下来如何核实",card["method"],y,max_h=1.15)
        y=block(sl,"如何正确理解",card["takeaway"],y,max_h=1.10)
    elif role=="synthesis":
        y=block(sl,"最重要的发现",card["takeaway"],y,main=True,max_h=1.50)
        y=block(sl,"研究依据",card["method"],y,max_h=1.10)
        y=block(sl,"实际观察",card["observation"],y,max_h=1.10)
        if limits:y=block(sl,"证据边界","；".join(limits),y,max_h=1.10)
    else:
        y=block(sl,"研究问题",q,y,main=True,max_h=1.35)
        y=block(sl,"实验或分析方法",card["method"],y,max_h=1.15)
        y=block(sl,"观察到什么",card["observation"],y,max_h=1.15)
        y=block(sl,"科学含义",card["takeaway"],y,main=True,max_h=1.35)
        if limits:y=block(sl,"证据边界","；".join(limits),y,max_h=1.0)
    for m in metrics:
        val=f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}"
        y=block(sl,"关键数字",val,y,max_h=1.15)
    if y>BOTTOM:
        raise ContractError(f"EDITORIAL_REPLAN_PAGE:{role}:{y:.2f}")
    return y

def framework(sl,c,limits,metrics,start):
    """Compact editorial framework with two-column steps, never a full-page cloned flowchart."""
    def row(label,val,y,*,accent=False):
        if not str(val).strip():
            return y
        labelw=1.73
        textw=CW-2.00
        required=max(height(label,labelw,16.5),height(val,textw,17.1))
        rh=max(.73,required+.19)
        if rh>1.08:
            raise ContractError("EDITORIAL_FRAMEWORK_ROW_REPLAN:"+label)
        R.rect(sl,X,y,.052,rh-.04,"royal" if accent else "border")
        put(sl,label,X+.12,y+.10,labelw,16.5,"royal",True,cap=rh-.10,where="framework_label")
        put(sl,val,X+1.94,y+.10,textw,17.1,"navy",accent,cap=rh-.10,where="framework_value")
        return y+rh+.03
    y=row("核心科学问题",c.get("question") or c["observation"],start,accent=True)
    y=row("研究策略",c["method"],y)
    steps=c.get("flow_steps") or []
    if steps:
        if len(steps)>4:
            raise ContractError("EDITORIAL_FRAMEWORK_STEPS_MAX_4")
        y=put(sl,"研究证据如何推进",X,y+.02,CW,16.2,"royal",True,where="flowheading")+.06
        gap=.17
        cellw=(CW-gap)/2
        for j,step in enumerate(steps):
            ix=j%2;iy=j//2
            xx=X+ix*(cellw+gap); yy=y+iy*.75
            R.rect(sl,xx,yy,cellw,.69,["light","mint","peach","light"][j],rounded=True)
            put(sl,f"{j+1:02d}",xx+.14,yy+.15,.43,16.3,"royal",True,cap=.45,where="step_number")
            put(sl,step,xx+.66,yy+.13,cellw-.78,17.2,"navy",True,cap=.53,where="step")
        y+=math.ceil(len(steps)/2)*.75+.07
    y=row("实际观察",c["observation"],y)
    y=row("核心认识",c["takeaway"],y,accent=True)
    if limits:
        y=row("证据边界","；".join(limits),y)
    for m in metrics:
        val=f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}"
        y=row("关键数字",val,y)
    if y>BOTTOM:
        raise ContractError("EDITORIAL_REPLAN_FRAMEWORK:"+str(round(y,2)))
    return y


def image(sl,asset,root,x,y,w,h):
    p=within(root,Path(root)/asset["path"])
    with Image.open(p) as im:
        r=im.width/im.height
    # A neutral light artboard prevents low-contrast axes from disappearing on dark themes.
    R.rect(sl,x,y,w,h,"FFFFFF",rounded=True)
    usable_h=h-.60
    iw=min(w-.16,usable_h*r)
    ih=iw/r
    if iw<1.4 or ih<1.6:
        # Reject very small source figure views rather than pretending they are readable.
        raise ContractError("EDITORIAL_FIGURE_REPLAN_UNREADABLE:"+asset["id"])
    xx=x+(w-iw)/2
    yy=y+(usable_h-ih)/2+.02
    sl.shapes.add_picture(str(p),Inches(xx),Inches(yy),width=Inches(iw),height=Inches(ih))
    cap=f"{asset['figure']} · PDF p.{asset.get('pdf_page','?')} · 原图待核验"
    put(sl,cap,x+.10,y+h-.52,w-.16,16.3,"263643",cap=.47,where="figure_source")
    return {"asset_id":asset["id"],"draw_width_in":round(iw,3),
        "draw_height_in":round(ih,3),"review_status":asset.get("review_status","PENDING"),
        "mobile_review_required":False,"slot":[round(x,3),round(y,3),round(w,3),round(h,3)]}

def evidence(sl,c,limits,metrics,assets,root,start):
    """Full-width scientific figure plus compact, readable source-linked explanation.

    Uses actual content measurements for explanation rows. No auto font shrink,
    cropped explanations or unreviewed scientific claims are invented.
    """
    ids=c.get("figure_asset_ids",[])
    if not ids:
        return stacked_blocks(sl,c,limits,metrics,start,c.get("narrative_role","finding")),[]
    if len(ids)>2:
        raise ContractError("EDITORIAL_REPLAN_MAX_TWO_FIGURES")

    def row_height(text,sz=17.4):
        return max(.68,height(text,CW-1.37,sz)+.15)
    def evidence_row(label,text,y,sz=17.4):
        rh=row_height(text,sz)
        if rh>1.12:
            raise ContractError("EDITORIAL_EVIDENCE_REPLAN_TEXT:"+label)
        R.rect(sl,X,y,.048,rh-.06,"royal")
        short_label={"观察结果":"观察","核心发现":"发现","图示解读":"解读","证据边界":"边界","关键数字":"数据"}.get(label,label)
        put(sl,short_label,X+.11,y+.10,1.05,16.3,"royal",True,cap=rh-.10,where="evidence_label")
        put(sl,text,X+1.32,y+.09,CW-1.37,sz,"navy",False,cap=rh-.10,where="evidence_text")
        return y+rh+.09

    q=c.get("question") or c["observation"]
    # Direct question and one-line method: avoid repeating title-like labels
    # above the Figure when it must be large enough for mobile inspection.
    y=put(sl,q,X+.04,start,CW-.10,19.2,"navy",True,cap=.85,where="evidence_question")+.08
    y=put(sl,"方法："+c["method"],X+.04,y,CW-.12,16.5,"muted",False,cap=.72,where="evidence_method")+.09

    # A source Figure card should make the data the main character.
    # Join, but do not drop, observation and takeaway: the detailed analytical
    # explanation can occupy the next story card when needed.
    evidence_readout="观察："+c["observation"]+"；解读："+c["takeaway"]
    bottom_items=[("图示解读",evidence_readout,17.2)]
    if limits:
        bottom_items.append(("证据边界","；".join(limits),16.4))
    for m in metrics:
        v=f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}"
        bottom_items.append(("关键数字",v,16.8))
    need=sum(row_height(value,size)+.09 for _,value,size in bottom_items)+.15
    max_space=BOTTOM-y-need-.10
    figure_h=min(5.05,max_space)
    if figure_h<2.0:
        raise ContractError("EDITORIAL_FIGURE_REPLAN_NO_SPACE:"+str(round(figure_h,2)))

    pics=[]
    if len(ids)==1:
        pics.append(image(sl,assets[ids[0]],root,X,y,CW,figure_h))
    else:
        hh=(figure_h-.14)/2
        if hh<1.85:
            raise ContractError("EDITORIAL_TWO_FIGURES_REPLAN")
        pics.append(image(sl,assets[ids[0]],root,X,y,CW,hh))
        pics.append(image(sl,assets[ids[1]],root,X,y+hh+.14,CW,hh))
    y+=figure_h+.15
    for label,value,sz in bottom_items:
        y=evidence_row(label,value,y,sz)
    if y>BOTTOM:
        raise ContractError("EDITORIAL_REPLAN_EVIDENCE:"+str(round(y,2)))
    return y,pics


def slides_editorial(story,assets,root):
    prs=Presentation()
    prs.slide_width=Inches(W)
    prs.slide_height=Inches(H)
    aa={a["id"]:a for a in assets["assets"]}
    cs={c["id"]:c for c in story["claims"]}
    geometry=[]
    for i,c in enumerate(story["cards"],1):
        sl=prs.slides.add_slide(prs.slide_layouts[6])
        y=top(sl,c,i,len(story["cards"]))
        chosen=[cs[k] for k in c["claim_ids"]]
        mets=[m for claim in chosen for m in claim.get("metrics",[])]
        limits=list(dict.fromkeys(q["limit"] for q in chosen if q.get("limit")))
        role=c.get("narrative_role") or "finding"
        try:
            if c.get("figure_asset_ids"):
                last,pics=evidence(sl,c,limits,mets,aa,root,y)
                layout="editorial_evidence"
            elif role=="framework":
                last=framework(sl,c,limits,mets,y)
                pics=[]
                layout="editorial_framework"
            else:
                last=stacked_blocks(sl,c,limits,mets,y,role)
                pics=[]
                layout="editorial_"+role
        except ContractError as ex:
            raise ContractError(f"CARD_{i}:{ex}") from ex
        bottom(sl,story)
        geometry.append({"card":i,"layout_type":layout,"content_end":round(last,3),
            "evidence_figure_slots":pics,"visible_metric_count":len(mets),
            "visible_limit_count":len(limits),"mobile_review_required":False})
    return prs,geometry
