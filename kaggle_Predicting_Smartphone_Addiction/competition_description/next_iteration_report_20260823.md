# S6E8 深度复盘与下一轮迭代报告（2026-08-23）

## 结论先行

当前问题已经不是“再换一组 GBDT 参数”，而是三个更基础的问题：

1. 比赛数据是从 7,500 行合成源再次生成的平滑概率场，不能把源数据的硬规则或
   原始标签直接拼回训练集。
2. 有效信号主要来自屏幕时间预算约束、0.01 离散格点和单列精确值条件概率；显式
   缺失特征主要识别 train/test，而不是目标。
3. 现有 11 个预测高度同质，v18 的全模型 stacking 没有创造新信息。下一阶段要么
   引入真正不同且足够强的模型视角，要么只做有稳定证据的小幅残差校正。

本轮已实现并验证两个实验：

- v19 clean-ID XGBoost：修复 v13 把 `id` 入模的问题。clean 单模小幅提升，放回
  v17 后本地几乎没有增益；后续按用户要求提交，Public LB `0.96981`。
- v20 负向 v1 corrector：固定 `1.075*v17 - 0.075*v1`，OOF 提升
  `+0.000135`，5/5 折提升，按 test 缺失模式重加权后仍提升约 `+0.00013`；
  Public LB `0.96998`，成为当前 best。

## 1. 比赛背景与生成机制

官方说明本赛为合成表格二分类，指标是 ROC AUC。AUC 只关心排序，因此最后一公里
的重点不是概率校准，而是能否进一步逼近每行真实的条件正类概率顺序。

