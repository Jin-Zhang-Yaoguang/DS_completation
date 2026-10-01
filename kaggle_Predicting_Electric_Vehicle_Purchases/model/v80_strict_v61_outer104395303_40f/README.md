# v80_strict_v61_outer104395303_40f

## Preflight revision

- `R2 / 2026-09-03`：在仍无正式产物状态下完成最后预算修订；不构成版本计数或效果证据。
- 60分钟预算改为自取得 `flock` 后开始的单调墙钟；每折前、每折后（明确包括第40折）、全部折结束后及写 COMPLETE 前均检查。
- 新增进程 peak RSS 记录及16 GiB硬门槛。使用 `resource.getrusage(RUSAGE_SELF).ru_maxrss`；macOS原生值按 bytes，其他受支持 Unix 按 KiB 转为 bytes。
- 任一墙钟或 peak RSS 超限均原子写 `FAILED` 后停止，不进入 COMPLETE；若第40折训练完成后才超限，其 checkpoint 仍保留，且已存在的部分产物明确标记为不可使用。
- `R1 / 2026-09-03`：在无正式产物状态下修订；不构成版本计数或效果证据。
- `verify_complete` 现在从40个 checkpoint 重建后复算并核对 strict gate、decision、融合/提交权限、fold AUC mean/std、best iterations和OOF/test Spearman。
- 正式 runner 在取得 `flock` 后再次检查 `cv_results.json`；若另一实例已完成，只校验并返回。
- audit 显式要求当前 LightGBM 版本等于历史 v61 `cv_results.json` 的 `4.6.0`。
- 下方 runner/config SHA 已更新为本次 revision 的冻结值。

## 前置裁决

- `v79_v61_split7_40f` 状态：`DESIGN_REJECTED_NOT_COUNTED`。
- 原因：v79 沿用了 v6 的 `encode_key`。其 inner hold 映射虽然扣除了 hold 的类别计数和目标和，但 smoothing prior 仍取完整 outer-fit 的 `y_fit.mean()`，间接使用了当前 inner hold 标签，不符合冻结的严格交叉拟合边界。
- 处置：v79 不修改、不运行、不计入 C01。本目录是独立新实验，不导入或调用 v79。
- 历史 v61 存在同一 prior 边界问题。其 `0.9462435667072661` 只作历史数值参考，不称为严格诚实 OOF，也不作为 v80 的无偏强度基准。

## 预注册

- 实验 ID：`v80_strict_v61_outer104395303_40f`
- 研究周期：`C01`
- 实验类型：`SINGLE_MODEL`
- 是否计入本周期 20 个普通版本：完整40折后正式关闭为 `COMPLETE` 或保留完整失败证据为 `FAILED` 时才计数；当前不计数
- 周期内序号：`1`
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-03
- 候选代码 SHA-256：`808e4fe41ef033da6b6df14edcce3e9f67ced418f9958fddbd0788045af8204a`
- 冻结配置 SHA-256：`79fc1e5451fb823cbde5a59e32b078e8e85cc0ebcef4c500694affab9195e5ab`
- 假设：修复 inner prior 的标签边界后，可以得到与 v61 同外层划分、同特征和同模型设置的首个严格 v61-family 基线。
- 机制依据：TE 的 inner hold 行不能通过全 outer-fit prior 看见自身标签；否则训练特征存在轻微目标泄漏，历史 OOF 的证据等级必须降级。
- 历史参考及 OOF：`v61_income_bin10_te_lgbm_40f_depth4_seed104395303`，`0.9462435667072661`，证据状态为 `NON_STRICT_INNER_PRIOR_NOT_AN_HONEST_BASELINE`。
- 唯一主要变量：inner hold 的 smoothing prior 从完整 outer-fit 均值改为该 hold 对应 inner-train 的标签均值。
- 保持不变的设置：outer seed、inner splitter seed序列、四个 LightGBM seed、全部模型参数、40 outer folds、5 inner folds、17个 TE key、smooths `[5,15,80]`、静态特征、数据及行序均与 v61 配方一致。
- 外层/内层切分：outer 为40折 `StratifiedKFold(shuffle=True, random_state=104395303)`；one-based outer fold 的 inner seed 为 `104395303 + fold`。
- 泄漏边界：inner hold 的 prior、count、target sum均仅来自 inner-train；outer-valid和test的 prior及统计来自完整 outer-fit；train+test 联合统计仅限无标签频次与取值编码。
- 主要指标：完整严格 OOF ROC AUC。
- 逐折判定方式：v80与v61使用相同 outer validation rows，可以报告逐折差异；由于 v61 训练侧 prior 非严格，这些差异只量化修复影响，不能解释为对严格诚实基准的模型提升。
- 预期提升：不预注册方向性分数提升；预期产出是泄漏边界正确的基线。任何分数变化必须原样报告。
- 晋级门槛：首先通过40折 checkpoint 重建、严格 prior 自检、行序/概率/哈希全校验；OOF `>=0.9458` 时可作为 strict v61-family 候选，是否进入融合需以后续严格小融合单独验证。相对历史 v61 的差值不构成强度晋级证据。
- 计算预算：40折，LightGBM `n_jobs=8`；单次正式进程自取得 `flock` 至 COMPLETE 前检查的墙钟不达到3600秒，进程 peak RSS 不超过16 GiB。每折前后均检查，第40折不例外。
- 提交预算：`0`。
- 停止条件：任何 prior 自检、配置/来源哈希、checkpoint 索引、重建预测、行序或概率校验失败；达到计算预算；禁止通过恢复或改配置掩盖失败。

