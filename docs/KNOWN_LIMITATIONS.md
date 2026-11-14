# SharePack v1.0.0｜已知限制与验收边界

本页描述[正式v1.0.0](https://github.com/Lu18835713910/paper-figure-story-SharePack/releases/tag/v1.0.0)及现有可核验结果，不继承旧v0.1.0-rc.1的发布前阻断状态。

| 范围 | v1.0.0已完成的验证 | 仍需明确的边界 |
| :--- | :--- | :--- |
| Standalone | 安装后实际通过原创虚构数据示例及独立Python入口 | Agent需完成科学信息整理；单凭PDF并不能自动认证结论 |
| PFS-assisted | 正式PFS v1.2.0的单个真实论文案例，同源M1、Research Logic A/B与Figure融合 | 没有证明全部论文/所有宿主均可复现；完整B独立保留 |
| 可信来源 | PDF、登记Figure和关系引用校验，错误SHA及缺失关键字段拒绝 | 来源一致性不代表Figure panel含义经过独立科学审稿 |
| 原生PPTX | PowerPoint编辑、保存、重开与PDF导出已用于发布验收 | 宿主字体、版式与导出实现会影响跨设备视觉一致性 |
| 400px预览 | 发布用原创示例通过实际移动端宽度审阅 | 复杂真实论文某些图内微型标注仍需要完整尺寸PDF |
| PDF引擎 | 正式运行时使用pypdfium2、pypdf；不依赖PyMuPDF | `prepare`只生成文本和图注候选；不生成推测性Figure预览 |
| PDF结构 | 审阅后的显示页面区域可提取；默认坐标及旋转案例得到定向验证 | XObject只支持直接显示对象；嵌套对象、显示矩形未承诺；非默认UserUnit被拒绝 |
| 安装与Agent | Python全新环境与Codex新会话实测通过 | WorkBuddy新会话路由尚未独立验证；旧版本副本需核实实际活动路径 |
| 科学终审 | 实际来源和选定Figure得到核验 | 独立领域专家完整审核、跨论文统计泛化能力未获认证 |

## 不能误解的事实

- `scientific_status=PARTIAL` 只表示科学审核范围尚未完全闭环，不代表软件安装失败。
- 结构、来源和SHA检查不能替代作者原文、图注、方法与对照的科学解释。
- 单个真实PFS-assisted案例不能作为通用科学理解能力的统计保证。
- 私人测试论文的科研原图、期刊Logo及未获授权素材不包含在公开发行附件中。
- Github main可能包含发布后文档/示例维护，固定 `v1.0.0` Tag 和 Release 附件不因此改变。

更多背景见 [README](../README.md)、[TESTING](../TESTING.md)、[COMPATIBILITY](../COMPATIBILITY.md)、[许可证](../LICENSE) 以及 [Release说明](../RELEASE_NOTES.md)。