官方最初引用的源数据已经不可下载；论坛定位到的高可信镜像是
[Smartphone Usage and Addiction Prediction](https://www.kaggle.com/datasets/jayjoshi37/smartphone-usage-and-addiction-prediction)。
本地通过 Kaggle CLI 核验为 7,500 行、16 列。它本身仍是人为合成数据，并非真实
用户调查。

该镜像的目标接近两条硬规则：

- `daily_screen_time_hours > 8` 或 `social_media_hours > 4` 时恒为 1；
- `daily <= 6` 且 `social <= 4` 时恒为 0；
- 中间 1,025 行近似随机标签。

两条规则在源数据上的 AUC 为 `0.98880`，但在比赛 train 上仅为 `0.83526`。源数据
高区、低区、中区的条件概率已被 Kaggle 二次生成器平滑和扭曲，直接把 7,500 行
加入 691,369 行比赛训练集既只有 1.08% 体量，又会系统性拉错边界。论坛的公开
消融也报告直接拼接约回退 `0.00008~0.0001`。相关讨论：

- [Generation model of the missing original dataset](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/732428)
- [The generator turned a hard rule into a smooth field](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/732434)

因此源数据只用于理解生成器，不作为扩样数据。

## 2. 数据中真正可利用的结构

### 2.1 离散格点与精确值支持

九个数值字段几乎全部落在 0.01 网格，train/test 的单列精确值支持高度重合。源数据
值在比赛非缺失行中的覆盖率大多为 93%~100%，但 train/test 没有可规模利用的整行
精确重复。这说明：

- 整行近邻抄标签无效；
- 单列 exact-value、rounding、digit 和低维 pair lattice 编码有效；
- v3 把数值同时作为连续值和精确字符串类别，是目前最关键的单模跃升。

本地严格折外诊断中，单列 exact TE 的 OOF AUC 为：daily `0.87758`、weekend
`0.86526`、social `0.82402`；0.1 网格的 daily+social 二维 TE 达到 `0.91179`。

### 2.2 时间预算约束

比赛 train+test 满足屏幕组成预算结构，`other_screen`、component sum、observed count
等特征能够把斜向约束显式交给轴对齐树。v2 在完全同折、同参数下 OOF
`+0.000926`，且 5/5 折提升；这是当前最可信的 FE 消融。

### 2.3 缺失不是目标信号

本地 adversarial validation：

- 仅使用 12 位缺失模式的 Logistic AUC：`0.565237`；
- raw LightGBM adversarial AUC：`0.564938`；
- `missing_count` 对目标的 AUC：`0.501717`。

也就是说 train/test 漂移几乎都来自缺失注入，但缺失对目标接近随机。显式
`missing_count` 或缺失 flags 可能提高同分布 OOF，却会强化 split identity。论坛已有
“本地 `+0.00009`、Public 反而下降”的配对结果：

- [LightGBM Gain Importance: What the Model Actually Cares About](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/732256)
- [Feature Engineering: What Works, What Fails](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/733541)

## 3. 过往模型过程与得分

| 阶段 | 代表版本 | OOF AUC | Public LB | 结论 |
| --- | --- | ---: | ---: | --- |
| 原始树基线 | v1 LGBM | 0.962633 | 0.96383 | 容量基线 |
| 预算 FE | v2 LGBM | 0.963559 | 0.96467 | 干净且稳定的 FE 增益 |
| 精确值双通道 | v3 CatBoost | 0.967965 | 0.96946 | 最大单模跃升 |
| 多种子降方差 | v7 CatBoost bag | 0.968132 | 未单交 | 小幅增益，相关性仍极高 |
| 定向三模型融合 | v8 | 0.968358 | 0.96954 | v7/v6/v2 互补有效 |
| 异构 XGB 校正 | v12 | 0.968457 | 0.96959 | rank 小权重增益 |
| 全量融合 | v14 | 无可信统一 OOF | 0.96861~0.96872 | 模型越多反而越差 |
| 两模型定向融合 | v17 | 0.968657 | **0.96977** | 本轮前线上 best |
| 11 模型 Logistic stack | v18 | 0.968336 | 0.96938 | OOF 与线上均回退 |
| clean-ID 消融 | v19 | clean XGB 0.966471 | 0.96981 | ID 不是 v17 增益主因；线上略高于 v17 |
| 负向残差校正 | v20 | **0.968793** | **0.96998** | 新 best；ref `55719089` |

完整分数、参数、ref 和依赖关系以 `model/experiments.md` 为准。

## 4. 论坛中最有意义的方案

### 4.1 精确值 TE / FE 必须真正折外

公开消融显示，对所有列做 exact target/frequency encoding、保留原始 NaN 列、增加
预算约束和小数格点，是强 GBDT 的主要增益来源。Target Encoding 必须位于外层 CV
内部；先在全数据生成 OOF TE、再做外层 CV 会让验证折标签进入训练特征。泄漏案例：
[Decoding the Synthetic Generator](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/734063)。

### 4.2 Lookup-Transformer 是最值得新增的模型视角

[Lookup-Transformer + Insights](https://www.kaggle.com/code/tamerlanomralinov/s6e8-lookup-transformer-insights-lb-0-97041)
把每个精确值映射为 embedding，并在 feature token 间做 attention。统一五折复训中单模
OOF 约 `0.96853`，与其他成员最大相关性约 `0.9869`，单独给融合带来约
`+0.000109`。它同时满足“足够强”和“足够不同”，价值高于继续增加树模型 seed。

### 4.3 多样性比单模分数更重要，但存在强度门槛

[Diversity Beats Strength](https://www.kaggle.com/code/adarsh1077/s6e8-diversity-beats-strength)
在统一 OOF 库中发现：去掉 TE 的 XGB/LGB/Cat 三种视角、以及 OOF 只有 `0.95891`
的 Logistic，能获得比多个更强 seed twin 更高的元模型权重。同模型不同 seed 几乎
无新增信息；弱但不同的模型常以负系数作为误差校正。

但低相关不等于一定有用：OOF 只有约 0.961 的神经网络仍太弱。合理门槛约为单模
OOF `0.966~0.967`，之后再比较与核心模型的 rank correlation 和 leave-one-out
stack delta。

### 4.4 stacking 的正确姿势与风险

[Honest OOF Blend](https://www.kaggle.com/code/szymonkapiski/s6e8-honest-oof-blend)
和大型统一实验支持标准化 logit/rank-gauss + L2 Logistic；等权 rank 在饱和模型池中
明显更差。

需要保留一个方法学 caveat：把既有一级 OOF 再切五折训练二层模型，不等于端到端
nested stacking。元训练行的一些一级预测来自看过当前元验证折标签的一级模型。
真正严格的评估需要在每个外层折内重新生成一级训练 OOF 和外层验证预测。v18 未
达到这个纯度，因此不能仅凭新的 meta OOF 自动替代 v17。

### 4.5 排除公开榜假象

- [Where does the 0.97101 NN score really come from?](https://www.kaggle.com/competitions/playground-series-s6e8/discussion/735404)：所谓 NN 权重只有 `1e-6`，分数实际来自外部公开提交。
- [Why Every S6E8 Notebook Above 0.97110 Overfits](https://www.kaggle.com/code/raykkretzschmar/why-every-s6e8-notebook-above-0-97110-overfits)：Public 偏好的修正方向与 honest OOF 相反，不适合作为 Private 选择。

## 5. 本轮实现与验证

### v19：clean-ID XGBoost

审计发现 v13 只删除目标，没有删除 `id`。test ID 全部在 train ID 最大值之外，树
模型对 ID 的外推没有统计依据。本轮完全复用 v13 FE、参数、seed 和 folds，只删除
`id`：

| 比较 | dirty | clean | clean-dirty |
| --- | ---: | ---: | ---: |
| v13 XGB 单模 OOF | 0.966428 | 0.966471 | +0.000042 |
| 固定 v17 权重 OOF | 0.968657 | 0.968658 | +0.0000017 |

clean 单模 4/5 折提升，但 clean v17 仅 2/5 折提升，未通过原融合提交门槛。后续按
用户要求提交固定权重候选，Public LB `0.96981`、ref `55719364`，比 v17 高
`0.00004`，但低于 v20 `0.00017`。结论是：v17 的小幅互补并非主要由 ID 造成；
以后模型仍永久删除 ID。

### v20：负向 v1 residual corrector

固定公式：

```text
corrected = 1.075 * v17 - 0.075 * v1
```

测试侧最后只做全局 percentile rank，避免两个轻微负值被 clipping 成并列。验证：

| 口径 | v17 | v20 | 增益 |
| --- | ---: | ---: | ---: |
| deploy-aligned OOF | 0.968657 | 0.968793 | +0.000135 |
| 缺失模式加权，alpha=1 | 0.969446 | 0.969575 | +0.000129 |
| 缺失模式加权，alpha=10 | 0.969041 | 0.969170 | +0.000130 |
| 缺失模式加权，alpha=100 | 0.968001 | 0.968132 | +0.000130 |

五个固定折增益为 `+0.000132 / +0.000170 / +0.000127 / +0.000110 /
+0.000141`。该方案没有训练二层模型、没有下载别人的提交，也没有混入新的标签
统计；它仍使用历史 OOF 选择方向，因此定位为一次低成本线上验证候选，而不是
端到端 nested 结果。

Kaggle 提交 ref `55719089`，Public LB `0.96998`，相对 v17 的 `0.96977` 提升
`+0.00021`，线上方向与本地三层验证一致。

## 6. 下一步优先级

1. **严格折外 exact/lattice TE XGBoost 或 CatBoost**
   - 永久删除 ID 和显式 missing_count；
   - 原始数值与精确值副本并存；
   - train+test 联合 frequency encoding 仅使用无标签计数；
   - exact 值、0.1 格点、daily-social / social-weekend pair TE 在每个外层折内部生成；
   - 先完成单块消融，再进入融合。
2. **统一五折复训 Lookup-Transformer**
   - 使用当前项目 seed=42 和原始行序；
   - 输出带 fold manifest 的 OOF/test；
   - 单模强度和相关性同时过门槛后才进栈。
3. **端到端 nested stacking**
   - 每个外层折内重新训练一级模型；
   - 只纳入 3~5 个强且不同的视角；
   - 比较 standardized-logit 与 rank-gauss L2 Logistic；
   - v17/v20 始终作为受保护线上基准。

明确停止：直接拼原始 7,500 行、伪标签、missing_count、更多同模型 seed、无 OOF
来源的公开提交混合、继续扩大相似 GBDT 的等权池。
