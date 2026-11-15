---
name: paper-figure-story-sharepack
description: 从科研论文或经验证的 PFS 科研逻辑、A/B 图与 Figure 证据制作可编辑中文竖版科研故事卡片。支持 Standalone 和 PFS-assisted，由 Agent 负责科研编辑与视觉设计并保留来源。
---

# SharePack v1.0.0 编辑工作流

- 只有论文 PDF、目标是科研小卡片时，使用 SharePack Standalone。
- 已有 PFS v1.2.0 科研逻辑和 Figure 时，使用 SharePack PFS-assisted。核对 M1 Schema 1.1 和 Research Logic 合同 pfs-research-logic-1。
- 若目标是科研逻辑重构、A/B 图或详细论文汇报，选择 Paper Figure Story。恢复任务前先核对实际加载的 Skill 路径、实际 Python 导入路径和输入 SHA。

1. 阅读原文、方法与图注。每个证据页建立主张、样本、方法、对照、观察、解读、限制、页码和 panel 的映射。区分作者所报告的发现、Agent 的解释和仍需独立核验的结论。
2. 为封面单独给出两个构图。一个问题只能有一个主视觉；主标题提出科学吸引点，副标题交代贡献或权衡。原创示意应标明非实验数据。默认用纯文字期刊名称、DOI 和独立解读署名。使用 Logo 时登记机构、年代、版本、文件身份和使用许可。
3. 为每页定一个任务，如提出问题、解释方法、读图、比较、转折、限定或总结。内部审查字段留在 story；画面只显示本页需要的信息。用图旁的语言指出比较对象和观察位置。数字先交代单位、分母与实验条件。正文以 16–19 pt 起步，并在 400px 实际审读。
4. 为要显示的每一幅裁图建立独立 R19 计划项。原 PDF、图页、图注页、Figure、矩形、panel 和原因都应可追溯。先运行 extract-reviewed-figures 和 verify-reviewed-figures。核对边缘字母、比例尺、坐标和图例；不要改变源颜色与几何关系。
5. 渲染可用既有 freeform，也可由 Agent 提供 editorial 布局。启用方式为 render --layout-engine editorial。每张 card 的 editorial.intent 和 editorial.elements 表达布局。元素支持 text、rect、ellipse、figure，box 使用英寸 [x,y,w,h]，画布为 7.5×10。图像按源宽高比适配，并且必须与 card.figure_asset_ids 精确一致。禁止从未登记路径直接嵌图。文本和几何图形生成 PowerPoint 原生对象。
6. 每轮以原生宿主导出，按 400px 宽检查整套。记录读不出的字、错位的对照、图注与图像的空间关系。修订后再次核验来源并导出。机器结构 PASS 只用于定位问题。历史对照看相同图或相同叙事任务；按页序的拼图同时保留供浏览。
7. 交付时把科学、叙事、视觉、来源、可编辑性、宿主、许可分别裁决。Agent 编排、内容编辑与视觉评议属于人工设计环节。无独立审核的内容保持正式审核待定。

## 期刊品牌工作流

每次为实际发表论文设计 SharePack 封面、首次生成内页或变更期刊品牌时，自动执行本段。先读 [品牌附加规范](references/SKILL_BRANDING_ADDENDUM.md)。本段按论文和期刊身份启动，适用于 Nature、Cell、Science、PLOS 各子刊及其他期刊。

1. 从 DOI、论文首页与期刊官网对照出版年份、正式刊名、ISSN 及出版社，避免混淆子刊、学会和集团品牌。冻结故事、Figure 计划及原生 PPTX。
2. 查经核验的缓存。按期刊身份、资产 SHA-256、年代、使用范围索引。复核权利状态及历史资料；已覆盖本次范围即可复用。发现更适合的新版本时，追加候选记录，保留原版本和更换理由。
3. 缓存未覆盖时，从多类来源发现候选。默认包含 https://logos-download.com/，同时查 Wikimedia Commons、期刊官网、出版社品牌页面及历史官方材料，可扩展到其他素材网站。记录每个渠道有无结果；单一来源不能独立确立历史身份或使用授权。优先对照实际发表文章和出版社档案，再从候选中选择适用年代与视觉版本。
4. 逐候选登记候选页面与直接素材网址、文件格式、历史/当前/未知版本、时间证据、来源可信度、实际资产 SHA-256、用途及权利限制。无法取得字节时填空并记录原因。用视觉样张比对字形、图案、色彩和使用年代，由 Agent 选择。素材哈希用于校验字节，网站下载或公版标签不自动授权商标使用。
5. 权利不明时，默认保持普通文本刊名、DOI 和独立解读署名。只有用户明确指定的私人评审才可使用已核实的权利待确认标识，并记录仅供私人评审；公开分发需独立检查使用依据。
6. 仅在已安装 SharePack Python wheel（或已验证的源码包）且 `sharepack-brand` 命令可用时，对已冻结的实际文件运行 `sharepack-brand inspect`、`draft`、`apply`、`verify`。独立安装 Skill ZIP 不等于安装 Python CLI；如果尚无该命令，提示先独立安装 SharePack Python 包，不得调用不存在的 `scripts/brand_tool.py`。按 400px 草图逐页选位置、尺寸与底板，分别校验未被调整和调整后对象的碰撞。验证 PPTX 字节身份、原科研图嵌入 SHA 和原文字。用原生宿主导出，再比对 400px；正文区变化必须调查。先排除影响后才登记该版为适配完成。工具执行保持为显式步骤，品牌工作流的自动启动由 Skill 指令触发。
## PFS Research Logic 与 Figure 融合

先在 PFS 确认同一论文的 M1、Scientific Index、Evidence Network、Research Logic 和 Figure 登记。复用 `bridge-pfs`、`import-pfs-assets` 取得本次真实来源。核对原文和图注后，由 Agent 按 A 核心、B 支线、汇合及边界编排，并保持完整 B 独立。

在 story 中添加 `research_logic`（`path`、`sha256`、`snapshot`）和现有 `pfs_bridge`。逐页 `logic_sources` 登记 `nodes`、`relations`、`rsus`，A 导览设 `scope: A`，支线设真实 `branch` ID。使用 `logic_node` 和 `logic_edge` 生成原生形状与连接线，分别用 `node_id` 和 `relation_id` 引用已登记身份。Agent 提供节点坐标和经科学核对的可选短显示文字。按实际证据选择 `figure` 元素，可用归一化 `crop: [left, top, right, bottom]` 放大且保留图片字节与来源。复核图窗的比例尺和标签。局限与作者模型在正文标明。

运行 `python -m sharepack render --layout-engine editorial --story STORY --assets ASSETS --outdir NEW_DIR --no-pdf`。关系身份与 SHA 在备注和 `card_source_map.json` 查看。现场 PowerPoint PDF 导出及 400px 科学可读性检查仍单独执行。

## 安装边界

Standalone 不需要 PFS。SharePack 安装、升级、卸载和回滚只处理 SharePack。若用户请求 PFS-assisted，先向宿主核对实际加载的 PFS 路径、版本及安装回执中的修订；仅凭 VERSION 无法推断 Git 修订。不兼容、缺少 PFS 或缺少所需成果时，提示从 https://github.com/Lu18835713910/paper-figure-story 独立安装或更新。不得调用 PFS 安装器或替换 PFS。成果通过现有只读文件合同交接。
