# P1 外层验证协议审查 R02

出分前修订。旧草稿快照在 `draft_snapshot_before_protocol_correction_20260926/`，含 SHA 清单。修订不触及正在运行的 P1 40 折合同，也没有启动新 E2E fit 或读取新 U 分数。

`completion_review.json` 明确旧 A/B 为 `A_NEW_CPU_CT_FULLFIT`/`B_NEW_CPU_CT_FOLDMEAN`，CPU 使用 F 内 90/10 选轮再全 F 重训；线上 V100 的 V80/V85 在 F 拟合、H 早停，以同一模型预测 H/test。两者算法不同，旧 A 的 0.946213357 只能用于新 CPU 配方下 CT fullfit/foldmean 的机制对照。旧 C/D 因旧 A/B 门槛失败未测试，不能当作已验证的线上 V100 外层基准。本次 P1 是新机制，旧 CT B-A 的资格门禁不迁移。

| 环节 | 线上 V100 实际合同 | 原草稿问题 | R02 忠实同 T/U 比较 |
|---|---|---|---|
| 外层与身份 | 五个 T/U，U 不参与训练；历史测试本身并非新盲测 | 复用 seed42437 的索引可以，但称旧 A 为 V100 | 沿用索引并校验标签、ID、fold、来源 SHA；新旧两臂共用 T/U |
| V80 | T 内 40 折 seed104395303；F 训练、H 早停500，同模型预测 H/U；113列 float32 | 旧缓存改成 F 内早停和全 F 重训 | 新跑 200 个旧算法原子，保留逐 atom 模型和预测 |
| V85 | T 内 40 折 seed42；嵌套 TE；F 训练、H 早停350，同模型预测 H/U；148列 float64 | 同上 | 新跑 200 个旧算法原子；P1 grouped 另跑同 F/H 的 200 原子，仅改12组交互约束 |
| CT | T 内5折 seed42 产 OOF；全 T 单模型 1426轮、GPU/特征状态按旧配方预测 U | 原 A 的 CT fullfit 本身不是 CPU 差异的补救 | 可复用已完成的五个 CT cache，但须单独审计逐折与 fullfit 预测、行、来源代码、GPU 运行及 SHA；旧缓存未保存模型/状态字节，不能宣称模型重载核验；不复用旧 A/B 分数或资格 |
| V90 元层 | T 内 seed42 五折；每折 fit-only mid-ECDF，网格选 V85 权重；五份不同状态/权重下的 U 预测取平均 | 原草稿直接拿旧 A 的元预测 | 用本次旧算法 V80/V85 OOF 和 U 重新拟合，不搬全局 OOF/ECDF/权重 |
| V100 元层 | T 内 seed42 五折用于开发 OOF；完整 T 的 V90/CT OOF 拟合两套 ECDF 和 CT 权重网格 0..0.5/0.025；U 用全 T 状态、V90 五份均值、CT 全 T 单模型 | 原草稿以旧 A `baseline_proba` 作为 V100 | 每个外层独立重建 V100 基准，不用旧 A/B 或未执行 C/D |
| P1 候选 | C=0.5×(V85+grouped V85)，M=0.5×(V100+C) | 文字误写 `0.5*V100+C`，代码是 `0.5*(ref+co)` | 统一为 `M_U=0.5*(V100_U+C_U)`；正式 40 折先选 C/M，U 不参与选择 |
| 提交验收 | 同口径完整 40 折高于 V100，外层同 T/U 5/5 正向，产物复核 | 弱 A 比较可以错误放行 | 旧 A 只作旁证；忠实线上 V100 外层重建和新候选全流程是硬门槛 |

CT cache 的历史训练不依赖旧 CPU A/B 配方，可在新合同下合法复用；复用只限相同 T/U、相同原始数据与 CT 配方且检查完整闭包。`splits.npz` 只提供已冻结的行索引。旧 CPU atom/cache、旧 assembled 预测、全训练 OOF/test 和旧 C/D 门禁均不作 R02 最终外层基准。参考：`model/validation/e2e_legacy_comparison_20260905/PREREGISTRATION_R01.md`、`legacy_cpu.py`、`compare_legacy.py`、`DEPLOYMENT_INPUT_INVENTORY.md`、`model/validation/e2e_v100_20260905/completion_review.json`。
