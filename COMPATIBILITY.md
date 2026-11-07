> **Historical development record** — retained for provenance. Consult README and KNOWN_LIMITATIONS for the current RC status.

# SharePack–PFS兼容合同 | 0.1.0-dev.2

## 不依赖与单向数据流
- PFS单独运行不需要SharePack，不需要额外Python依赖；SharePack不import PFS，也不要求PFS安装。
- SharePack能够复用PFS科学知识 **M1 1.1** 及 M2-B `m2b-1` 图像清单，作为输入文件而非PFS内部库；支持独立PDF源模式。
- 两者**没有**互相写入对方的文件或修改PFS状态的权限。PFS内部工程PASS不能升级SharePack的科学审核结果。

## 兼容矩阵
| 场景 | 当前结果 | 证据限制 |
| --- | --- | --- |
| 独立PDF输入 / Passmore 原论文 | 工程回归PASS | 10卡、12个裁图、10/10 PNG旧版一致；Agent预先准备科学故事 |
| PFS public v1.1.0 M1 1.1结构 | 合同与合成端到端PASS | 已校验RSU/typed relation/Source hash；不是实际PFS已产生的M1 |
| M2-B `m2b-1` Figure资产 | 合成文件导入PASS | 实际SHA验证复制、来源记录、缺文件拒绝；未测试真实PFS全部资产类型 |
| PFS本地v1.1.1实际模型 | **NOT_TESTED** | 需要Windows受保护维护环境里的真实文件 |
| 早期1.0、未知schema1.2、陌生relation | 明确拒绝 | 不允许无审查语义转换 |
| 同篇论文：PDF直入 vs PFS真实输出 | **NOT_TESTED** | 未获得同一论文的真实PFS知识模型；不可声明质量提升幅度 |

## 重要约束
1. 研究关系保留原 ID、两端、type、provenance、certainty。`experimental_precedes`需要paper_reported + order_basis；`argument_transition`仅表示讲述；比较/并行不是因果。
2. `pfs_bridge_context.json`绑定上游 `knowledge_sha256` 和资产清单SHA。卡片验证时会**再次读取和校验**上游文件，避免桥接后PFS变更仍沿用旧证据。
3. 来源PDF的SHA须与知识模型标记的primary paper一致（如该标记可用）；跨PDF或多篇输入不得自动合并。
4. 图像导入只支持可访问、SHA匹配的PNG；未登记有效视觉审核的图片保持PENDING。缺少真实图片或不支持文件格式必须报错或单独启动PDF裁切流程。
5. 不覆盖已有桥接文件，不输出到知识文件所在目录树；真实PFS验收只读保护目录SHA。
6. 现阶段桥接只是**科学身份与证据接口**：Agent仍需根据材料制作SharePack故事JSON；没有成功的PFS协同自动故事生成器。

## Windows真实v1.1.1验收
在本地受保护维护环境，找到一个实际产生过且有效的 `knowledge.json` 和可用的原始Figure `assets.json`（没有就只做知识桥接），执行：

```powershell
python scripts/readonly_compat_accept.py --knowledge "C:\actual\PFS_output\knowledge.json" --pfs-assets "C:\actual\PFS_output\assets.json" --outdir "C:\isolated\sharepack_probe" --protect-root "C:\actual\PFS_output"
```

之后必须审核 `readonly_acceptance_report.json` 与被保护文件SHA；本脚本只验结构和来源，不运行PFS主流程，也不改动其状态。若原PFS产物本身缺图/缺知识，报告 `NOT_TESTED/INPUT_UNAVAILABLE`，不可模拟成通过。
