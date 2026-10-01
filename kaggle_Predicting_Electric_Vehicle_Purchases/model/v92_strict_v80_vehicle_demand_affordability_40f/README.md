# v92_strict_v80_vehicle_demand_affordability_40f

## Preflight revision

- `R2 / 2026-09-04`：正式 40 折训练、显式 verify 与独立终审均通过。OOF `0.9462479761681426`，相对 v80 `+0.000007365191779`、seed42 同行桶胜 `21/40`；未过项目强度门槛，但绝对 OOF 通过多样性边界，故仅可另立融合预注册。C01 按完成顺序计为第 10 个关闭项。
- `R1 / 2026-09-04`：修复历史去重不可复现问题。新增冻结的 `history_formula_manifest.json`，覆盖截至 v90 的全部 90 个数值版本目录、101 个递归 Python 文件，并记录逐文件 SHA、大小与 AST 跨字段除法签名；audit 会逐文件重算并校验 v84–v90 全覆盖，三种目标签名任一命中即拒绝。合成测试使用完全不同的变量名验证别名传播仍能识别三种公式；guarded smoke 明确把 `LightGBM.fit` 替换为拒绝函数。
- `R0 / 2026-09-04`：完成无标签字段契约、历史 feature-builder 重叠审计和预注册；从 v87 R4 的工程合同复制 checkpoint、flock、资源硬停、统一失败关闭和 staged verify，但更换为本实验唯一的 3 列 feature block。没有正式训练，也没有产生效果证据。
- 候选代码 SHA-256：`b97236c4266473e5d391991158789f142bb6a7b81a74402e13df0cb638b7239b`
- 冻结配置 SHA-256：`4efa8809ee66d7839ef10265914cd6e37f0a9f7be66079741c750cac6337c2c3`
- 回归测试 SHA-256：`ca1528b76751b78739e2fd0518db72d9fd825ca48c4707bf9de97e9bdb1a88e8`
- 历史公式 manifest SHA-256：`0d525fdb7294efa9ea344834dd8dd42815e84f0365130fd6a1f2463726e73f25`

## 字段边界与历史审计

结论：`GO_DISTINCT_MECHANISM`，但不得把它描述为真实家庭人均量或成本偏好。

`train.csv`、`test.csv` 和 original 10k 都没有 `Household_Size`、`Cost_Sensitivity`。因此本实验只表示可观测的“已有车辆容量、增加一辆车后的收入承载、单位通勤承载”，不声称观测到家庭人数或成本敏感度。

冻结 manifest 对 `model/v1_*` 至 `model/v90_*` 的全部递归 Python 文件逐一记录 SHA，并用 AST 别名依赖传播检查分子/分母原始字段。三种目标签名均为零命中，不依赖最终特征列名：

| 历史方向 | 已覆盖内容 | 与 v92 的边界 |
| --- | --- | --- |
| v2/v6/v80 | 收入、通勤、车辆数各自的原始值、数字位、频次和单列 TE | 没有三者的逐行需求比或承载比 |
| v54/v55 | 各字段的类别、分箱和 spline 加性表示 | 没有车辆需求/收入承载比 |
| v65 | 复制补贴、环保等强列改变 column sampling | 与比值机制无关 |
| v68–v76 Naji | 构造特征前明确删除 `Number_of_Cars_Owned` | 不可能包含车辆归一化比值 |
| v87 | 通勤距离÷充电供给及无家充负担 | 没有用车辆数或收入归一化 |

候选选择只依据字段语义、历史源码和 train/test 无标签范围；没有用目标标签比较多个候选块。train/test 的收入、通勤和车辆数均严格为正，车辆数只取 1–4，三个冻结比值均有限且 train/test 分布范围一致。

## 预注册

