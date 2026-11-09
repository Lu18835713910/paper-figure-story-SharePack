#!/usr/bin/env python3
"""Second-paper smoke test using the public scVI preprint (not its journal layout).
No scientific/panel review is implied. Run in isolated workspace. No outputs are published.
"""
from pathlib import Path
import tempfile, urllib.request, json, hashlib, re
import fitz
from sharepack.ingest import inspect_pdf,extract_regions
from sharepack.common import save,digest
from sharepack.contract import validate_story
from sharepack.render import build

URLS=[
"https://arxiv.org/pdf/1709.02082",
"https://export.arxiv.org/pdf/1709.02082",
"https://escholarship.org/content/qt5777r2c7/qt5777r2c7.pdf",
"https://pmc.ncbi.nlm.nih.gov/articles/PMC6289068/pdf/nihms1510930.pdf",
]
PAPER={"title":"A deep generative model for gene expression profiles from single-cell RNA sequencing",
       "doi":"10.48550/arXiv.1709.02082","authors_short":"Lopez et al.",
       "journal":"arXiv preprint (2017); related Nature Methods paper (2018)"}
SPECS=[
 ("cover","科研问题","为什么单细胞表达数据需要概率模型？","细胞表达存在技术噪声和生物变异。","考虑技术因素的概率生成模型","scVI提出对单细胞表达分布进行概率建模。","不等于消除了所有测序偏差。"),
 ("framework","研究框架","scVI 如何表示单细胞？","将观测的基因表达转化为潜在表示。","构建带有神经网络的生成过程","低维潜在状态可用于多种分析任务。","潜在空间可解释性仍需外部检验。"),
 ("method","模型结构","如何把测序深度和批次纳入模型？","建立包含潜在变量与技术协变量的模型。","用变分推断与随机优化拟合","框架考虑批次效应及测序深度。","模型前提与归一化策略决定适用性。"),
 ("comparison","计算性能","模型能否扩展到大量细胞？","比较方法在大规模单细胞数据上的效率。","评估运行时间与可扩展性","作者报告可扩展到百万细胞规模。","运行条件与基准规模需参照原文。"),
 ("finding","数据表示","潜在表示能保留哪些细胞差异？","比较不同方法得到的细胞结构。","评估聚类与表示结果","作者在多个单细胞任务中比较 scVI 和基线。","聚类不能自动证明新的细胞类型。"),
 ("finding","去批次效应","如何区分技术差异与生物差异？","分析跨批次细胞表示。","比较批次对齐与生物群体保持情况","作者展示批次校正应用。","批次混合不等于完全去除混杂。"),
 ("synthesis","差异表达","生成模型如何支持差异表达？","构建基于模型的统计比较。","评估差异表达与传统分析的差别","框架支持基于概率的比较。","统计关联与生物学因果不能混同。"),
 ("limits","结论边界","如何理解方法价值与尚未解决的问题？","从多个任务综合评价。","明确适用条件和未验证场景","scVI 将多个分析任务纳入统一框架。","这次仅是工程压力测试，内容未经独立科研审查。"),
]

