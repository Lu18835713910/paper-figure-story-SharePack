#!/usr/bin/env python3
"""Isolated cross-paper QA on a public article. Do not publish cropped panels or claim scientific approval."""
import hashlib
import json
import re
import tempfile
import urllib.request
from pathlib import Path

import fitz

from sharepack.common import save, load, digest
from sharepack.ingest import inspect_pdf, extract_regions
from sharepack.contract import validate_story
from sharepack.planning import plan_audit, panel_selection_audit
from sharepack.render import build

PAPER = {
    "title": "Statistical identification of cell type-specific spatially variable genes in spatial transcriptomics",
    "authors_short": "Shang, Wu & Zhou",
    "doi": "10.1038/s41467-025-56280-4",
    "journal": "Nature Communications 16, 1059 (2025)",
}
LINKS = [
    "https://www.nature.com/articles/s41467-025-56280-4.pdf",
    "https://link.springer.com/content/pdf/10.1038/s41467-025-56280-4.pdf",
    "https://pmc.ncbi.nlm.nih.gov/articles/PMC11770176/pdf/",
]
# Claims paraphrase the article Results and Abstract; complete supplementary checking has NOT been performed.
CARD_SPECS = [
    ("cover", "研究问题", "空间差异基因，不一定来自同一种细胞的内部变化", "为什么普通空间差异分析可能混入细胞类型组成差异？", "区分组织总体空间变化与细胞类型内部变化", "作者提出细胞类型特异空间变化的统计识别问题。", "ct-SVG 应关注特定细胞类型内部的空间变异。", "概念区分不代表已有实验因果验证。"),
    ("framework", "科研框架", "识别细胞类型内部的空间表达模式", "如何兼顾单细胞和多细胞 spot 的观测？", "利用目标细胞类型的指标或比例及空间位置建模", "将细胞类型组成与空间变化共同纳入分析框架。", "同一问题可在不同空间分辨率下形式化。", "不同分辨率的观测及模型前提不能混同。"),
    ("method", "Figure 1 方法", "用空间变系数模型识别 ct-SVG", "方法在统计模型中控制了什么？", "以空间位置和细胞类型比例等作为模型输入", "方法在细胞类型内部估计空间相关的表达成分。", "模型输出统计检验结果，并不是基因功能因果效应。", "需要结合原文方法与补充材料核对具体统计假设。"),
    ("comparison", "Figure 2 模拟", "比较统计效能和假阳性控制", "与已有方法相比有什么证据？", "比较多种模拟空间模式与方法", "研究在梯度、条带和热点模拟中比较检测功效。", "模拟支持方法适用性，但结果依赖生成情境。", "这些数值是特定模拟设置下的结果，不是任意数据集保证。"),
    ("finding", "Figure 3 应用", "肺癌数据中的细胞类型内部空间差异", "算法在真实肿瘤组织中能识别什么？", "在肺癌空间数据中比较 ct-SVG 检出与功能富集", "作者报告不同细胞类型内的空间表达关联。", "真实数据说明统计检出的生物学解释潜力。", "相关性、功能富集与生存关联不能直接解释为因果。"),
    ("finding", "Figure 4–5 应用", "不同组织中的空间模式", "方法是否只能在一种组织中使用？", "分析肾癌与阿尔茨海默病小鼠组织等数据", "作者报告与增殖、免疫或斑块邻域相关的空间模式。", "多种组织场景展示潜在泛化价值。", "不同数据集的样本、分辨率与混杂因素需分开评价。"),
    ("synthesis", "如何理解发现", "从统计结果到科学解释，需要分清证据层次", "统计识别回答了什么，尚未回答什么？", "整合模拟与真实数据结果的证据定位", "检测到 ct-SVG 并不能自动说明其调控机制。", "方法提供后续机制研究的候选线索。", "独立功能验证及外部数据泛化仍需另外研究。"),
    ("limits", "证据与边界", "哪些结果需要谨慎表达？", "如何避免夸大方法优势？", "明确模拟、真实数据和验证层次", "论文讨论了坐标缩放、细胞组成估计和数据场景的限制。", "谨慎区分模型能力、预测表现与实验发现。", "科学审阅尚未完成，此次卡片仅用于软件压力测试。"),
]

def download_pdf(dest: Path):
    attempts = []
    for url in LINKS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SharePack QA (research)"})
            with urllib.request.urlopen(req, timeout=50) as res:
                data = res.read(30000000)
            if not data.startswith(b"%PDF-"):
                raise ValueError("response is not a PDF")
            dest.write_bytes(data)
            return {"url": url, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "attempts": attempts}
        except Exception as e:
            attempts.append({"url": url, "error": str(e)[:160]})
    return {"error": "SOURCE_PDF_UNAVAILABLE", "attempts": attempts}

