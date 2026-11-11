"""Agent-directed, constraint-checked journal card composition (opt-in QA).

A model/agent may express per-card preferences, never raw coordinates or font
sizes. This compositor tries bounded editorial variants, discards failed
candidate slides and records exactly what was selected and rejected. Original
science, sources and figures are never rewritten to force layout acceptance.
"""
from __future__ import annotations
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

from .common import ContractError, load, digest
from . import editorial as E

CONTRACT="sharepack-agent-layout-plan-v1"
ALLOWED={"essay","classic","framework","figure_first","figure_explain"}
ALLOWED_KEYS={"card","preferred","rationale"}

def read_plan(path, story_path, assets_path, story):
    """Accept only source-bound layout preferences. No free-form layout code."""
    if path is None:
        return {},{"status":"AUTO_HEURISTIC","contract":CONTRACT}
    data=load(Path(path))
    if data.get("contract")!=CONTRACT:
        raise ContractError("AGENT_LAYOUT_CONTRACT_UNKNOWN")
    if data.get("story_sha256")!=digest(story_path) or data.get("assets_sha256")!=digest(assets_path):
        raise ContractError("AGENT_LAYOUT_SOURCE_HASH_MISMATCH")
    if not isinstance(data.get("cards"),list):
        raise ContractError("AGENT_LAYOUT_CARDS_INVALID")
    hints={}
    allowed_ids={int(c["order"]) for c in story["cards"]}
    for item in data["cards"]:
        if not isinstance(item,dict) or set(item)-ALLOWED_KEYS:
            raise ContractError("AGENT_LAYOUT_UNKNOWN_FIELDS")
        i=item.get("card")
        if type(i) is not int or i not in allowed_ids or i in hints:
            raise ContractError("AGENT_LAYOUT_CARD_DUPLICATE_OR_UNKNOWN")
        if item.get("preferred") not in ALLOWED:
            raise ContractError("AGENT_LAYOUT_VARIANT_UNKNOWN")
        rationale=item.get("rationale","")
        if not isinstance(rationale,str) or len(rationale)>600:
            raise ContractError("AGENT_LAYOUT_RATIONALE_INVALID")
        hints[i]=item["preferred"]
    return hints,{"status":"SOURCE_BOUND_AGENT_PLAN","contract":CONTRACT,
                  "file_sha256":digest(path),"cards_with_preferences":len(hints)}

def candidates(card, assets, hint):
    ids=card.get("figure_asset_ids",[])
    role=card.get("narrative_role") or "finding"
    if ids:
        available=["figure_first","figure_explain"]
    elif role=="framework":
        available=["framework","essay","classic"]
    else:
        available=["essay","classic"]
    if hint is not None and hint not in available:
        raise ContractError("AGENT_LAYOUT_VARIANT_INCOMPATIBLE:"+str(card["order"])+":"+hint)
    # Source density and narrative role affect default layout, not only a generic
    # per-article template. Agent preference only moves a valid variant to first.
    if hint is not None:
        return [hint]+[v for v in available if v!=hint]
    if ids:
        a=assets[ids[0]]
        dims=a.get("pixel_dimensions")
        if isinstance(dims,list) and len(dims)==2 and dims[1]>0:
            ratio=dims[0]/dims[1]
            if ratio<1.2:
                return ["figure_explain","figure_first"]
        return available
    if role in ("cover","limits"):
        return ["classic","essay"]
    return available

def essay(sl,card,limits,metrics,start):
    """Title-forward article spread with clear information hierarchy."""
    role=card.get("narrative_role") or "finding"
    y=start
    # Emphasize the takeaway on synthesis/finding; emphasize the question on
    # methods/cover. This is a semantic rearrangement, not content deletion.
    anchor=card["takeaway"] if role in ("finding","synthesis","limits") else (card.get("question") or card["observation"])
    y=E.block(sl,"本页重点",anchor,y,main=True,max_h=1.63)
    E.rule(sl,y+.06);y+=.32
    if role in ("finding","synthesis","limits"):
        y=E.block(sl,"研究问题",card.get("question") or card["observation"],y,max_h=1.08)
    y=E.block(sl,"方法",card["method"],y,max_h=1.12)
    y=E.block(sl,"研究观察",card["observation"],y,max_h=1.12)
    if role not in ("finding","synthesis","limits"):
        y=E.block(sl,"科学认识",card["takeaway"],y,max_h=1.32)
    if limits:
        y=E.block(sl,"证据边界","；".join(limits),y,max_h=1.13)
    for m in metrics:
        val=f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}"
        y=E.block(sl,"关键数字",val,y,max_h=1.13)
    if y>E.BOTTOM:
        raise ContractError("AGENT_LAYOUT_ESSAY_OVERFLOW")
    return y,[]

