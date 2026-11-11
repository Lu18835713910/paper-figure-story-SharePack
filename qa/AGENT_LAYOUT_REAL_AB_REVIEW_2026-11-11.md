# Agent 参与排版：真实论文 A/B 盲点审查（2026-11-11）

## 本轮真实执行

- 实验论文：Posfai 等，*Gauge fixing for sequence-function relationships*，PLOS Computational Biology，DOI 10.1371/journal.pcbi.1012818。
- 真实 PDF：24 页，SHA-256 `53cf1a75f3173c39640dd1f1963f0d708114a71377fc62cd0bedc792ca402fc1`。
- 真正使用出版社提供的 Figure 1 PNG，2190×1028，SHA-256 `e05e7ba6a51b72d9992ee60243ffc89ddd8c68b085fce9d571ce4f4bc858ac10`；科学检查 `PENDING`。
- 实验隔离分支：`qa/agent-planned-ab-20261111`。A/B 共享同一故事、Figure、字体、期刊设计规范，输出分别置于独立目录。
- A：无 Agent 文件的默认启发式自适应选版；B：ChatGPT 依据科研角色逐卡编写 8 项版式建议及理由，写成 SHA 绑定的真实 `sharepack-agent-layout-plan-v1`，提交给程序。**不是 GitHub Actions 中实时调用外部 LLM/自主多轮反思**。
- 实际执行：[Actions 42948795797](https://github.com/Lu18835713910/paper-figure-story-SharePack/actions/runs/42948795797)，输出包含真实 PPTX、PDF、八页 1080×1440 PNG 与 A/B 图片。

## 量化结果

| 项目 | A 自动启发式 | B Agent 提议 |
|---|---|---|
| PPTX、PDF、8 PNG | PASS | PASS |
| 八卡版式序列 | classic, framework, essay, figure_explain, essay, classic, essay, classic | classic, framework, classic, figure_explain, classic, classic, classic, classic |
| 与 A 不同的卡片 | — | 第3、5、7张 |
| 提议因容量不足回退 | — | 第4、6、8张 |
| 几何文本框碰撞 | 0 | 0 |
| 400px 字号静态预警 | 0 | 0 |
| 科学叙事字段覆盖 | 未全部验收 | **FAIL：第7张遗漏原始研究问题** |

Agent 在第4张提出的 `figure_first` 因 `AGENT_FIGURE_FIRST_REPLAN_SPACE` 被拒绝；第6与第8张提出的 `essay` 因 `AGENT_LAYOUT_ESSAY_OVERFLOW` 被拒绝。说明安全约束在实际执行中有用，不代表外观得到改善。

## 逐卡实际视觉观察

- 第3张：B 改成逐项标签，信息较均匀，A 对中心问题的视觉强调更明显；没有明显证明 B 优于 A。
- 第5张：B 改成报告式多段排列，A 的加粗核心发现更容易扫描；B 不一定更合适。
- 第7张：B 将综合页的结论置于段中，没有显著美观提升，且**原稿的研究问题（“这项工作最重要的认识是什么？”）未显示**。几何检验仍为 0 碰撞，揭示内容完整性门禁缺失。
- 其余五张基本相同，包括 Figure 1 页面。没有获得新的 panel 细分能力，也没有自主改变卡片数。并非“真正自由排版”已完成。

## 结论和工程要求

**真实 Agent 规划接口：PASS。Agent 提议自动验收/回退机制：PASS。Agent 提升视觉质量：UNPROVEN。排版后科研字段完整性：FAIL。总体：NEEDS_REVISION，禁止集成主分支或发布 Beta。**

下一轮先做“每卡必须显示哪些科研字段”的语义覆盖核验，不允许从故事中丢掉问题、方法、观察、解释、局限或数值。然后再让 Agent 逐页根据实际导出图做质量评分与重排，允许科学合理的拆卡/合卡，不靠盲目放宽模板。
GitHub 跟踪：[Issue #3](https://github.com/Lu18835713910/paper-figure-story-SharePack/issues/3)。

> 本轮有经过模型阅读内容后编写的布局偏好文件，不是纯启发式；但 ChatGPT 编写的偏好没有经过独立科学专家核实，因此不能把其理由说成已获同行科学验证。Logo 本次为期刊文字标识，没有在公共 QA 演示中加入尚未核实使用权限的商标图片。
