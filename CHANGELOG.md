> **Historical development record** — retained for provenance. Consult README and KNOWN_LIMITATIONS for the current RC status.

## 0.1.0-dev.4-candidate — 2026-11-06

- Restored evidence-first free-composition portrait pages using new `sharepack/freeform.py`.
- Added narrative logic, figure hero, portrait figure+text, side-by-side, stacked figure, and synthesis compositions selected from reviewed story/media shape.
- Preserved legacy dev.3 renderer behind `--layout-engine legacy`; freeform is candidate default.
- Added `composition_plan.json`, stronger text collision check, and explicit figure-size visibility notes; metric/limit/source trace retained.
- New four regression tests cover mixed media compositions, actual PPT shapes, input immutability, layout choice guards, and no silent metric loss.
- This does NOT confer PFS 1.1.1 real end-to-end pass or scientific / Office visual acceptance; public beta still NO-GO.

# SharePack change log

## 0.1.0-dev.3-candidate (2026-11-05)

- S0：对WorkBuddy报告进行授权边界、SharePack代码缺陷、PFS历史接口差异的分层归因；冻结核心产品合同。
- S1：支持 `m2b-1`及历史 `pfs-figure-assets-1` 的受控归一化；缺证据Figure显式待审，原PFS来源不可变；保留M1 RSU文本、来源定位和关系身份。
- S1：消除 `crop_pdf_pt` KeyError、`numbers[0]`、`limit`遗漏及`pfs_needed=False`硬编码；引入多布局策略、容量检测、待审核小图告警。
- S1：新增`audit-plan`及story coverage / panel-selection审计，承认Agent语义阅读不可由CLI代替。
- Tests：24项PASS（19项原回归+5项新增）；不同布局的十卡内部样例。真实G5_R和双Agent实跑未执行，发布NO-GO。

## dev.2 baseline

以现有`0.1.0-dev.2`为不可变基线；相关旧报告保留于历史文档，不与dev.3候选验收结果混同。
