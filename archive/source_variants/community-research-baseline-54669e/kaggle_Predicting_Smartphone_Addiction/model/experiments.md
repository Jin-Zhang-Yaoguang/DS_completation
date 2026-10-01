# 实验记录 — Predicting Smartphone Addiction (S6E8)

- **指标**：ROC AUC，越高越好。
- **每日提交上限**：10 次。
- **截止时间**：2026-08-31 23:59 UTC / 2026-09-01 07:59 台北时间。
- **当前状态**：已完成四次提交；当前最佳为 v8，Public LB `0.96954`。

## 实验台账

| # | 方案 | 特征 | 模型/关键参数 | 本地 OOF AUC | 线上 Public | 提交 ref | 备注 |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 1 | v1_baseline_lgbm | 原始 12 特征；类别 one-hot | LightGBM 31 leaves × 1500 trees；5 折 StratifiedKFold | 0.962633 | 0.96383 | 55575008 | 首个端到端基线；状态 COMPLETE |
| 2 | v2_budget_lgbm | v1 + 组成时长总和、剩余屏幕时长、组成观察数 | 同 v1，严格同折配对 | **0.963559** | **0.96467** | 55575810 | OOF `+0.000926`；5/5 折提升；Public `+0.00084` |
| 3 | v3_dual_catboost | 连续数值 + 12 个精确值字符串类别 + v2 时间预算 | CatBoost depth 8，最多 3000 轮，5 折早停 | **0.967965** | **0.96946** | 55576614 | OOF `+0.004407`；5/5 折提升；Public `+0.00479` |
| 4 | v4_blend_lgbm_catboost | v2/v3 percentile rank | 留一折选权重；最终 0.12/0.88 | 0.968055 | — | 未提交 | 相对 v3 `+0.000089`，低于预注册 `+0.0001` 门槛 |
| 5 | v5_hierarchical_lookup | 精确值 → 分位区间 → 全局先验；严格内层 OOF | 经验贝叶斯平滑 + Logistic Regression | 0.958196 | — | 未提交 | 纯加性模型不足；v8 五折均给零权重 |
| 6 | v6_highres_lgbm | v2 + v5 折外层级编码 | LightGBM 63 leaves，`max_bin=1023`，5 折早停 | 0.967373 | — | 未单独提交 | 单模低于 v3 `0.000593`，但为融合提供互补性 |
| 7 | v7_catboost_bagging | v3 双表示 | CatBoost seed 42/2026 概率平均 | 0.968132 | — | 未单独提交 | 相对 v3 `+0.000167`；种子秩相关 `0.998242` |
| 8 | v8_three_model_blend | v7/v6/v2 percentile rank | 交叉拟合贪心三模型；权重 0.6608/0.2832/0.0560 | **0.968358** | **0.96954** | 55577566 | 五折全部提升；相对 v7 `+0.000226`；Public 相对 v3 `+0.00008` |
| 9 | v9_catboost_engineered | 在 v3 的基础上加入时间预算比例与 log 特征 | CatBoost 深度 8，2200 轮，5 折 | 0.963478 | — | 未单独提交 | OOF 明显低于 v3，未进入融合候选 |
| 10 | v10_three_model_blend_plus_v9 | 在 v8 基础上加入 v9 候选的交叉拟合 | rank 融合（门槛 1e-4），5 折重采样 | 0.968358 (fixed) | 0.96954 | 55578920 | 与 v8 完全等价（预测文件哈希一致），无增益 |

## 初始化计划

- [x] 在 Kaggle 接受比赛规则并下载 `train.csv`、`test.csv`、`sample_submission.csv`。
- [x] 核验数据哈希、shape、字段类型、缺失率、目标分布和唯一 ID。
- [x] 建立 LightGBM 首个端到端基线并完成 Kaggle 提交。
- [ ] 补充常数概率和 Logistic Regression 作为低容量 sanity check。
- [x] 固定 5 折 StratifiedKFold 与随机种子，保存每折 AUC 和 OOF 预测。
- [ ] 比较原生缺失处理、折内插补、缺失指示三种策略。
- [ ] 做 train/test adversarial validation，识别合成数据分布偏移。
- [x] 对时间预算结构残差做同折消融，并确认 5/5 折提升。
- [x] 对浮点精度与精确值查表特征做独立消融。
- [x] 用 CatBoost 连续值/精确值双重表示验证 value-level 信号。
- [x] 评估 v2/v3 的 cross-fitted rank blend，并按预注册门槛决定不提交。
- [x] 用严格内层 OOF 验证层级查表，并排除 leave-one-out + 频次的隐蔽泄漏。
- [x] 训练高分辨率 LightGBM 与 CatBoost 双种子袋装。
- [x] 交叉拟合三模型权重，并仅在五折一致增益后提交 v8。
- [x] 只有在 OOF 稳定增益后才生成线上提交。

## 验证与防泄漏约定

1. `id` 默认不入模；任何 ID/行序特征都必须先证明不是生成顺序泄漏。
2. 编码器、插补器、缩放器和目标统计只能在训练折拟合。
3. 以概率计算 ROC AUC，不用 `accuracy` 代替比赛指标。
4. 每次提交必须能追溯到同目录的代码、参数和本地 OOF 结果。
5. 公开榜只用于外部校验，不以多次试探替代交叉验证。
