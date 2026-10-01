# v84_strict_v80_original_supervision_40f

## Preflight revision

- `R0 / 2026-09-04`：候选只完成预注册、数据审计、runner 实现与 smoke；未启动 EV 模型训练，未生成任何正式效果证据，不更新台账或周期计数。
- 候选代码 SHA-256：`80619a26f2ea3d1c867944048880ce805b4052e253c9d58a4f93646c77613911`
- 冻结配置 SHA-256：`d696059ba9d1f338f4de2504adc21551ebf646bbe5f707b2614a1c4adc0df5be`

## 预注册

- 实验 ID：`v84_strict_v80_original_supervision_40f`
- 研究周期：`C01`；预留顺序为第5个普通版本候选。只有正式运行后以 `COMPLETE` 或保留充分证据的 `FAILED` 关闭，才计入周期；当前不计数。
- 实验类型：`SINGLE_MODEL`
- 状态：`DESIGN_READY_NOT_STARTED`
- matched control：已完成且可重建的 `v80_strict_v61_outer104395303_40f`，严格 OOF `0.946240610976364`。
- formal trigger：`v80` 必须保持 `COMPLETE`，其 OOF、test、配置、runner 与 `cv_results.json` 全部进入 v84 运行合同哈希；不满足即拒绝运行。
- 机制假设：少量 original 真实标签可能补充 synthetic 生成分布未充分表达的监督信号；只有在 synthetic validation 和 TE 标签边界完全不变时，这个假设才可被 matched OOF 证伪。
- 唯一主要变量：每个 outer fit 在 synthetic outer-train 后追加清洗后的 original 带标签行，所有行权重固定为 `1.0`。
- 保持不变：outer seed `104395303`、inner seed base `104395303`、四个 LightGBM seed `104395303`、40 outer folds、5 inner folds、62个静态特征、17个 key × 3 smooth = 51个 TE、113总特征、全部 LightGBM 参数和早停设置均与 v80 一致。
- 禁止项：不加 source flag；不调 original 权重；不改特征、模型参数、seeds 或 folds；不得依据 source classifier/PSI 调整候选；不得让 original 标签进入任一 TE prior/count/target-sum；validation 不得混入 original。

## Original 数据边界

- 文件：`data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv`。
- schema 解析：比赛 synthetic 非标签列看似14列，但其中一列是 `id`；original 的对应额外列是另一命名空间的 `Buyer_ID`。两种 ID 只检查唯一、非空且明确不入模，也不进入重复键。
- 精确去重键：v80 实际建模的13个共享原始特征；original 逐行与 `synthetic train ∪ test` 做全列精确相等判断。
- 预检结果：original 原始 `10000` 行；与 synthetic train/test 完全重复 `0` 行；清洗后 `10000` 行；共享特征内部也无重复键。
- 标签映射：`Yes → 1`、`No → 0`；清洗后 `Yes=1750`、`No=8250`。
- 缺失：`Annual_Income_USD=178`、`Daily_Commute_km=181`、`Environmental_Concern_Level=184`。LightGBM 只在 original 原始数值列接收这些 NaN；数字位以 v80 既有规则填0，synthetic 拟合的频次未知值填0，TE 未见 key 回退到 synthetic outer-fit prior。
- 无标签静态变换：categorical code、频次和 key code 仍只由 synthetic train+test 拟合，再应用到 original；original 不改变 v80 的联合协变量统计。
- TE：inner hold 的 prior/count/sum 只来自对应 synthetic inner-train；outer-valid、test、original 的映射只由完整 synthetic outer-fit 标签拟合。original 标签只进入最终 LightGBM fit，不进入51个 TE 映射。
- validation：永远只使用 synthetic outer-valid；因此与 v80 的40组 validation row 完全一致，可逐折 matched 比较。

## 只读分布诊断

- 固定 source classifier：从 synthetic train 以 seed `104395303` 抽取10000行，与10000行 cleaned original 平衡；5折固定预处理和固定 `HistGradientBoostingClassifier`，无调参。OOF AUC `0.76491627`，逐折 `[0.7625425, 0.760707625, 0.7682215, 0.770331125, 0.76459475]`。
- PSI 仅提示分布差异，不参与特征、权重、参数、门槛或是否运行的选择。最大项：`Daily_Commute_km=0.37062411`；其次 `Annual_Income_USD=0.24205054`、`Environmental_Concern_Level=0.18287494`；13列均值约 `0.07936658`。
- 证据等级：`PREFLIGHT_DIAGNOSTIC_NOT_MODEL_EVIDENCE`。来源可分并不证明 original 标签监督有效，也不允许据此调权。

## 验收与停止

- 主指标：完整40折 synthetic OOF ROC AUC。
- 晋级门槛必须同时满足：`OOF(v84) - OOF(v80) >= 0.0001`；且在相同 validation rows 上至少 `24/40` 折 AUC 严格高于 v80。
- 达标决策：`ADVANCE_TO_STRICT_SMALL_FUSION`，仅允许进入后续严格小融合；提交预算仍为0。
- 未达标：`STOP`，不得进入融合或提交。
- 10折预注册中停：仅在第10折完整 checkpoint 后，以已覆盖 synthetic OOF rows 做 matched AUC；若 `delta < -0.00005` 且胜出折数 `<=4/10`，原子写 `FAILED / PREREGISTERED_10_FOLD_FUTILITY`，保留10个 checkpoint 并永久停止本候选。等于 `-0.00005` 不触发；胜出5折不触发。
- 资源停止：取得 `flock` 后60分钟墙钟；每折前后（含第40折）、全部折后和 COMPLETE 前检查。进程 peak RSS 硬门槛16 GiB。任一超限原子写 `FAILED`，不得写 COMPLETE，已完成 checkpoint 保留。
- 提交预算：`0`。

## 恢复、校验与可观测性

- 每折一个原子 checkpoint，绑定候选代码、冻结配置、数据、original 文件、v80控制产物和配方的完整运行合同哈希。
- 使用内核 `flock` 防并发；取得锁后再次检查 `cv_results.json`，另一实例若已 COMPLETE 则只 verify 后返回。
- 每5折输出 `INTERIM_DIAGNOSTIC_NOT_FINAL`，同时报告 candidate/control partial OOF、delta、逐折胜数、墙钟和 peak RSS。
- COMPLETE verify 必须从40个 checkpoint 逐元素重建 OOF/test，复算每折 AUC、均值/标准差、best iterations、matched delta、24/40胜数、gate、decision、fusion/submission 权限、OOF/test Spearman、submission、source manifest 和所有哈希。
- audit 的 source classifier 是固定数据诊断训练，不是 EV 目标模型训练；smoke 不拟合任何模型。

## 运行方式

```bash
python model/v84_strict_v80_original_supervision_40f/v84_strict_v80_original_supervision_40f.py --mode audit
python model/v84_strict_v80_original_supervision_40f/v84_strict_v80_original_supervision_40f.py --mode smoke

# 本次实现任务禁止执行：
python model/v84_strict_v80_original_supervision_40f/v84_strict_v80_original_supervision_40f.py --mode train

# 仅在正式40折完成后使用：
python model/v84_strict_v80_original_supervision_40f/v84_strict_v80_original_supervision_40f.py --mode verify
```

## 当前结果

- EV 模型正式训练：未运行。
- OOF/test/submission/checkpoint/sources/cv_results：均未生成。
- audit：通过；只生成终端诊断，不写正式产物。
- smoke：通过；只用临时目录测试 checkpoint、flock、FAILED 原子证据、original apply-only 特征、strict TE 与中停边界。
- 台账、research cycle 和历史目录：未修改。
