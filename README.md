<div align="center">

# SharePack

**从科研证据到可讲述的图文故事**

*From scientific evidence to editable, source-linked research story cards.*

<img src="docs/images/sharepack-cover.svg" alt="SharePack 原创科研传播工作流示意：问题、证据、认识三张竖版卡片，非真实实验数据" width="100%">

**v1.0.0 正式版** · **Standalone / PFS-assisted** · **可编辑竖版 PowerPoint** · **来源可追溯**

[正式版下载](https://github.com/Lu18835713910/paper-figure-story-SharePack/releases/tag/v1.0.0) · [安装与运行](#安装与快速开始) · [两种工作模式](#两种工作模式) · [科研来源与限制](#科研来源与使用边界)

</div>

---

## SharePack 做什么？

一篇研究论文通常包含多个研究问题、实验分支和证据图。SharePack 帮助 **Agent 在完成文献阅读、科研判断与来源审阅后**，把这些内容编排为适合交流和阅读的中文竖版科研故事卡片。

它不是「上传 PDF 后自动得出经过证实的结论」的工具，也不以一段通用摘要代替科研故事。

| 科研叙事 | 证据绑定 | 可编辑输出 |
| :--- | :--- | :--- |
| 按问题、方法、观察、进一步探索和综合认识组织卡片；允许并行分支与汇合 | 将关键 Figure / panel 绑定原论文 PDF、页码、裁图区域与文件身份 | 输出竖版 PPTX，文字与逻辑图形可编辑，原始 Figure 可独立替换 |

## 两种工作模式

| | **Standalone** | **PFS-assisted** |
| :--- | :--- | :--- |
| **从哪里开始** | 论文 PDF 与 Agent 审阅形成的科研故事及 Figure 计划 | 已验证的 [Paper Figure Story (PFS)](https://github.com/Lu18835713910/paper-figure-story) 科研模型、A/B逻辑图和 Figure 证据 |
| **科研叙事由谁负责** | Agent 阅读正文、方法、图注，明确研究问题、实际观察与解释边界 | 复用PFS的既有科学逻辑、节点、关系、研究分支与证据身份；Agent再做面向读者的科学编辑 |
| **重点产物** | 可编辑的科研传播卡片与来源映射 | 基于PFS逻辑A导览、B关键分支和Figure的完整故事，保留完整B独立画布 |
| **是否必须安装 PFS** | **不需要** | 需要已有有效、同源的 PFS 成果；SharePack不会凭空生成未经审核的A/B模型 |

### 从论文到卡片的流程

```text
Standalone                                PFS-assisted
论文 PDF + 可用补件                      PFS v1.2.0 已核验成果
      │                                     │
Agent 科研阅读与证据编辑                 M1 + Research Logic + A/B + Figure
      └─────────────────┬───────────────────┘
                        ▼
                科研故事与Figure计划
                        │
              来源绑定 / 关系身份核对
                        ▼
                Agent逐页编辑与排版
                        ▼
          可编辑PPTX + 来源台账 + QA记录
                        │
                PowerPoint实际导出
                        ▼
             PDF + 400px逐页可读性审查
```

PFS-assisted 已在**一篇真实论文案例**中完成同源模型、逻辑与 Figure 融合的实际验证；不应将此理解为所有论文均已完成自动化科学审核。PFS 软件兼容基线为 **v1.2.0**；M1 Schema 为 **1.1**，Research Logic 合同为 **`pfs-research-logic-1`**。这三个编号并非同一个版本号。

## 安装与快速开始

### 方式一：通过正式 Release 安装

前往 **[SharePack v1.0.0 Release](https://github.com/Lu18835713910/paper-figure-story-SharePack/releases/tag/v1.0.0)**，获取已发布的 wheel、Skill ZIP、源码包（sdist）和原创演示包。

在 Python 3.10+ 环境中安装下载的 wheel（命令在该文件所在目录运行）：

```bash
python -m pip install paper_figure_story_sharepack-1.0.0-py3-none-any.whl
python -m pip check
python -m sharepack --help
```

安装 Skill 时，先确认当前 Agent 的**实际 Skill 发现目录**，再将 Skill ZIP 安装到正确位置；Codex 与 WorkBuddy 使用的用户级目录不同。旧版本应先备份，安装后在**新会话**确认真正加载的 Skill 与 Python 模块路径，而非仅查看 `pip show`。

### 方式二：运行仓库中的原创虚构数据示例

```bash
git clone https://github.com/Lu18835713910/paper-figure-story-SharePack.git
cd paper-figure-story-SharePack
python -m pip install -e .

python scripts/render_reviewed.py \
  --pdf examples/original_demo/sample.pdf \
  --story examples/original_demo/story.json \
  --plan examples/original_demo/plan.json \
  --output out_original_demo
```

> 示例仅展示软件行为与可编辑输出，使用**虚构数据**，不构成真实实验发现或论文科学结论。README 示例 PDF 已在发布后补入 `main`；如需复现固定的 `v1.0.0` 发行资产，请使用正式 Release 的源码包或原创演示包，而非假设 Tag 源码树与后续 main 完全一致。

### 告诉 Agent 怎么做

**Standalone**

> 使用 SharePack v1.0.0 Standalone 模式阅读我提供的论文和补充资料，先核查研究问题、实验对照、原始 Figure 及结论边界，再组织中文竖版科研故事卡片。保留原始Figure来源，交付可编辑PPTX、来源台账和视觉检查结果。

**PFS-assisted**

> 我已有 PFS v1.2.0 的科研逻辑及 Figure 结果。请使用 SharePack PFS-assisted，沿用同源 M1、Research Logic、A/B 分支、关系ID及Figure证据构建科研故事卡片。保留完整B独立文件，生成竖版可编辑PPTX，并核对来源和关键图例可读性。

开发者可查看 [SKILL.md](SKILL.md) 中的审查、`editorial` 布局、`bridge-pfs`、`import-pfs-assets` 及来源绑定流程。

## 核心特性

- **逻辑驱动而非机械逐图排序**：研究问题、独立验证、证据互补与结论限制决定叙事顺序；不把并行关系冒充因果。
- **真实 Figure 来源记录**：审阅裁图位置、图注和panel后登记来源PDF及字节身份；源头变化和错误绑定不会静默放行。
- **原生 PowerPoint 对象**：正文、框、连线可编辑；原论文图像保持可替换，不重绘实验数据。
- **Agent 主导的科研传播设计**：逐页决定封面、图文比例、局部放大和读者阅读路径，而不是强制固定模板。
- **期刊品牌核验**：可核对正式刊名与品牌素材，但未确认使用权限时使用文字刊名，不默认嵌入期刊Logo。

## 科研来源与使用边界

**科学判断 ≠ 软件校验。** PDF哈希、Figure区域、关系ID、结构测试、PowerPoint导出和QA都不能代替独立领域专家对结论的审查。生成物须根据实际来源检查实验组别、统计口径、图例及作者假说。

本版采用 PDFium / pypdf 处理相关 PDF 工作流：

- `prepare` 生成文本和图注候选索引，**不**自动生成未经审核的裁图预览。
- 经过审阅的区域可用于Figure提取；直接XObject支持范围有限，嵌套对象及显示矩形不属于本版承诺能力。
- 不支持非默认 `UserUnit` 的PDF页面；跨引擎编码改变可能要求重新审批历史图像字节。
- 复杂论文的某些原始图内文字需要查看完整尺寸；400px预览需要人工检查。
- 本版PFS-assisted真实案例的覆盖范围为**一篇论文**；WorkBuddy新会话路由尚未完成独立验证。

详见 [已知限制](docs/KNOWN_LIMITATIONS.md)、[测试说明](TESTING.md)、[兼容性说明](COMPATIBILITY.md) 和 [正式Release说明](RELEASE_NOTES.md)。

## 版本、授权与引用

**当前正式版：[v1.0.0](https://github.com/Lu18835713910/paper-figure-story-SharePack/releases/tag/v1.0.0)**。维护分支或后续main文档修订不会自动更改已冻结的 v1.0.0 Tag、wheel 或 Skill ZIP。需复现时优先固定 Release 附件及其SHA。

**许可证：个人非商业使用，源码可查看（不是OSI开源许可证）。** 个人学习、科研和私人修改范围见 [LICENSE](LICENSE)；商业使用、共享机构部署以及软件再分发需要另外授权。第三方论文、Figure、数据、期刊Logo与PFS软件不因SharePack许可证自动获得授权。详见 [LICENSE_STATUS.md](LICENSE_STATUS.md)、[第三方素材说明](NOTICE_THIRD_PARTY.md) 和 [PDF依赖声明](NOTICE_PDF_DEPENDENCIES.md)。

如复用本项目的方法或软件，请注明：*SharePack v1.0.0, Paper Figure Story · SharePack*，并附仓库或正式Release链接。此项为建议署名，并非对未发布科研内容的引用要求。

---

<div align="center">

**Evidence first. Story second. Design with traceability.**

[获取正式版](https://github.com/Lu18835713910/paper-figure-story-SharePack/releases/tag/v1.0.0) · [返回顶部](#sharepack)

</div>
