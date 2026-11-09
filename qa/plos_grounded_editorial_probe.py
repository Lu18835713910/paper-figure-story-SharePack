#!/usr/bin/env python3
"""Real journal-source style smoke test: PLOS Computational Biology, CC BY article.

Source figure crops/interpretations remain unreviewed. We do not automatically
publish these examples as completed scientific cards or assert scientific correctness.
"""
import hashlib
import json
import re
import tempfile
import urllib.request
from pathlib import Path

import fitz
from PIL import Image,ImageDraw

from sharepack.ingest import inspect_pdf,extract_regions
from sharepack.common import save,digest
from sharepack.render import build
from sharepack.publisher_figures import fetch_plos_original_figure

DOI="10.1371/journal.pcbi.1012818"
URLS=[
 "https://journals.plos.org/ploscompbiol/article/file?id="+DOI+"&type=manuscript",
 "https://journals.plos.org/ploscompbiol/article/file?id="+DOI+"&type=printable",
 "https://pmc.ncbi.nlm.nih.gov/articles/PMC11957564/pdf/",
]
PAPER={"title":"Gauge fixing for sequence-function relationships",
       "authors_short":"Posfai et al.","journal":"PLOS Computational Biology",
       "doi":DOI,"source_type":"journal"}

def test():
 with tempfile.TemporaryDirectory(prefix="sharepack_plos_style_") as tmp:
  root=Path(tmp);pdf=root/"source.pdf";errors=[]
  for url in URLS:
   try:
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=35) as response:
     b=response.read(30000000)
     kind=response.headers.get("Content-Type")
    if not b.startswith(b"%PDF-"):raise ValueError("NOT_PDF_CONTENT_TYPE:"+str(kind))
    pdf.write_bytes(b);selected=url;break
   except Exception as e:
    errors.append({"url":url,"error":str(e)[:180]})
  report={"article":PAPER,"source_attempts":errors,"original_figures_scientifically_reviewed":False,
          "purpose":"publication-style engineering test; no publisher affiliation"}
  if not pdf.exists():
   report["status"]="SOURCE_UNAVAILABLE"
   print("PLOS_GROUNDED_EDITORIAL_QA="+json.dumps(report,ensure_ascii=False));raise RuntimeError("Source download blocked")
  report["source_url"]=selected;report["source_sha256"]=digest(pdf)
  doc=fitz.open(pdf)
  report["pages"]=len(doc)
  index=inspect_pdf(pdf,root/"index")
  report["publication_hint"]=index.get("publication_hint")
  report["figure_candidates"]=[{"label":v["figure_label"],"page":v["page"]} for v in index["figures"]][:16]
  reg=[]
  for x in index["figures"]:
   if len(reg)>=2:break
   box=fitz.Rect(*x["candidate_rect_pdf_pt"]) & doc[x["page"]-1].rect
   if box.width<100 or box.height<75:continue
   reg.append({"id":"candidate"+str(len(reg)+1),"figure":x["figure_label"],"pdf_page":x["page"],
                "crop_pdf_pt":list(box),"review_status":"PENDING"})
  if reg:
   save(root/"regions.json",{"source_pdf_sha256":digest(pdf),"regions":reg})
   assets=extract_regions(pdf,root/"regions.json",root/"assets")
  else:
   assets={"contract":"sharepack-figure-assets-v1","source_pdf_sha256":digest(pdf),"assets":[]}
   (root/"assets").mkdir();save(root/"assets"/"assets.json",assets)
  figure_ids=[x["id"] for x in assets["assets"]]
  report["unreviewed_asset_count"]=len(figure_ids)
  if figure_ids:
   original=fetch_plos_original_figure(doi=DOI,figure_num=1,
      source_pdf_sha256=digest(pdf),pdf_page=reg[0]["pdf_page"],outdir=root/"assets")
   assets["assets"][0]=original
   save(root/"assets"/"assets.json",assets)
   figure_ids=[x["id"] for x in assets["assets"]]
   report["publisher_original_figure"]={
      "source_url":original["source_url"],"sha256":original["sha256"],
      "pixel_dimensions":original["pixel_dimensions"],
      "review_status":original["review_status"],"content_changed":False
   }

  cards=[];claims=[];sources=[]
  # Research-grounded, author-prepared paraphrases of the article abstract,
  # author summary and Fig. 1 caption. Pending independent science audit.
  cases=[
   ("cover","科学问题","同样预测，为什么模型参数会不同？",
    "不同参数组合可能给出相同预测，该如何解释参数？",
    "作者研究不改变预测结果的规范自由度。",
    "模型参数可以变化，但其预测可能保持相同。",
    "解释参数之前，需要先明确规范约束。",
    "研究结论受具体模型与约束条件限制。"),
   ("framework","理论框架","从自由度到固定规范",
    "怎样去掉不影响预测的冗余参数方向？",
    "为参数设置约束，选择一组可解释的表示。",
    "论文建立了线性规范与正则化方法之间的联系。",
    "常用规范能够纳入同一个数学框架。",
    "不同规范下参数的具体含义仍可能不同。"),
   ("method","方法推导","一个可用于多类模型的规范族",
    "规范固定能否用于不同阶的相互作用模型？",
    "作者从全阶相互作用模型推导规范族。",
    "部分层级规范适用于加性、成对及更高阶模型。",
    "若干已有规范可看作这一规范族的特例。",
    "适用范围依赖模型形式及假设。"),
   ("comparison","Figure 1","三种规范如何改变参数？",
    "三种规范怎样改变参数图？",
    "比较 CRP 模型的三种规范参数图。",
    "热图与序列标识随规范变化。",
    "参数不同，预测可以相同。",
    "这不是新的实验测量。"),
   ("finding","模型解读","参数不同，不意味着预测冲突",
    "如何避免把冗余参数看成真实生物效应？",
    "分析规范变换与参数解释的关系。",
    "规范自由度使部分参数值不能由数据唯一确定。",
    "报告规范选择，是解释模型的必要步骤。",
    "规范固定不保证模型本身已经充分验证。"),
   ("finding","应用案例","复杂序列模型能否在局部简化？",
    "层级规范能帮助理解蛋白质功能景观吗？",
    "论文分析了 GB1 蛋白的经验成对相互作用景观。",
    "不同规范可用于探索局部序列空间的结构。",
    "在特定局部区域，复杂模型可能得到有效近似。",
    "局部可简化不等于全局都是简单关系。"),
   ("synthesis","研究认识","预测准确，还需要解释得通",
    "这项工作最重要的认识是什么？",
    "结合理论推导与序列功能模型应用。",
    "常见规范被统一，并展示了模型探索用途。",
    "预测相同不代表参数解释天然唯一。",
    "数学上的参数解释不等同于实验因果机制。"),
   ("limits","研究边界","固定规范，也不能替代独立验证",
    "选定规范后，模型就一定可信了吗？",
    "分别判断模型假设、数据和规范约束。",
    "规范固定可处理部分参数不可辨识问题。",
    "需要把参数可解释性与预测验证分开评价。",
    "生物学结论仍需要独立证据支持。")
  ]
  cards=[];claims=[];sources=[]
  for i,(role,stage,title,question,method,observation,takeaway,limit) in enumerate(cases,1):
   cid="C"+str(i);sid="S"+str(i)
   source_page=5 if i==4 else 1
   sources.append({"id":sid,"pdf_page":source_page})
   claims.append({"id":cid,"question":question,"method":method,
      "observation":observation,"meaning":takeaway,"limit":limit,
      "source_ids":[sid],"required":True,"review_status":"PARTIAL"})
   ids_for_card=[figure_ids[0]] if i==4 and figure_ids else []
   cards.append({"order":i,"stage":stage,"title":title,
      "intro":"Posfai et al. · PLOS Comput Biol · 2025",
      "question":question,"method":method,"observation":observation,
      "takeaway":takeaway,"interpretation":takeaway,
      "narrative_role":role,
      "layout_type":"evidence" if ids_for_card else "framework" if role=="framework" else "synthesis" if role in ("synthesis","limits") else "cover",
      "claim_ids":[cid],"figure_asset_ids":ids_for_card,
      "flow_steps":["发现参数冗余","固定数学规范","比较不同表示","解释序列功能"] if role=="framework" else []})
  story={"contract":"sharepack-story-v1","paper":PAPER,"pdf_sha256":digest(pdf),"profile":"standard",
         "review_status":"PARTIAL","formal_ready":False,"sources":sources,"claims":claims,"cards":cards}
  save(root/"story.json",story)
  try:
   qa=build(root/"story.json",root/"assets"/"assets.json",root/"render",
            layout_engine="editorial",render_png=True,
            pdf_index_path=root/"index"/"pdf_index.json")
   report["style"]=qa["publication_style"]
   report["render"]={"pptx":True,"png_count":qa.get("png_count",0),"layout_types":[x["layout_type"] for x in qa["layout_geometry"]],"mobile_type_warning_count":len(qa["static_visual_qa"]["mobile_type_warnings"]),
                     "text_collisions":qa["static_visual_qa"]["text_text_collisions"][:6],
                     "small_panels":qa["static_visual_qa"]["small_panel_slots"],
                     "formal_ready":qa["contract_qa"]["formal_ready"]}
   if report["style"]["style_id"]!="journal-plos-computational-biology":
    raise AssertionError("Unexpected journal theme selection")
   if qa.get("png_count")!=8:raise AssertionError("Missing slide renders")
   # Public article is CC BY 4.0, but this is still a clearly unreviewed test.
   preview=Path("qa_preview");preview.mkdir(exist_ok=True)
   sheet=Image.open(root/"render"/"00_contact_sheet.png").convert("RGB")
   canvas=Image.new("RGB",(sheet.width,sheet.height+95),(243,247,249))
   canvas.paste(sheet,(0,95))
   draw=ImageDraw.Draw(canvas)
   draw.text((16,12),"PLOS / SOURCE-GROUNDED EDITORIAL / SCIENCE REVIEW PENDING",fill=(34,42,53))
   draw.text((16,45),"CC BY: Posfai et al. (2025), DOI "+DOI+" | NOT PUBLISHER OFFICIAL",fill=(34,42,53))
   canvas.save(preview/"plos_grounded_editorial_contact_sheet.png")
   report["status"]="PPTX_AND_PNG_ENGINEERING_PASS"
  except Exception as e:
   report["status"]="RENDER_FAILED";report["render_error"]=type(e).__name__+": "+str(e)
   print("PLOS_GROUNDED_EDITORIAL_QA="+json.dumps(report,ensure_ascii=False));raise
  print("PLOS_GROUNDED_EDITORIAL_QA="+json.dumps(report,ensure_ascii=False))
if __name__=="__main__":test()