## 实现检查

- [x] 只新增 v80 目录，未修改历史实验
- [x] v80 不导入、不调用 v79
- [x] inner hold prior仅使用 inner-train 标签
- [x] outer-valid/test prior仅使用完整 outer-fit标签
- [x] outer、inner、四个模型随机源分别显式记录
- [x] 配置逐项对照历史 v61 参数与特征合同
- [x] 每折 checkpoint 含配置、代码/输入合同及 validation index哈希
- [x] 使用内核 `flock` 保证单实例，不删除锁文件，不存在 stale-lock unlink TOCTOU
- [x] 每5折输出带 `INTERIM_DIAGNOSTIC_NOT_FINAL` 标记的汇总
- [x] 每折前后（含第40折）、全部折后及 COMPLETE 前记录单调墙钟与进程 peak RSS
- [x] 墙钟/peak RSS超限时原子写 FAILED；第40折后超限不会落 COMPLETE，checkpoint 保留
- [x] `verify` 从40个 checkpoint逐元素重建 OOF/test，并逐折复算 AUC
- [x] 默认只读 audit；smoke不拟合模型、不计算效果指标、不写正式产物

## 运行方式

```bash
python model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py --mode audit
python model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py --mode smoke

# 本次实现任务禁止执行：
python model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py --mode train

# 仅在正式40折完成后使用：
python model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py --mode verify
```

正式运行应使用已安装 LightGBM 4.6.0 的解释器；当前 shell 的 `python` 为 `/opt/anaconda3/bin/python`。共享父目录 `.venv/bin/python` 没有 LightGBM。

## 结果

- 运行状态：未运行
- 整体 OOF：—
- 历史 v61 参考 OOF：`0.9462435667072661`，非严格诚实基准
- 差值：—，只量化 prior 修复影响
- 提升折数：—
- 与历史 v61 的 OOF/test Spearman：—
- 运行耗时与资源：—
- 产物 SHA-256：—
- 异常或偏离预注册：无

## 失败归因

- 主因：—
- 证据：—
- 是否存在新的可证伪假设：—

## 决策

- 决策：待完整40折后填写
- 是否达到预注册门槛：待定
- 是否允许进入融合：否，需后续严格小融合验证
- 是否允许提交：否
- 完成后的周期计数：当前仍为 `0/20`
- 是否触发超级大融合：否
- 下一步及理由：仅在正式运行获准后启动同一 runner；完成前不更新台账或周期计数。
