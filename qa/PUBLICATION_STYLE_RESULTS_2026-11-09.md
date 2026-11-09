# SharePack｜按上传论文出版来源自动选择视觉风格：实测审查（2026-11-09）

## 0. 测试裁决

**工程：PARTIAL PASS；样式路由：PASS；PDF自动识别：PARTIAL；科研图片完整性：NOT REVIEWED；手机可读性：FAIL / NOT APPROVED；正式Beta：NO-GO。**

本轮不是 AI 生成的概念图。已实际使用两篇不同来源的公开 PDF，调用仓库 `sharepack` 真实代码、`python-pptx` 和 LibreOffice，生成可编辑 PPTX、PDF 与 1080×1440 PNG。科学讲解文本是明确标记为 `PARTIAL` 的工程测试输入，**不能冒充经过科研审阅的文章解读**。

## 1. 版本及隔离边界

- 受保护基线：`main=0caea5796ce7d9f958eb70e8fddaa5742cd206c7`，历史 `v0.1.0-rc.1` 不变。
- 测试分支：`qa/publication-style-20261109`，只在该分支增补期刊/预印本主题、探针与结构/字体 QA。
- 未修改 PFS 主仓库、现有十卡演示、Release 及 `main`。
- 不嵌入期刊的 Logo，不假称官方合作；视觉配色与编辑层级仅为**原创的期刊风格化解读**，不是期刊封面的一比一复制。
- 测试运行环境：GitHub Actions Ubuntu、Python 3.11、LibreOffice；真实 PowerPoint/Windows 字体验收尚未执行。

## 2. 测试样本与观察结果

### A. scVI：arXiv 预印本

- 原文：Lopez et al., *A deep generative model for gene expression profiles from single-cell RNA sequencing*, arXiv:1709.02082，来源 `https://arxiv.org/pdf/1709.02082`。
- 源 PDF：6 页，SHA-256 `edfaece53e86fe4dde79528020d642de3b86f389dcd9a665f471f991c1ace3eb`。
- 识别到 **2 张候选 Figure**（第 2、4 页），真实裁图暂为 `PENDING`，未获实验面板审核。
- 生成 **8 页 PPTX、PDF、8 张 PNG**，静态几何碰撞 0，但不代表正式版式可读性合格。
- **实际选择 `preprint-arxiv`，PASS**：优先使用上传的预印本身份，没有因为该研究后来发表期刊文章而把旧 PDF 伪装成期刊版本。
- **自动识别不完整**：`inspect_pdf` 仅检查首 3000 字符，在本 PDF 返回 `publication_hint.source_type=unknown`。这次正确选择 arXiv 是因为测试 story 里明确提供了 arXiv 来源字段，不能宣称“PDF 无元数据也能完全自动识别”。

### B. PLOS Computational Biology：正式期刊论文

- 原文：Posfai et al., *Gauge fixing for sequence-function relationships*, PLOS Computational Biology, 2025, DOI `10.1371/journal.pcbi.1012818`。
- 官方打印版 PDF：`https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1012818&type=printable`。
- 源 PDF：24 页，SHA-256 `53cf1a75f3173c39640dd1f1963f0d708114a71377fc62cd0bedc792ca402fc1`。
- 检测到 **5 个 Figure 候选**：Figure 1/2/3/4/5，位于 PDF 第 5/6/13/15/18 页；这是图注候选，不保证准确裁切。
- **自动提取首屏期刊身份为 PLOS Computational Biology**（`PDF_HEADER_CANDIDATE`，仍需审核）；生成 **8 页 PPTX、PDF、8 张 PNG**。
- **实际选择 `journal-plos-computational-biology`，PASS**；源码中深色学术编辑样式与 Arial/SimHei 字体声明均在渲染产物中生效。
- 第一 URL `type=manuscript` 返回 XML，备用 `type=printable` 成功：说明来源下载必须校验文件头/类型，而非仅看 HTTP 200。

