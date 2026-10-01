# v79_v61_split7_40f

## 预注册

- 实验 ID：`v79_v61_split7_40f`
- 研究周期：`C01`
- 实验类型：`ROBUSTNESS`
- 是否计入本周期 20 个普通版本：`true`，但只有正式 40 折完成并作出最终决策后才计数
- 周期内序号：`1`
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-03
- 候选代码 SHA-256：`13ee485e7cd6ebdd75036e0eb3a9373b771b2a899f642b988764ff819096b770`
- 冻结配置 SHA-256：`61f5799a2db6f4c58e63382a0043d8941c8ac0c7c9bec17a405571781ffbc2a1`
- 假设：仅改变 v61 的外层切分种子不会改变 OOF 期望，同时能为 P2-04 提供一份独立的测试侧折平均预测。
- 机制依据：v61 实际将 outer split、inner TE 与模型 seed 同时设为 `104395303`。本实验只隔离外层划分方差，避免把 TE 或模型随机性混入结论。
- 基准版本与 OOF：`v61_income_bin10_te_lgbm_40f_depth4_seed104395303`，OOF `0.9462435667072661`。
- 唯一主要变量：outer `StratifiedKFold` 的 `random_state: 104395303 -> 7`。
- 保持不变的设置：数据、行序、v29/v6 收入 bin10 多尺度嵌套 TE、40 折、5 inner folds、smooths `[5,15,80]`、62 static + 51 TE、LightGBM 全部参数、early stopping 500、inner TE seed base 与四个 LightGBM seed 均保持 `104395303`。
- 外层/内层切分：outer 为 40 折 `StratifiedKFold(shuffle=True, random_state=7)`；每个 one-based outer fold 的 inner seed 为 `104395303 + fold`。
- 泄漏边界：外层训练折用 inner 5-fold OOF TE；外层验证和测试只使用外层训练标签统计。train+test 联合出现的统计只有无标签频次与取值编码。
- 主要指标：整体 OOF ROC AUC。
- 逐折判定方式：seed7 的40个 validation bucket 报告候选和 v61 在相同行桶上的 AUC，但因两者训练折不同，只作诊断，不声称逐折配对。
- 晋级门槛：`abs(v79 OOF - v61 OOF) < 0.0001` 且 v79/v61 test Spearman `>= 0.998`；通过后仅允许进入 P2-04 split-bag，不自动取得提交资格。
- 计算预算：40 折；LightGBM `n_jobs=8`；墙钟时间不超过60分钟；内存不超过16 GB。
- 提交预算：`0`。
- 停止条件：配置或来源哈希改变；checkpoint 索引/合同不一致；数据或产物校验失败；超预算；完整结果未过稳定性门槛则停止 split-bag 分支并先归因。

## 实现检查

- [x] 未修改历史实验目录
- [x] outer、inner TE、模型随机种子分别显式记录
- [x] 折数、线程、特征与 LightGBM 参数写入 `frozen_config.json`
- [x] 目标编码保持 v61 的严格嵌套边界
- [x] 测试集只参与无标签统计
- [x] runner 校验 OOF/test 行序、长度、有限值、概率范围及提交 ID
- [x] 每折原子 checkpoint，包含冻结配置哈希、代码/输入合同哈希、fold index 哈希
- [x] 每5折向 stdout、`train_log.txt`、`progress.jsonl` 写可观测汇总
- [x] 默认模式为只读 `audit`；正式训练必须显式 `--mode train`
- [x] smoke 不拟合模型、不计算效果指标、不写正式实验产物

## 运行方式

```bash
# 只读合同检查（默认）
python model/v79_v61_split7_40f/v79_v61_split7_40f.py --mode audit

# 无模型拟合 smoke：验证特征、嵌套 TE 与 checkpoint roundtrip
python model/v79_v61_split7_40f/v79_v61_split7_40f.py --mode smoke

# 正式训练；本次实现任务禁止执行
python model/v79_v61_split7_40f/v79_v61_split7_40f.py --mode train

# 正式完成后的独立全产物校验
python model/v79_v61_split7_40f/v79_v61_split7_40f.py --mode verify
```

建议正式运行时不要依赖 shell `tee`；runner 自身写入 `train_log.txt`。中断后使用完全相同的 `--mode train` 恢复，配置、代码或输入哈希不一致时会拒绝读取已有 checkpoint。

## 结果

- 运行状态：未运行
- 整体 OOF：—
- 基准 OOF：`0.9462435667072661`
- 增量：—
- 提升折数：—
- 重复切分结果：—
- 与关键成员的 OOF/test Spearman：—
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
- 是否允许进入融合：否，待定
- 是否允许提交：否
- 完成后的周期计数：仍为 `0/20`
- 是否触发超级大融合：否
- 下一步及理由：仅在正式运行授权后执行同一 runner；完成前不得更新台账或周期计数。