- 实验 ID：`v92_strict_v80_vehicle_demand_affordability_40f`
- 研究周期：`C01`；计划位置 `10`，最终以正式关闭顺序和 `research_cycle.json` 为准。
- 实验类型：`SINGLE_MODEL`。
- 状态：`COMPLETE`；已通过显式 verify 与独立终审，计为 C01 第 10 个关闭项。
- 基准：`v80_strict_v61_outer104395303_40f`，OOF `0.946240610976364`。
- 唯一机制假设：深度 4 的树从三个独立原始列逼近“单位已有车辆的通勤需求”和“新增一辆车后的收入/通勤承载”需要额外分裂；显式的低维逐行比值可能稳定暴露购车边界。
- 唯一主要变量：只追加冻结的 `vehicle_demand_affordability_v1` 三列；不增加 TE key，不改变 LightGBM 参数、模型种子或 inner TE 种子。
- outer：`StratifiedKFold(40, shuffle=True, random_state=42)`。v80 自身 outer seed 为 `104395303`；只比较完整 OOF，并把同一 seed42 行桶用于 24/40 诊断，不声称跨 seed 同编号折配对。
- inner TE：`104395303 + one_based_outer_fold`；inner-hold prior/count/sum 仅来自 inner-train，outer-valid/test 仅使用完整 outer-fit。
- LightGBM：四个随机源、全部超参数与 v80 一致；版本必须为 `4.6.0`。
- 项目强度门槛：完整 OOF 相对 v80 至少 `+0.0001`，且固定 seed42 行桶至少 `24/40` 胜出。
- 多样性边界：若 OOF 至少 `0.9452` 但未过强度门槛，只能设 `eligible_for_separate_preregistration=true`；本实验自身 `allowed_for_fusion=false`，后续小融合必须单独预注册并满足 `+0.0001` 与 `5/5`。
- 10 折止损：第 10 折 checkpoint 和资源检查后，若同覆盖行 OOF delta `< -0.00005` 且胜桶 `<=4/10`，原子写 `FAILED` 并停止；等号不触发。
- 预算：40 folds、8 threads、墙钟 60 分钟、进程 peak RSS 16 GiB、提交 `0`。
- 预注册时禁止：审计阶段正式训练、读取 v86 中间预测、修改历史目录/台账/周期计数、用 audit/smoke 判断效果。

## 冻结 feature block

仅使用每行自身原始字段，不使用标签、test 拟合态或全局统计：

1. `mobility_commute_per_owned_car = Daily_Commute_km / Number_of_Cars_Owned`
2. `afford_income_per_postpurchase_car = Annual_Income_USD / (Number_of_Cars_Owned + 1)`
3. `afford_income_per_postpurchase_car_km = Annual_Income_USD / ((Number_of_Cars_Owned + 1) * Daily_Commute_km)`

列序 SHA-256 为 `ae0be4adc87e916ae6db1d79748639f297f642bff43dc5448c3ee7379ea0354c`。v80 static `62` + 本块 `3` + 原有 TE `51` = `116` 列。

## 工程合同

- v80 COMPLETE、OOF、参数、17 个 TE key、smooths、strict prior、inner/model seeds 与 LightGBM 版本逐项校验。
- audit/smoke 只对 v80 预测做流式哈希，不用 `np.load` 解析真实数组；smoke 只用合成预测。
- 每折 checkpoint 绑定 runner/config/input/validation-index 哈希，可安全恢复。
- formal 使用单实例 `flock`；获得锁后再次检查 COMPLETE。
- 每 5 折一行 `INTERIM_DIAGNOSTIC_NOT_FINAL`。
- 每折前后、40 折后、staged verify 前后执行 60 分钟/16 GiB 硬停。
- 完整结果先 staged，从 40 checkpoints 重建验证后才原子标记 COMPLETE。
- futility、资源、异常三类失败都有统一最小 schema、present/missing/invalid 清单；异常关闭在原 flock 释放前完成。
- verify 重建 OOF/test，复算逐折/整体 AUC、Spearman、止损、门槛、权限和产物哈希。

## 运行方式

```bash
python model/v92_strict_v80_vehicle_demand_affordability_40f/v92_strict_v80_vehicle_demand_affordability_40f.py --mode audit
python model/v92_strict_v80_vehicle_demand_affordability_40f/v92_strict_v80_vehicle_demand_affordability_40f.py --mode smoke

# 正式训练已经完成，不得用相同配置重复计数：
python model/v92_strict_v80_vehicle_demand_affordability_40f/v92_strict_v80_vehicle_demand_affordability_40f.py --mode train
python model/v92_strict_v80_vehicle_demand_affordability_40f/v92_strict_v80_vehicle_demand_affordability_40f.py --mode verify
```

## 当前结论

- 运行状态：`COMPLETE`；显式 verify 与独立终审均 `PASS`。
- 正式 OOF / delta / 胜桶：`0.9462479761681426` / `+0.000007365191779` / `21/40`。
- 与 v80 的 OOF/test Spearman：`0.998341826483` / `0.999925870236`。
- 运行耗时与资源：`1578.990369` 秒 / peak RSS `4.448287964 GiB`。
- 正式产物：40 个 checkpoint、OOF/test、submission、`cv_results.json`、`sources.json`；OOF/test 均由 checkpoint 独立逐元素重建一致。
- 决策：`ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_ONLY`。
- 是否允许当前产物直接融合：否，必须另立预注册；是否允许提交：否。
- 周期计数：C01 第 10 个正式关闭项，`10/20`；ME-C01 仍为 `NOT_DUE`。
