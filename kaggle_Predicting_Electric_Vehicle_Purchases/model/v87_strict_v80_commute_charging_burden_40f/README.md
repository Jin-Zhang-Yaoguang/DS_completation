# v87_strict_v80_commute_charging_burden_40f

## Preflight revision

- `R5 / 2026-09-04`：正式 40 折训练、显式 verify 与独立终审均通过。OOF `0.9462357606221546`，相对 v80 `-0.000004850354209`、seed42 同行桶胜 `23/40`；未过项目强度门槛，但绝对 OOF 通过多样性边界，故仅可另立融合预注册。C01 按完成顺序计为第 9 个关闭项。
- `R4 / 2026-09-04`：修复 R3 的并发关闭边界与测试缺陷。`FAILED_EXCEPTION` 现在由 `exclusive_run_lock` 在释放原 formal flock 前写入；第二实例只能在失败证据已经原子落盘后取得锁。合成并发测试会在异常 writer 执行期间从独立进程尝试同一把非阻塞 flock，必须被拒绝；同时修正 `pending_path` 测试变量作用域。
- `R3 / 2026-09-04`：补齐统一异常关闭。取得 formal `flock` 并进入计时范围后，训练、恢复、产物生成或 staged verify 的任一普通异常都会清理 pending 文件，记录最终墙钟/peak RSS，以统一最小 schema 原子写 `FAILED_EXCEPTION`；残留 checkpoint/输出列入 present 且全部标记无效，结果可由 `verify` 在不解析预测数组时独立复核。并新增合成 wrapper 异常回归测试。
- `R2 / 2026-09-04`：按独立审计修复关闭边界。完整结果先写进进程专属 staged 文件，以 `STAGED_COMPLETE_PENDING_VERIFY` 身份从 40 个 checkpoint 完整重建和验证；验证结束后再做墙钟/peak RSS 硬检查，仅允许追加这条资源证据和改为 `COMPLETE`，最后原子替换。资源与 10 折 futility 两类 `FAILED` 统一包含最小 schema、elapsed/资源摘要及 expected/present/missing 产物清单，所有已存在产物明确无效；`verify` 可在不解析预测/checkpoint 数组的情况下独立验证 FAILED。formal 读取 v80 OOF/test 后，强制核对 v80 `sources.json` 自身哈希、train/test ID 行身份及 OOF/test 的 source/artifact 哈希。
- `R1 / 2026-09-04`：修复只读边界。`audit`/`smoke` 显式使用 `load_predictions=False`，只读取 strict v80 的 JSON 合同并对 OOF/test 文件做流式 SHA-256，不再用 `np.load` 解析真实预测数组；smoke 的概率数组均为合成数据。
- `R0 / 2026-09-04`：完成历史重叠审计、预注册、冻结配置、runner、audit 与 smoke；没有启动任何 LightGBM 拟合，也没有产生正式效果证据。
- 候选代码 SHA-256：`88286808f3cd0cbac1426a8b20090a92d1ee0dc68e451c96e47797b76b2877a2`
- 冻结配置 SHA-256：`a245bfff0f61ae66d0c3f4730d06268736c734812ffb5294569c34992bf6caa6`
- 回归测试 SHA-256：`c0c9190766856d0d97c2bdc0d740ad0c52eb5a590291b102d40361c9f48443ad`

## 历史重叠审计与 GO/NO-GO

结论：`GO_DISTINCT_MECHANISM`。最接近的是 v40，但它只增加 `1 km` 通勤分箱 TE，没有表示“通勤距离相对居家/工作地充电覆盖的负担”。本实验不重复历史已经否定的收入 TE 邻域、交叉、平滑或特征复制路线。

