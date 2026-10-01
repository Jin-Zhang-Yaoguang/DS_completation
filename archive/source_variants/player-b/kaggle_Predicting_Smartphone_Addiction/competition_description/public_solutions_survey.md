# 公开方案调研 — Predicting Smartphone Addiction（S6E8）

- **调研日期**：2026-08-17
- **调研范围**：Kaggle 官方比赛讨论与公开 Notebook
- **目标**：提取可复现、无标签泄漏且适合本地首个提交的方案线索

## 结论先行

首个提交采用 **原始特征 + LightGBM + 5 折 StratifiedKFold**。核心不是堆叠大量人工特征，而是给模型足够容量：`num_leaves=31`、约 1,500 棵树、数值缺失值直接交给 LightGBM。类别列只做无监督 one-hot 编码，不使用目标编码。

暂不采用以下做法：

- 数值列显式缺失标记：train/test 缺失率系统性不同，可能强化 split identity。
- 大量行为比例和差值：公开消融显示，在足够树容量下没有稳定增益。
- 全局或 CV 外 target encoding：验证集标签会间接进入训练折编码，导致 OOF 泄漏。
- 下载并混合他人的提交文件：无法证明模型自身能力，也不利于私榜稳健性。

## 公开证据与判断

### 1. 模型容量比常规特征工程更重要

[Model capacity was worth 18x my feature engineering](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/734990) 对同一折和种子做配对实验：`num_leaves=15 → 31` 带来约 `+0.0077` CV AUC，而 15 个比例/差值特征只带来约 `+0.0004`；容量提高后，这些人工特征增益归零。公开 Notebook 的全量 5 折参考为 CV `0.9637`、Public LB `0.96487`。

可复现参数线索：

```python
n_estimators=1500
learning_rate=0.03
num_leaves=31
min_child_samples=40
subsample=0.9
subsample_freq=1
colsample_bytree=0.85
reg_lambda=1.0
```

### 2. 需要拟合平滑概率场，而不是硬编码两条规则

[The generator turned a hard rule into a smooth field](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/732434) 指出：原始小数据中的屏幕时长硬规则在合成训练集上只约 `0.835` AUC；合成器把规则边界平滑化，并把信号扩散到多个变量。适合使用能拟合非线性平滑场的 GBDT，而不是手写阈值。

### 3. 缺失模式存在 train/test 偏移

[Feature Engineering: What Works, What Fails](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/733541) 报告 adversarial AUC 约 `0.564`，并指出显式缺失计数可能提升本地 CV 却伤害 Public LB。本地核验也确认 12 个输入字段的 train/test 缺失率均不同。因此 v1 保留 LightGBM 的原生数值缺失处理，但不额外添加数值缺失指示器。

该讨论还报告 `other_screen` 和小数位长度等合成器结构特征可能带来约 `+0.00088`，但这类特征留到 v2 进行严格同折消融，不混入首个基线。

### 4. XGBoost 是后续强单模候选

[XGBoost + Optuna on GPU](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/732985) 报告 Public LB 从 `0.96514` 提升到 `0.96602`，主要线索包括 `screen_time_bin`、`weekend_gap`、`leftover_screen` 与比例特征。当前环境未安装 XGBoost，且首要目标是建立可信的端到端基线，因此放到后续独立方案比较，不能把线上分数当作本地可复现结论。

### 5. 排除两类不可信高分

- [Decoding the Synthetic Generator](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/734063) 的评论确认其 target encoding 在 CV 循环外完成，验证标签泄漏进训练折编码；作者随后也确认修正后分数明显下降。
- [Where does the 0.97101 NN score really come from?](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/735404) 证明所谓 `0.97101` NN 的权重仅 `1e-6`，分数实际来自两个外部公开提交 CSV。该结果不作为模型能力或 baseline 依据。

## v1 Baseline 设计

1. 删除 `id` 和目标，仅使用官方 12 个原始输入字段。
2. 三个类别列以 train/test 联合类别集合做 one-hot；不读取任何测试标签或目标统计。
3. 数值 NaN 原样保留，由 LightGBM 学习缺失方向；不做全局插补。
4. 使用 5 折 `StratifiedKFold(shuffle=True, random_state=42)`。
5. 每折训练相同的 31-leaf LightGBM，记录折 AUC、全量 OOF AUC 与 gain importance。
6. 测试概率取 5 折算术平均；严格校验 ID 顺序、列名、概率范围与有限性后提交。

实际运行结果：OOF AUC `0.962633`，Public LB `0.96383`，提交 ref `55575008`。该结果落在公开方案的合理区间内，且线上/线下方向一致。

## 首轮迭代验证

在与 v1 完全相同的五折和参数下，加入组成时长总和、剩余屏幕时长与组成观察数：

- OOF 从 `0.962633` 提升到 `0.963559`，增益 `+0.000926`；
- 五个配对折全部提升；
- Public LB 从 `0.96383` 提升到 `0.96467`，增益 `+0.00084`。

本地和线上增益高度一致，说明时间预算约束确实补充了轴对齐树不易直接表达的结构，而不是一次排行榜波动。

## 精确值双重表示与融合验证

CatBoost 同时接收连续数值和全部 12 个字段的字符串精确值，并保留时间预算特征：

- OOF `0.967965`，相对 v2 提升 `+0.004407`，5/5 折提升；
- Public LB `0.96946`，相对 v2 提升 `+0.00479`；
- 精确值字段位列特征重要性前列，验证了合成器的 value-level 信号。

v2 与 v3 的 OOF Spearman correlation 为 `0.984420`。防过拟合的留一折权重实验稳定选择 v2 `0.12` / v3 `0.88`，五个 held-out 折均提升，但总体只比 v3 高 `+0.000089`，未达到预注册 `+0.0001` 门槛，因此没有提交融合。

## 第二轮：层级查表、多种子与三模型融合

1. 严格内层 5 折的层级查表 + Logistic Regression 得到 OOF `0.958196`。它验证了精确值信号，但纯加性组合无法替代非线性交互模型。
2. 将同一套层级编码接入 `max_bin=1023` 的 LightGBM，OOF 达到 `0.967373`。单模略低于 v3，但在后续五个 held-out 融合实验中全部被选择。
3. CatBoost seed 42/2026 的概率平均达到 OOF `0.968132`，相对 v3 提升 `+0.000167`；两个种子的秩相关性为 `0.998242`，说明这是小幅降方差而非新信号。
4. 在看到多种子结果前固定三模型选择范围、权重网格和 `+0.0001` 准入门槛。最终 v7/v6/v2 权重为 `0.6608/0.2832/0.0560`，cross-fitted OOF `0.968358`，五个 held-out 折全部提升。
5. v8 Public LB `0.96954`，提交 ref `55577566`；相对 v3 Public 提升 `+0.00008`。线上方向与 OOF 一致，但幅度更小，符合融合边际收益递减。

过程中额外识别出一种隐蔽泄漏：leave-one-out target encoding 与组频次同时输入树模型时，树可从自排除造成的细微差异反推标签。最终 v5/v6 均改为内层 K 折 OOF 编码。

## 后续实验优先级

1. 在完全相同 folds 上比较 XGBoost 与 v8 的预测相关性；只有同时满足单模精度和互补性才进入融合。
2. 对 v6 单独消融 `max_bin` 与层级编码，确认两者各自贡献。
3. 考虑第三个 CatBoost 种子前先做收益/计算成本评估；当前双种子增益仅 `+0.000167`。
4. 只有内层 K 折 target encoding 能进入候选池；全局编码和可反推标签的 leave-one-out 组合一律禁止。
