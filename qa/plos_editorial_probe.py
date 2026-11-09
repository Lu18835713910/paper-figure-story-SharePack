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
   print("PLOS_EDITORIAL_QA="+json.dumps(report,ensure_ascii=False));raise RuntimeError("Source download blocked")
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

  cards=[];claims=[];sources=[]
  stages=["研究问题","理论框架","模型设定","方法比较","案例分析","适用条件","结果含义","证据边界"]
  for i,stage in enumerate(stages,1):
   cid="C"+str(i);sid="S"+str(i)
   sources.append({"id":sid,"pdf_page":1})
   claims.append({"id":cid,"question":"什么是序列—功能关系中的规范选择？",
      "method":"比较序列—功能模型中的参数表示与变换。",
      "observation":"本页为期刊风格路由测试，不提供独立复核后的实验发现。",
      "meaning":"仅评价PPTX结构和可读性，不据此作出科学发现判断。",
      "limit":"论文内容与裁图仍需人工审核。","source_ids":[sid],"required":True,
      "review_status":"PARTIAL"})
   aids=[figure_ids[0]] if i==4 and figure_ids else []
   cards.append({"order":i,"stage":stage,"title":stage+"｜期刊视觉测试",
      "intro":"实际PLOS期刊PDF输入；内容为未经审核的工程测试文本。",
      "question":"来源与Figure是否清晰？","method":"检验来源和布局。",
      "observation":"本卡未获科学内容核准。","takeaway":"验证编辑风格，不验证科研结论。",
      "interpretation":"图像为未审核的候选裁图。",
      "narrative_role":["cover","framework","method","comparison","finding","finding","synthesis","limits"][i-1],
      "layout_type":"evidence","claim_ids":[cid],"figure_asset_ids":aids,
      "flow_steps":["研究问题","方法比较","研究意义","研究限制"]})
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
   draw.text((16,12),"PLOS COMPUTATIONAL BIOLOGY / EDITORIAL LAYOUT / UNREVIEWED",fill=(34,42,53))
   draw.text((16,45),"CC BY: Posfai et al. (2025), DOI "+DOI+" | NOT PUBLISHER OFFICIAL",fill=(34,42,53))
   canvas.save(preview/"plos_editorial_test_contact_sheet.png")
   report["status"]="PPTX_AND_PNG_ENGINEERING_PASS"
  except Exception as e:
   report["status"]="RENDER_FAILED";report["render_error"]=type(e).__name__+": "+str(e)
   print("PLOS_EDITORIAL_QA="+json.dumps(report,ensure_ascii=False));raise
  print("PLOS_EDITORIAL_QA="+json.dumps(report,ensure_ascii=False))
if __name__=="__main__":test()