| 历史方向 | 已验证内容 | 与 v87 的边界 |
| --- | --- | --- |
| v23 | income × environment × subsidy TE，OOF `0.9458685953610309` | 没有通勤/充电基础设施负担 |
| v40 | commute bin1 TE，OOF `0.9459491015370579` | 只有通勤分箱，无充电交互 |
| v45/v46 | income × environment 半径 TE | 均只完成 3 折，不是该机制 |
| v53 | income-bin2 × range，均值增量约 `+0.000001465`，2/5 胜出 | 没有通勤/充电交互 |
| v65 | 复制 subsidy/environment 特征以改变 column sampling | 不是新基础设施表示 |
| v69–v76 | Naji、收入邻域、income × environment/subsidy | 没有通勤/充电负担 |
| v54 补充核查 | 稀疏类别 home-charging 交互 | 没有通勤距离÷公共充电覆盖的数值表示 |

若上述冻结历史文件中出现本实验四个精确列名，runner 会拒绝 audit/train，GO 自动失效。

## 预注册

- 实验 ID：`v87_strict_v80_commute_charging_burden_40f`
- 研究周期：`C01`
- 实验类型：`SINGLE_MODEL`
- 是否计入本周期 20 个普通版本：是；正式 `COMPLETE` 且独立终审通过后计为 C01 第 9 个关闭项
- 周期内序号：`8`
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-04
- 假设：同样的通勤距离，在家庭与工作地充电覆盖更弱时会形成更高购车摩擦；显式提供“基础设施供给”和“单位充电覆盖的通勤负担”可让深度 4 的树更稳定地找到这类有限交互。
- 机制依据：v80 已有原始通勤、两处充电站数量和居家充电类别，也有各自 TE，但浅树需自行消耗多个分裂才能形成比率与瓶颈；新增列是逐行、无标签、低维表示，不增加 TE key。
- 基准版本与 OOF：`v80_strict_v61_outer104395303_40f`，严格 OOF `0.946240610976364`，正式触发前必须仍为 `COMPLETE` 且配方合同通过。
- 唯一主要模型变量：只追加冻结的 `commute_charging_burden_v1` 四列；不调模型参数、不新增 TE、不改严格 prior。
- 评估切分：候选 outer 为 `StratifiedKFold(40, shuffle=True, random_state=42)`；v80 基准自身 outer seed 为 `104395303`。整体 OOF 在同一批训练行上比较；24/40 使用候选固定 seed42 validation 行桶同时切两条完整 OOF，不能解释为跨 seed 的同编号折配对。
- inner TE：每个 outer fold 使用 `104395303 + fold`；inner hold 的 prior/count/sum 仅来自 inner-train，outer-valid/test 映射仅来自完整 outer-fit。
- LightGBM：四个随机源和所有参数逐项保持 v80，运行版本必须为 `4.6.0`。
- 主要指标：完整 OOF ROC AUC。
- 项目强度门槛：相对 strict v80 整体 OOF 至少 `+0.0001`，且固定 seed42 行桶至少 `24/40` 胜出。
- 多样性边界：若 OOF 至少 `0.9452` 但未过项目强度门槛，只能标记 `eligible_for_separate_preregistration=true`；本实验 `allowed_for_fusion=false`，后续小融合必须独立预注册并满足 `+0.0001` 与 `5/5`。
- 10 折止损：第 10 折 checkpoint 与资源检查完成后，若同覆盖行 OOF delta `< -0.00005` 且胜出桶 `<=4/10`，原子写 `FAILED`、保留 checkpoint 并停止；等于阈值不触发。
- 计算预算：40 folds、8 threads；取得 `flock` 后墙钟不达到 3600 秒，进程 peak RSS 不超过 16 GiB；每折前后（含第 40 折）、全部折后、staged 完整验证前及验证后/原子 `COMPLETE` 前检查，验证耗时与 peak RSS 必须计入最终摘要。
- 提交预算：`0`。
- 预注册时禁止事项：审计阶段不得正式训练；不得读取 v85 中间结果；不得修改 v80、历史目录、实验台账或周期计数；不得因 audit/smoke 输出判断效果。
- 非正式预测访问边界：audit/smoke 不解析 strict v80 OOF/test 数组；来源合同只对文件字节做流式哈希，并在输出中标记 `HASH_ONLY_BYTES_NOT_PARSED`。

## 冻结 feature block

仅使用每行自身的原始字段，不使用标签、全局统计或 train/test 拟合态：