def run():
    with tempfile.TemporaryDirectory(prefix="sharepack_celina_QA_") as t:
        root = Path(t)
        pdf = root / "celina_original.pdf"
        dl = download_pdf(pdf)
        report = {"study": "Celina (Shang, Wu & Zhou, 2025)",
                  "source_doi": PAPER["doi"], "license": "CC BY-NC-ND 4.0",
                  "purpose": "internal engineering evaluation only, no public figure redistribution",
                  "mode": "standalone", "pfs_used": False, "download": dl}
        if not pdf.is_file():
            print("SHAREPACK_CROSS_PAPER_REPORT=" + json.dumps(report, ensure_ascii=False))
            raise RuntimeError("Cannot download the authentic PDF for the QA run")

        doc = fitz.open(pdf)
        report["pdf_pages"] = len(doc)
        idx = inspect_pdf(pdf, root / "index")
        report["prepare"] = {
            "pages": idx["pages"],
            "candidate_figures": len(idx["figures"]),
            "figure_labels": [x["figure_label"] for x in idx["figures"]],
            "caption_pages": [x["page"] for x in idx["figures"]],
            "candidate_statuses": list(sorted(set(x["status"] for x in idx["figures"]))),
        }

        # Use exact coordinate rectangles around *unreviewed* Figure candidates for engineering only.
        # They may contain unrelated page text and never become VISUAL_REVIEWED automatically.
        seen = set()
        regions = []
        for x in idx["figures"]:
            label = x["figure_label"]
            if label in seen or len(regions) >= 5:
                continue
            seen.add(label)
            page = doc[x["page"] - 1]
            bbox = fitz.Rect(*x["candidate_rect_pdf_pt"])
            bbox &= page.rect
            if bbox.height < 70 or bbox.width < 100:
                continue
            aid = "candidate_fig_" + re.search(r"\d+", label).group(0)
            regions.append({"id": aid, "figure": label, "pdf_page": x["page"],
                            "crop_pdf_pt": list(bbox), "review_status": "PENDING",
                            "license_note": "For internal QA only; CC BY-NC-ND article, no public derivative distribution"})
        report["candidate_region_count"] = len(regions)
        if not regions:
            report["status"] = "INDEX_ONLY_NO_CANDIDATE_REGIONS"
            print("SHAREPACK_CROSS_PAPER_REPORT=" + json.dumps(report, ensure_ascii=False))
            return
        manifest = {"source_pdf_sha256": digest(pdf), "regions": regions}
        save(root / "regions.json", manifest)
        assets = extract_regions(pdf, root / "regions.json", root / "assets")
        report["extract"] = {"asset_count": len(assets["assets"]), "asset_pages": [x["pdf_page"] for x in assets["assets"]]}
        ids = [x["id"] for x in assets["assets"]]
        page_for_asset = {x["id"]: x["pdf_page"] for x in assets["assets"]}

        claims, cards, sources = [], [], []
        for n, (role, stage, title, question, method, observation, takeaway, limit) in enumerate(CARD_SPECS, 1):
            cid = f"C{n:02d}"
            # Source pages are genuine PDF page numbers; interpretation is still PENDING scientific review.
            spage = page_for_asset.get(ids[min(max(0, n-3), len(ids)-1)], 2)
            sid = f"S{n:02d}"
            sources.append({"id": sid, "pdf_page": spage})
            claim = {"id": cid, "question": question, "method": method,
                     "observation": observation, "meaning": takeaway,
                     "limit": limit, "source_ids": [sid],
                     "required": True, "review_status": "PARTIAL"}
            if n == 4:
                claim["metrics"] = [{"label": "单细胞模拟平均功效", "value": "96% / 61% / 53%",
                    "definition": "梯度、条带、热点三类模式",
                    "comparison": "四种场景，FDR阈值0.05；原文报告"}]
            claims.append(claim)
            figs = []
            if n == 3 and len(ids) >= 1: figs = [ids[0]]
            if n == 4 and len(ids) >= 3: figs = ids[1:3]
            if n == 5 and len(ids) >= 3: figs = [ids[2]]
            if n == 6 and len(ids) >= 4: figs = [ids[3]]
            cards.append({"order": n, "stage": stage, "title": title,
                 "intro": "论文示例的结构性讲解，仅用于跨论文工程压力测试。",
                 "question": question, "method": method, "observation": observation,
                 "takeaway": takeaway, "interpretation": takeaway,
                 "narrative_role": role,
                 "layout_type": "framework" if role == "framework" else "cover" if role == "cover" else "synthesis" if role in ("synthesis","limits") else "evidence",
                 "claim_ids": [cid], "figure_asset_ids": figs,
                 "flow_steps": ["研究问题", "建模与模拟", "真实数据", "结论与局限"]})
        story = {"contract": "sharepack-story-v1", "paper": PAPER,
                "pdf_sha256": digest(pdf), "profile": "standard",
                "sources": sources, "claims": claims, "cards": cards,
                "required_figure_labels": [],
                "review_status": "PARTIAL", "formal_ready": False}
        save(root / "story.json", story)
        validation = validate_story(story, assets, root / "assets", strict=False)
        report["validate"] = {"valid": validation["valid"],
            "formal_ready": validation["formal_ready"],
            "errors": validation["errors"], "warnings": validation["warnings"]}
        report["audit_plan"] = {
            "status": plan_audit(story, assets)["status"],
            "figure_selections_pending": len(panel_selection_audit(story, assets)["pending"]),
        }
        try:
            qa = build(root / "story.json", root / "assets" / "assets.json",
                       root / "render", render_png=False, layout_engine="freeform")
            report["render"] = {"success": True, "slides": qa["contract_qa"]["cards"],
                "pptx_size": (root / "render" / "SharePack_editable.pptx").stat().st_size,
                "layouts": [x["layout_type"] for x in qa["layout_geometry"]],
                "mobile_size_flags": qa["static_visual_qa"]["small_panel_slots"],
                "text_text_collisions": qa["static_visual_qa"]["text_text_collisions"][:20],
                "text_collision_count": len(qa["static_visual_qa"]["text_text_collisions"]),
                "canvas_overflow_count": len(qa["static_visual_qa"]["canvas_overflow"]),
                "release_ready": qa["release_ready"], "release_blockers": qa["release_blockers"]}
        except Exception as e:
            report["render"] = {"success": False, "error": type(e).__name__ + ":" + str(e)}
        print("SHAREPACK_CROSS_PAPER_REPORT=" + json.dumps(report, ensure_ascii=False))
        if not validation["valid"] or not report["render"]["success"]:
            raise RuntimeError("Second-paper render not fully successful; see diagnostic report")

if __name__ == "__main__":
    run()