[真实 GHA 端到端日志](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42567649971)；
[PLOS 的未审阅八卡图片](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42567649971/artifacts/13651798497)。
该截图只用于展示软件当前行为，**不是成果宣传图或可复用的科研解读**。

## 3. 实际视觉审查（不能只看脚本通过）

查看真实 PLOS PNG 总览后，**可读性未通过**。尽管双色深底与清晰的黑体替代了原先纯白背景，仍有以下缺陷：

1. **阅读字号不足**：目前 freeform 中大量正文字体约 8–11 pt。页面为 7.5 英寸宽，缩至 400px 宽时约等于 6–8px，达不到手机阅读要求。
2. **风格映射只改变了调色板、英文字体和眉题**，没有真正实现期刊风格的内容层级、图片占比和版式变化。不能把此结果宣传成已经达到对应期刊编辑水平。
3. **八页仍高度重复**：大量页面复用四步流程框，且正文/结论没有足够大的对比/数字/证据展示区域；测试输入 story 的重复也会放大这一问题，应在相同科学内容基础上分开测 renderer 和 planner。
4. **真正的 Figure 被缩小**：首轮自动区域从页顶到图注，存在把正文等非 Figure 内容一起裁入的结构性风险；必须先做精准原图区域/面板审核。
5. **Table 与补充材料未完全覆盖**：只检测 Figure 候选会漏掉方法论文中以表格表达的关键指标。

最新版候选另增加 400px 移动端字号的静态预警门槛：低于约 12px 的文字在报告 `static_visual_qa.mobile_type_warnings` 登记，且 `release_blockers` 添加 `MOBILE_TEXT_TOO_SMALL`。这属于问题检测，不代表已修复字号。

## 4. 当前机制边界

1. `prepare` 对 PDF 首屏尝试产生 `publication_hint`，状态为候选，不能仅凭关键词做不可逆的出版身份判定。
2. `render --pdf-index path/to/pdf_index.json` 绑定真实源 PDF SHA，不匹配则拒绝 `PUBLICATION_INDEX_PDF_HASH_MISMATCH`。
3. style 选择有显式来源类型/DOI/期刊名、已映射期刊和未知期刊/预印本安全回退。
4. 目前专门主题仅覆盖 **arXiv、PLOS Computational Biology、Nature Communications、Cell Systems**，其他期刊用克制的通用期刊主题。**尚不是对任意期刊的自动视觉抽取**。
5. 为防止跨运行污染，渲染时采用 `ContextVar` 作用域管理当前主题；`qa_report.json` 与 `publication_style.json` 会记录所选样式及其依据。
6. 某个期刊首屏检测正确，不保证所有 PDF 变种都能正确检测；未识别的预印本应该保留回退/人工校正路径。

## 5. 下一轮优先次序

**P0｜科研证据质量**
- PDF Figure/Table 内容清点（而非只查 Figure 标题）；原图精确裁图和面板审核。
- 所有图表的来源、页面、适用结论和许可证完整可追溯。
- 拒绝把仅候选 PDF 裁图当作正式科研卡片的已核验素材。

**P0｜手机端可读性**
- 设计以 400px 手机宽度仍可读为准的字体与图表占比约束；正文建议目标至少 12–14px，实际页面需检查图例、注释、坐标轴。
- 优先少图大图、减少卡片内容，允许短文章用 5–7 张卡；不机械凑十张。
- 在 PDF/PNG 的真实渲染结果上做视觉审核，而不只是识别 PPTX shape 是否相交。

**P1｜真正的期刊式版面规划**
- 从期刊提取的是页面语言：文字密度、图文比例、引用方式和内容层级；不是简单用一层深色背景。
- 增加不同 role 的编辑版式：封面要点、方法导读、核心数据图、数字比较、局限性，不复用同一流程图。
- 整个过程保留 SharePack 自身品牌和原论文署名，不使用第三方期刊官方标志/封面图构造假冒官方作品。