1. `infra_charging_total = Charging_Stations_Near_Home + Charging_Stations_Near_Work`
2. `infra_charging_endpoint_floor = min(Charging_Stations_Near_Home, Charging_Stations_Near_Work)`
3. `infra_commute_km_per_charger = Daily_Commute_km / (1 + infra_charging_total)`
4. `infra_no_home_commute_burden = infra_commute_km_per_charger * I(Home_Charging_Possible == "No")`

列序 SHA-256 为 `95c64c7b6c60458a2197e36b60df9f6faefdcad5baa4cfd9b5ab4b2feae831da`。v80 static `62` 列 + 本块 `4` 列 + 原有 `51` 个 TE 列 = `117` 列。

## 工程合同

- [x] v80 `COMPLETE`、OOF、参数、17 个 TE key、smooths、strict prior、inner/model seeds 与 LightGBM 版本逐项校验
- [x] feature block 原始列、非空、有限值、非负数值、列序、宽度和标签不变性校验
- [x] 每折 checkpoint，绑定 runner/config/input 哈希与 validation index 哈希，安全恢复
- [x] 内核 `flock` 单实例；取得锁后再次检查 `COMPLETE`
- [x] 每 5 折一行 `INTERIM_DIAGNOSTIC_NOT_FINAL` 汇总
- [x] 60 分钟/16 GiB 硬停；超限原子写 `FAILED`，第 40 折 checkpoint 也保留
- [x] staged 结果完整 verify 后才可原子标记 `COMPLETE`；verify 时间/RSS 纳入最终硬停，任何超限都不能留下 `COMPLETE`
- [x] 两类 `FAILED` 统一最小 schema、资源摘要和 expected/present/missing 清单；现存 checkpoint/输出明确 `invalid_for_use`，支持独立失败关闭验证
- [x] formal 主体统一捕获普通异常；包括 staged verify 异常在内都在原 flock 释放前原子写 `FAILED_EXCEPTION`，不遗留伪 `COMPLETE`、未关闭状态或第二实例竞态窗口
- [x] formal v80 预测绑定 sources SHA、train/test ID 行身份、OOF/test 路径/字节/哈希及 cv artifact SHA；任一不一致 fail closed
- [x] `verify` 从 40 个 checkpoint 逐元素重建 OOF/test，复算逐折及整体 AUC、Spearman、10 折止损、项目门槛、权限和所有产物哈希
- [x] 默认 `audit`；`smoke` 不调用 `model.fit`，两者均不解析真实预测数组；5 项 pytest 仅使用合成产物测试边界

## 运行方式

```bash
python model/v87_strict_v80_commute_charging_burden_40f/v87_strict_v80_commute_charging_burden_40f.py --mode audit
python model/v87_strict_v80_commute_charging_burden_40f/v87_strict_v80_commute_charging_burden_40f.py --mode smoke

# 正式训练已经完成，不得用相同配置重复计数：
python model/v87_strict_v80_commute_charging_burden_40f/v87_strict_v80_commute_charging_burden_40f.py --mode train

# 仅在完整正式运行后：
python model/v87_strict_v80_commute_charging_burden_40f/v87_strict_v80_commute_charging_burden_40f.py --mode verify
```

## 当前结果与决策

- 运行状态：`COMPLETE`；显式 verify 与独立终审均 `PASS`
- 整体 OOF / delta / 逐桶胜出：`0.9462357606221546` / `-0.000004850354209` / `23/40`
- 与 v80 的 OOF/test Spearman：`0.998339024217` / `0.999905056478`
- 运行耗时与资源：`1548.930169` 秒 / peak RSS `4.430999756 GiB`
- 正式产物：40 个 checkpoint、OOF/test、submission、`cv_results.json`、`sources.json`；OOF/test 均由 checkpoint 独立逐元素重建一致
- 决策：`ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_ONLY`
- 是否允许当前产物直接进入融合：否；必须另立预注册并相对当时最佳严格基准满足 `+0.0001` 与 `5/5`
- 是否允许提交：否
- 周期计数：C01 第 9 个正式关闭项，`9/20`；ME-C01 仍为 `NOT_DUE`
