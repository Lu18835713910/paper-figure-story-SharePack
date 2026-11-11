# SharePack｜Agent 自适应排版实验（2026-11-11）

## 决策

**建议固定“期刊视觉识别 + 科研证据约束 + 字体/碰撞下限”，允许 Agent 为每张卡选择内容组织与页面变体。** 不应把所有论文强行塞入一套固定版式，也不应放开成 Agent 直接修改 PPT 任意坐标和字号。

本轮引入 opt-in `flex` 引擎，仅在隔离分支 `qa/publication-style-20261109`；`main`、Release 和 PFS 未改。

## 已实现的范围（不能夸大为完全自主排版）

- `sharepack/flex_layout.py` 支持 **5 种受控页面类型**：essay、classic、framework、figure_first、figure_explain。对每张卡按照科学角色与有无 Figure 产生候选列表。
- Agent 提交 **可选的每卡 `preferred` 与理由**；没有 Agent 文件时，也可以按内容角色自动选取变体。Agent **不能直接编造内容、修改 Figure、指定任意坐标/字号、跳过来源核验**。
- Agent 布局文件必须同时绑定故事 JSON 与 Figure 资产 JSON 的 SHA-256；不匹配或重复卡号、非法模式直接拒绝。
- 每张卡先在临时幻灯片上试排，计算正文容量、图片容纳尺寸及文字框碰撞；若失败，记录原因并尝试其他允许变体；全部不合格则显式返回 `AGENT_LAYOUT_REPLAN_REQUIRED_CARD_N`，**不会自动降字号或偷偷删结论**。
- 导出可编辑 PPTX、PDF 和 PNG；另存 `adaptive_composition_plan.json`，可追溯每页选择、失败备选、Figure、来源与科学审核状态。
- 官网风格从当前上传的 PLOS 网站截图与 PDF 继承：白色文章底、浅灰页眉、蓝色强调，**不使用与期刊无关的深绿色**。真实 Logo 未获得可公开分发的独立授权前，正式产出不会冒充官方素材；已有截图 Logo 仅限本地 QA 样稿。
- 2026-11-11 本轮原始 PLOS 图像：原论文 Figure 1 从官方完整图片资源取得，仍标记独立科学审核 PENDING。

## CLI

```bash
sharepack render --story work/story.json --assets work/assets/assets.json \
  --pdf-index work/index/pdf_index.json \
  --layout-engine flex --agent-layout-plan work/agent_layout.json \
  --outdir work/flex-output
```

Agent 配置示例（须替换为对应文件的实际 SHA-256）：

```json
{
  "contract": "sharepack-agent-layout-plan-v1",
  "story_sha256": "<SHA256_OF_STORY_FILE>",
  "assets_sha256": "<SHA256_OF_ASSETS_FILE>",
  "cards": [
    {"card": 1, "preferred": "essay", "rationale": "文章的核心问题作为阅读锚点"},
    {"card": 4, "preferred": "figure_explain", "rationale": "Figure 1 是三面板横向图，需要大图和简洁解读"}
  ]
}
```

## 真实论文结果及安全边界

- PLOS 论文：Posfai et al., 2025, DOI `10.1371/journal.pcbi.1012818`；源 PDF 24 页，Figure 1 完整图 2190×1028。
- 旧版与新 `flex` 使用同一研究故事，八卡内容、来源和图像相同。实际 `flex` 选择了四类页面（classic / framework / essay / figure_explain）；Figure 页的首选 `figure_first` 因 `AGENT_FIGURE_FIRST_REPLAN_SPACE` 被拒绝，使用了 `figure_explain`，避免图片与科学说明互相挤占。
- 形状层面：**0 个文本框交叉、0 个登记的极小图片槽**；但这不代表实际字体替换、图表内部标注和手机端可读性已经全部通过。
- 旧样例的 400px 手机端仍有小字号警告。本轮继续把页眉、DOI 来源、非官方说明文字等升级到接近正文的可读字号，并重跑检查。
- 四个 Python 版本（3.10–3.13）回归测试包含 SHA 错配、非法布局、文本碰撞、候选回退；真实性能仍需在多篇不同图结构论文和 Microsoft PowerPoint 中继续测试。

### 阶段裁决

**FLEX 版式工程候选：可以继续受控测试；正式对外发布：NO-GO。**

与用户期望的真正自主布局仍有差距：目前只支持 5 种受控变体，尚不能任意决定跨卡拆分、动态页数、任意横纵组合与 panel 放大。下一阶段逐步引入 **页面内容拆分/合并提议 → 新规划试排 → 真实字体与像素级碰撞核验 → 多端导出 → 明确审核标记**。