**P1｜更可靠的来源识别**
- DOI、PDF 元数据、首页信息按一致性判定；相互冲突标为 `NEEDS_REVIEW`，不盲选。
- arXiv PDF 元数据未知时，提供明确的用户纠正机制。
- 保留上传 PDF 的版本身份；别把预印本变成正式期刊版。

## 6. 最终裁决

**不集成 main，不发布 Beta，不替换现有 GitHub 首页作品展示。**

本阶段已证明“**上传论文信息→主题自动路由→真实可编辑 PPTX 与 PNG 输出**”的工程链路可以工作，也证明原始一套模板不能单靠颜色变换达到用户希望的期刊视觉质量。下一步应在**相同论文和证据**下做“默认版与新的期刊编辑版”的 A/B 视觉对照，再考虑受控集成。

## 7. Journal editorial V2 — actual Figure source and source-grounded story

**Baseline:** isolated `qa/publication-style-20261109` branch; no merge to `main`; no Release tag changes.

**Real article:** Posfai, Zhou, McCandlish & Kinney (2025), *Gauge fixing for sequence-function relationships*, PLOS Computational Biology, DOI [10.1371/journal.pcbi.1012818](https://doi.org/10.1371/journal.pcbi.1012818), CC BY 4.0.

**Changes under real workflow:**
- Introduced opt-in `--layout-engine editorial` with distinct cover, framework, methods, evidence, finding, synthesis and limitations pages. Existing `freeform` and `legacy` remain available. This is not a new journal-authorized template.
- Original publisher Figure 1 obtained from [PLOS full-resolution original PNG](https://journals.plos.org/ploscompbiol/article/figure/image?size=large&id=10.1371/journal.pcbi.1012818.g001), unmodified, **2190×1028** pixels, SHA-256 `e05e7ba6a51b72d9992ee60243ffc89ddd8c68b085fce9d571ce4f4bc858ac10`. The Figure asset remains `PENDING` independent scientific/panel QA.
- The Figure 1 card now gives the image **6.161 inches of 6.5-inch content width (~94.8%)**. The old figure crop included neighboring article paragraphs and provided a much smaller apparent science image.
- The Figure card shows the scientific question, method, original Figure, explicit observation and interpretation, source citation and evidence boundary. Combining observation/takeaway on one legible row preserves both strings, rather than deleting scientific content to make space.
- Created an eight-card PLOS case based on paper abstract, author summary and Figure 1 caption; it is a **research-grounded, unreviewed engineering demonstration**, not a completely vetted article story.
- Exported **8-slide editable PPTX, 8-page PDF and eight 1080×1440 PNGs** plus provenance/QA JSON in a temporary GitHub Actions artifact. Published scientific review status remains `PARTIAL`.
- First raster inspection revealed Figure attribution text on a white image-board used too-light text; corrected it to dark and re-exported.
- **Static geometry:** 0 text-box collisions, 0 registered small-panel slots. **Visual review still PARTIAL**: mobile Figure internal axes and legends still may be too small, no real Microsoft PowerPoint Windows inspection, and table/supplement coverage remains incomplete.
- **Typography QA:** 68 below-12px warnings at 400px card width in latest `qa_report.json`; mostly masthead, page counter, source/independence footers, with four 16.0pt framework step numerals. Main story copy uses larger type. This is not a blanket mobile PASS.

### Reproduction links

- [Real-paper and editable-output GitHub Actions run 42576005586](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42576005586).
- [Complete eight-card QA ZIP (PPTX, PDF, PNG, provenance; **UNREVIEWED**)](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42576005586/artifacts/13654968226).
- [Source-grounded preview](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42576005586/artifacts/13655526080).

### Final decision

**EDITORIAL ENGINEERING PASS / CONTENT AND MOBILE VISUAL REVIEW PARTIAL / NO BETA INTEGRATION APPROVAL.**

Prioritize the next improvement on original Figure panel-level legibility and reviewed Table/Supplement evidence selection. Do not keep introducing decorative themes or fabricate publisher logos. Authorized unmodified publisher logos are supported only via documented rights and exact SHA/DOI/source checks; none was embedded into these PLOS cards.