def figure_first(sl,card,limits,metrics,assets,root,start):
    """Image-led story page when a large Figure and concise explanation coexist."""
    ids=card.get("figure_asset_ids",[])
    if len(ids)!=1:
        raise ContractError("AGENT_FIGURE_FIRST_REQUIRES_ONE_ASSET")
    y=start
    q=card.get("question") or card["observation"]
    y=E.put(sl,q,E.X,y,E.CW,19.2,"navy",True,cap=.82,where="lead_question")+.10
    method=card["method"]
    observation=card["observation"]
    takeaway=card["takeaway"]
    lim="；".join(limits)
    metric_strings=[f"{m['label']}：{m['value']}｜{m['definition']}；对照：{m['comparison']}" for m in metrics]
    # Reserve all remaining text at mandated font sizes before sizing the
    # Figure. Nothing is clipped or sacrificed for visual preference.
    row_texts=[("研究方法",method,16.8),("观察",observation,17.3),
               ("解释",takeaway,18.0)]
    if lim:row_texts.append(("局限",lim,16.7))
    row_texts.extend(("关键数字",v,16.8) for v in metric_strings)
    text_height=sum(.38+E.height(t,E.CW-.12,fs)+.14 for _,t,fs in row_texts)
    avail=E.BOTTOM-y-text_height-.18
    if avail<2.45:
        raise ContractError("AGENT_FIGURE_FIRST_REPLAN_SPACE")
    fig_height=min(5.05,avail)
    pic=E.image(sl,assets[ids[0]],root,E.X,y,E.CW,fig_height)
    y+=fig_height+.11
    for label,value,fs in row_texts:
        y=E.put(sl,label,E.X,y,E.CW,16.5,"royal",True,cap=.42,where="figfirst_label")+.06
        y=E.put(sl,value,E.X+.04,y,E.CW-.08,fs,"navy",cap=1.15,where="figfirst_text")+.13
    if y>E.BOTTOM:
        raise ContractError("AGENT_FIGURE_FIRST_OVERFLOW")
    return y,[pic]

def render_one(sl,card,claims,assets,root,i,total,variant,story):
    start=E.top(sl,card,i,total)
    selected=[claims[k] for k in card["claim_ids"]]
    metrics=[m for claim in selected for m in claim.get("metrics",[])]
    limits=list(dict.fromkeys(c["limit"] for c in selected if c.get("limit")))
    if variant=="essay":
        y,pics=essay(sl,card,limits,metrics,start)
    elif variant=="classic":
        y=E.stacked_blocks(sl,card,limits,metrics,start,card.get("narrative_role") or "finding")
        pics=[]
    elif variant=="framework":
        y=E.framework(sl,card,limits,metrics,start)
        pics=[]
    elif variant=="figure_first":
        y,pics=figure_first(sl,card,limits,metrics,assets,root,start)
    elif variant=="figure_explain":
        y,pics=E.evidence(sl,card,limits,metrics,assets,root,start)
    else:
        raise ContractError("AGENT_LAYOUT_UNKNOWN_VARIANT")
    E.bottom(sl,story)
    return {"card":i,"layout_type":"flex_"+variant,"content_end":round(y,3),
            "evidence_figure_slots":pics,"visible_metric_count":len(metrics),
            "visible_limit_count":len(limits),
            "mobile_review_required":bool(pics)}

def inspect_slide(sl):
    """Hard stop for shape bounds and text-box intersections, no 0-size hacks."""
    width=Inches(E.W);height=Inches(E.H)
    for j,shape in enumerate(sl.shapes):
        if (shape.left < -500 or shape.top < -500 or
            shape.left+shape.width>width+500 or shape.top+shape.height>height+500):
            raise ContractError("AGENT_LAYOUT_CANVAS_OVERFLOW:"+str(j))
    boxes=[(i,s) for i,s in enumerate(sl.shapes)
           if s.has_text_frame and s.text.strip()]
    for j,(ai,a) in enumerate(boxes):
        for bi,b in boxes[j+1:]:
            dx=min(a.left+a.width,b.left+b.width)-max(a.left,b.left)
            dy=min(a.top+a.height,b.top+b.height)-max(a.top,b.top)
            if dx>Inches(.03) and dy>Inches(.03):
                raise ContractError(f"AGENT_LAYOUT_TEXT_OVERLAP:{ai}:{bi}")

def slides_editorial_flex(story,assets,root,hints=None):
    """Agent suggestions are soft, but **constraints are hard**."""
    hints=hints or {}
    deck=Presentation()
    deck.slide_width=Inches(E.W);deck.slide_height=Inches(E.H)
    amap={a["id"]:a for a in assets["assets"]}
    cmap={c["id"]:c for c in story["claims"]}
    geometries=[]
    for i,card in enumerate(story["cards"],1):
        tried=[];chosen=None
        variants=candidates(card,amap,hints.get(card["order"]))
        for variant in variants:
            trial=Presentation();trial.slide_width=Inches(E.W);trial.slide_height=Inches(E.H)
            sl=trial.slides.add_slide(trial.slide_layouts[6])
            try:
                geom=render_one(sl,card,cmap,amap,root,i,len(story["cards"]),variant,story)
                inspect_slide(sl)
                chosen=variant
                break
            except ContractError as ex:
                tried.append({"variant":variant,"rejected":str(ex)[:200]})
        if chosen is None:
            raise ContractError("AGENT_LAYOUT_REPLAN_REQUIRED_CARD_"+str(i)+":"+
                                ";".join(x["variant"]+"="+x["rejected"] for x in tried))
        target=deck.slides.add_slide(deck.slide_layouts[6])
        geom=render_one(target,card,cmap,amap,root,i,len(story["cards"]),chosen,story)
        inspect_slide(target)
        geom["agent_preference"]=hints.get(card["order"])
        geom["alternative_variants_rejected"]=tried
        geom["decision"]=("AGENT_PREFERENCE_ACCEPTED" if hints.get(card["order"])==chosen
                          else "FALLBACK_ACCEPTED" if hints.get(card["order"]) else "AUTO_ACCEPTED")
        geometries.append(geom)
    return deck,geometries