def run():
 with tempfile.TemporaryDirectory(prefix="scvi_real_article_QA_") as tmp:
  root=Path(tmp);pdf=root/"scvi_article.pdf";attempts=[]
  for url in URLS:
   try:
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=35) as res:
     data=res.read(20000000)
     info={"url":res.url,"status":res.status,"type":res.headers.get("Content-Type"),"first_bytes":data[:20].decode("utf8","replace")}
    if not data.startswith(b"%PDF-"):raise ValueError("Not PDF "+json.dumps(info))
    pdf.write_bytes(data);chosen=url;break
   except Exception as e:attempts.append({"url":url,"error":str(e)[:190]})
  rep={"paper":"scVI arXiv preprint 1709.02082","downloads":attempts,"pfs_used":False}
  if not pdf.is_file():
   rep["status"]="SOURCE_PDF_UNAVAILABLE"
   print("SCVI_REAL_PAPER_QA="+json.dumps(rep,ensure_ascii=False));raise RuntimeError("No PDF")
  rep["source_url"]=chosen;rep["source_sha256"]=digest(pdf)
  doc=fitz.open(pdf);rep["pages"]=len(doc)
  idx=inspect_pdf(pdf,root/"index")
  rep["captions"]={"count":len(idx["figures"]),"labels":[x["figure_label"] for x in idx["figures"]],"pages":[x["page"] for x in idx["figures"]]}
  seen=set();reg=[]
  for x in idx["figures"]:
   label=x["figure_label"]
   if label in seen or len(reg)>=4:continue
   seen.add(label)
   bbox=fitz.Rect(*x["candidate_rect_pdf_pt"]) & doc[x["page"]-1].rect
   if bbox.height<70:continue
   reg.append({"id":"figure"+re.search(r"\d+",label).group(),"figure":label,"pdf_page":x["page"],
               "crop_pdf_pt":list(bbox),"review_status":"PENDING"})
  rep["eligible_candidate_crops"]=len(reg)
  if not reg:
   rep["status"]="INDEX_WITHOUT_REGION_CANDIDATES"
   print("SCVI_REAL_PAPER_QA="+json.dumps(rep,ensure_ascii=False));return
  save(root/"regions.json",{"source_pdf_sha256":digest(pdf),"regions":reg})
  ass=extract_regions(pdf,root/"regions.json",root/"assets")
  ids=[x["id"] for x in ass["assets"]]
  st={"contract":"sharepack-story-v1","pdf_sha256":digest(pdf),"paper":PAPER,
      "review_status":"PARTIAL","formal_ready":False,"profile":"standard",
      "sources":[],"claims":[],"cards":[],"required_figure_labels":[]}
  for i,(role,stage,title,method,obs,take,limit) in enumerate(SPECS,1):
   q=title
   cid="C"+str(i);sid="S"+str(i)
   st["sources"].append({"id":sid,"pdf_page":min(len(doc),max(1,i))})
   st["claims"].append({"id":cid,"question":q,"method":method,"observation":obs,
      "meaning":take,"limit":limit,"source_ids":[sid],"required":True,"review_status":"PARTIAL"})
   fig=[ids[(i-3)%len(ids)]] if 3<=i<=6 else []
   st["cards"].append({"order":i,"narrative_role":role,"stage":stage,"title":title,
     "intro":"来自另一篇实际论文的工程测试；科学审核尚未完成。",
     "question":q,"method":method,"observation":obs,"takeaway":take,
     "interpretation":take,"figure_asset_ids":fig,"claim_ids":[cid],
     "layout_type":"evidence" if fig else ("framework" if role=="framework" else "synthesis" if role in ("synthesis","limits") else "cover"),
     "flow_steps":["研究问题","设计与模型","验证与对照","结论边界"]})
  save(root/"story.json",st)
  va=validate_story(st,ass,root/"assets",strict=False)
  rep["validation"]={"valid":va["valid"],"formal_ready":va["formal_ready"],"errors":va["errors"],
                     "warnings":va["warnings"][:16]}
  if not va["valid"]:
   rep["status"]="VALIDATION_FAIL"
   print("SCVI_REAL_PAPER_QA="+json.dumps(rep,ensure_ascii=False));raise RuntimeError("validation fail")
  try:
   qa=build(root/"story.json",root/"assets"/"assets.json",root/"render",render_png=True,layout_engine="freeform")
   rep["render"]={"success":True,"slides":qa["contract_qa"]["cards"],
      "png_count":qa.get("png_count",0),"layout_types":[x["layout_type"] for x in qa["layout_geometry"]],
      "text_collisions":qa["static_visual_qa"]["text_text_collisions"][:10],
      "small_panel_slots":qa["static_visual_qa"]["small_panel_slots"],
      "release_ready":qa["release_ready"],"blockers":qa["release_blockers"],
      "pptx_bytes":(root/"render"/"SharePack_editable.pptx").stat().st_size}
   if (root/"render"/"00_contact_sheet.png").exists():
    from PIL import Image,ImageDraw,ImageFont
    import shutil
    public=Path("qa_preview");public.mkdir(exist_ok=True)
    thumb=Image.open(root/"render"/"00_contact_sheet.png").convert("RGB")
    canvas=Image.new("RGB",(thumb.width,thumb.height+92),(238,244,251))
    canvas.paste(thumb,(0,92))
    d=ImageDraw.Draw(canvas)
    d.text((16,10),"scVI PREPRINT - UNREVIEWED ENGINEERING PREVIEW",fill=(140,30,25),stroke_width=0)
    d.text((16,43),"Original preprint arXiv:1709.02082 | No scientific or font QA approval",fill=(50,62,77))
    canvas.save(public/"scvi_unreviewed_contact_sheet.png")
    rep["render"]["preview_artifact"]="qa_preview/scvi_unreviewed_contact_sheet.png"
  except Exception as e:
   rep["render"]={"success":False,"error":type(e).__name__+": "+str(e)}
  rep["status"]="RENDERED_ENGINEERING_ONLY" if rep["render"]["success"] else "RENDER_FAIL"
  print("SCVI_REAL_PAPER_QA="+json.dumps(rep,ensure_ascii=False))
  if not rep["render"]["success"]:raise RuntimeError("Render failure")
if __name__=="__main__":run()
