> **Historical development record** — retained for provenance. Consult README and KNOWN_LIMITATIONS for the current RC status.

# 0.1.0-dev.2 开发验收记录（2026-11-05）

## 实际执行与结果

| 检查 | 已观测结果 |
| --- | --- |
| unittest 全部合同与适配测试 | **19 PASS / 0 FAIL** |
| Nature Communications Passmore 2026 实际原文 | 10页PDF，4处Figure caption候选，12处真实Figure裁切，10张卡输出 |
| 真实图与成果 | 原PDF数据图、PPTX、10页PDF、10张PNG，全部重新生成 |
| dev.1 到 dev.2 PNG回归 | **10/10逐字节SHA匹配** |
| PFS 合成端到端适配 | `bridge-pfs`→SHA复制Figure→source-bound story→PPTX（8页）PASS |
| PFS原始知识文件被改动 | 正常拒绝，`PFS_ORIGINAL_KNOWLEDGE_DRIFT` |
| M2-B素材丢失、预认证图丢失 | 显式诊断/拒绝，不升级为 reviewed |
| PFS relation/type/PDF错配 | 明确拒绝未知类型和来源错误 |
| PDF Caption容错 | `Fig. 1 |` / `Fig 2.` / `Figure 3:` 三类样例成功识别为未核验候选 |
| 本地受保护只读探针 | 合成fixture: 1 RSU/1关系/1Figure，保护文件SHA不变 |
| wheel 制作与入口 | `0.1.0.dev2` wheel构建、离线安装、`sharepack --help` PASS |
| 干净环境全依赖安装 | **BLOCKED**：无联网/未缓存依赖；离线新venv不能运行PDF/PPT功能 |
| 真实 PFS v1.1.1 导入 | **NOT_TESTED**：保护目录未挂载本环境 |
| 第二篇真实PDF软件端到端 | **NOT_TESTED**：可查到公开ST-CellSeg论文，但二进制PDF下载不成功；有跨版式合成PDF测试，不能冒充第二篇真实盲测 |
| 真实Windows Office 字体/视觉验收 | **NOT_TESTED** |

## 命令

```bash
python -m unittest discover -s tests -v
python -m sharepack.cli prepare --pdf article.pdf --outdir output/index
python -m sharepack.cli extract-regions --pdf article.pdf --regions reviewed_regions.json --outdir output/assets
python -m sharepack.cli validate --story reviewed_story.json --assets output/assets/assets.json
python -m sharepack.cli render --story reviewed_story.json --assets output/assets/assets.json --outdir output/cards
python scripts/readonly_compat_accept.py --knowledge PFS/output/knowledge.json --outdir separate/bridge_probe --protect-root PFS/output
```

## 未关闭事项

1. PDF独立模式仍需Agent全面阅读和审查科学故事，不是无人辅助的高可信自动科研结论生成。
2. 任意论文的Figure定位与panel完整性仍需Agent/审阅者确认，未实现通用可靠的自动裁切决策。
3. 真实v1.1.1、真实多论文科学质量/用户体验、完整Windows安装与字体、许可证/人物版权全部阻断公开Beta。
4. 只用一篇真实PDF做回归。没有实测任何“接入PFS后科学质量提升”的结论；合成合同测试不代表改善已经实现。

**裁决：DEV2_ENGINEERING_PASS / PFS_SYNTHETIC_END_TO_END_PASS / PFS_REAL_1.1.1_NOT_TESTED / SCIENCE_PARTIAL / PUBLIC_BETA_NO_GO**
