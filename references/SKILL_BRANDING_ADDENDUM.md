# SharePack Skill 附加规范：期刊身份与品牌视觉（候选，R22）

## 定位

这是 **SharePack 科研编辑流程的品牌层**，不是科研事实证书，也不是商标许可。禁止用 Logo 状态晋升科学审核、来源审核或 publication_ready。

### 1. 输入与核验

1. 从 DOI、原始论文首页、出版社和期刊官网确认**论文所在期刊**。优先官方当前品牌页面与真实发表文章；历史档案用于辨认旧版，第三方 Logo 库仅作候选发现渠道。
2. 记录：`journal_name`、`paper_doi`、`logo_variant`（historic/current/editorial_text_fallback）、`branding_source_url`、`source_date_or_era`、`asset_sha256`、`brand_rights_status`、`private_or_public_scope`、`reviewer`。
3. 不得把旧彩色Logo、当前黑字标、第三方仿制品称为同一版本，也不得把找到Logo误写成取得授权。
4. 如查不到可信标识或公开使用权限不明确：仅用**普通文本期刊名称**，并标注“独立科研解读 / 非期刊官方出品”。

### 2. 科研叙事与封面设计分离

- 先冻结该轮已审核的科学故事和 Figure 计划，再设计品牌区域。
- 封面Logo不能喧宾夺主或遮盖主题标题；仍以论文研究问题、原创科学视觉和读者认知路径为主。
- 内页Logo不得削减 Figure、比例尺、正文的可读性；总结页深色背景应设计有足够对比度的浅色Logo底板。
- 页眉尺寸是候选起点，不是对任意论文强制固定位置：STP R22 私有已验收封面图宽约 3.40 in、内页约1.81 in；Seq或其他模板必须重新检查布局坐标。
- 保留PPTX原生可编辑标题/正文/形状。期刊Logo可单独作为图片，不把整页扁平化。

### 3. 受控执行

- **inspect**：获得PPTX页数、尺寸和所有页眉候选对象。
- **draft**：生成默认 `layout_approved=false` 的待审JSON。**绝对禁止**直接将草稿当批准的布局。
- 审核者根据真实400px预览逐页手动确定Logo与标题位置、字号；必要时编辑 `slides[].adjust`。
- **apply**：必须有 `--private-only`、精确源PPTX SHA、Logo SHA、逐页批准布局；如位置冲突、试图覆盖原稿或标记为公开分发则STOP。
- **verify**：原始所有文字与嵌入科研Figure字节均应无变化；未经授权修改的原有XML元素也应相同。
- PowerPoint 16.0 原生打开、编辑、保存、重开、导出及400px视觉核查要独立完成；LibreOffice PDF核查不能冒充Windows宿主通过。

### 4. 验收区分

| 范围 | 技术要求 | 可称状态 |
|---|---|---|
| 私人研究评审 | 身份清楚、来源SHA、视觉适配、非官方声明 | `PRIVATE_BRANDING_PASS` |
| 科学与来源 | 数值/对照/图注独立核验，R19来源通过 | 不由 Logo 工具判定 |
| GitHub/公众再分发 | 商标使用、论文Figure许可、第三方素材权利均已核查并获必要权限 | 需要单独外部权利审查；当前 `NO-GO` |

### 5. 已验证/未验证

- **已验证**：STP R22 六页私人版本使用用户指定的Nature Communications历史彩色波纹Logo，原文和4个科研Figure保持不变，400px页眉以下无差异。
- **未验证**：Seq-Scope-X R22 四页版因当前会话未得到其真实PPTX，不能拿Seq-R17旧稿冒充修订，也不能自动复用STP坐标。
- **勿改**：R7/R11/R13/R17历史母版，R19来源子系统、正式GitHub main和RC2发布门禁。
