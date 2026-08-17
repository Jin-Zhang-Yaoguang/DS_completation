# 公开高分方案调研 — Predicting Student Health Risk (S6E7)

> 首次调研：2026-07-03。方法：Kaggle API 拉取本赛题按分数/票数/时间排序的公开 notebook 源码逐一精读。
> 目的：学习方法论（特征、模型、融合），服务于自研方案，不搬运提交。本文档随每日巡视持续更新。

## 更新日志

| 日期 | 动作 | 一句话结论 |
| --- | --- | --- |
| 2026-07-03 | 首次全量调研，精读 10 份 | 确立共识配方：决策校正是第一杠杆、逐值 TE 是第二杠杆、慢/浅/重正则操作点 |
| 2026-07-03 | 巡视：52 候选，新精读 3 份（RepLeafGBM / GRN / cross-family calibration） | 发现表格 NN 多样性包（CV 0.9493~0.9496）；NN 上缺失指示 +0.0025（树上无效）；「多样性 > 单模强度」有了定量证据 |
| 2026-07-03 | 巡视2：52 候选，无新发布；快扫 2 份旧候选（nina2025 CatBoost / kirikiti stacking）确认无新方法论 | 今日无新方案；清单补登 24 条历史候选（消灭模糊通配，保证 diff 幂等） |
| 2026-07-04 | 巡视3：53 候选，24 个新 ref，精读 6 份（amerhu EDA / masayakawamata LogReg stacker / pavloivanin logit blend / NaNs-Are-Features / n0rollback×2） | amerhu 逐特征信号表 + 「缺失集中在最强特征」；LogReg 全成员堆叠 CV 0.95052 与融合天花板一致；公开榜新高 0.95088（仍为提交融合器） |
| 2026-07-04 | 巡视4：50 候选，34 个新 ref，精读 5 份（nybbler 天花板分解 ⭐ / georgymamarin 天花板分析 ⭐ / philippsinger TabPFN-3 / yunsuxiaozi RealMLP / amanatar 融合器） | **两份权威分析独立定量确认天花板 ~0.951–0.952**；机制补全：**stress_level 是独立采样纯噪声**（源数据里与任何特征无联合依赖），故 12% stress 缺失行不可救——这是硬墙的根因；公开榜新高 0.95112（三文件多数投票）；TabPFN-3 基础模型登场但需 GPU |

## 一、公开榜格局

| 分数段 | 构成 |
| --- | --- |
| 0.9511+ | 「提交融合器」：收集多份公开提交做加权投票/多数票（无原创模型，public 过拟合，私榜大概率回吐） |
| 0.9505~0.9508 | 两三个异源模型的概率融合（如 0.6×HGBC栈 + 0.4×RealMLP） |
| 0.9500~0.9505 | **原创单模天花板区**：精调 XGB / HGBC+TE / RealMLP |
| ≤0.948 | 常规 GBDT 基线（我们的 #1~#4 也在此区） |

> **天花板已被社区定量锁定（2026-07-04）**：nybbler 分解 ~0.05 gap = 标签噪声 0.033（硬顶，全特征已知也只到 0.967）+ 缺失 0.026（主要是不可救的 stress）+ 代理恢复 +0.009（step→activity、sleep_quality→sleep，好模型已自动榨取）。**现实天花板 ~0.951，私榜获胜区预计 0.951–0.952**。georgymamarin 佐证：上季 S6E6 私榜前 20 名在公开榜排 149–495 位，冠军公开榜第 343 名——**公开榜排名几乎不携带私榜信息**。

## 二、逐个方案分析

### 1. redamountassir/TE-HGBC（单模 CV 0.95026 / LB 0.95034）⭐ 信息量最大

- **核心武器：全 13 列逐值目标编码（per-value Target Encoding）**——包括 7 个数值列**按精确值转字符串**后 TE。
- **原理（其原文）**：合成标签是从「依赖精确特征值的概率」中采样的；690k 行里每个不同取值重复上百次（如 sleep_duration 仅 701 个不同值），**逐值标签率就是对生成器条件概率的直接估计**。HGBC 自身把数值分箱到 ≤255 桶会损失逐值分辨率，TE 把逐值统计直接递给模型。
- 防泄漏：每折内 `TargetEncoder(cv=5)` 交叉拟合。
- **操作点：慢/浅/重正则**：lr 0.063、max_iter 300、叶 33、min_samples_leaf 298、L2 0.029、max_bins 237。
- 不平衡处理：`sample_weight = len/(3*counts)`（训练时平衡权重）。

### 2. szymonkapiski/XGB+RealMLP blend（CV 0.95058 / LB 0.95070）

- **XGB 单模（CV 0.95005）**：原始特征 + 原生类别，**depth=4、lr 0.021、reg_lambda=26.5、3000 树 ES100**——又是慢/浅/重正则操作点；平衡样本权重。
- **RealMLP（CV 0.95046，取自 yekenot）**：表格神经网络，见下。
- **融合：加权几何平均**（log 概率线性插值），单权重 w 在 OOF 上 0~1 网格搜索。
- 关键观察（其原文）：树和神经网络的错误约 12% 不重叠，故融合超过任一单模。
- 两模型用**同一套冻结 CV（seed 42, 5 折）**保证概率可对齐融合。

### 3. yekenot/RealMLP PyTorch（单模 CV 0.95046）— 全场最强原创单模

- 自实现 RealMLP：PBLD 周期数值嵌入 + 类别嵌入/one-hot + 内部 8 成员集成（n_ens=8）+ EMA 权重 + label smoothing 调度。
- **特征工程与 TE**：每折 `TargetEncoder(cv=5)`；且把**数值列 factorize 成类别码**作为额外类别特征（逐值思想的另一种表达）。
- **epoch 选择直接用验证集 balanced accuracy**（指标对齐的模型选择，与我们发现的 HGBC 早停同理）。
- 训练仅 2 epochs（每 epoch 后按指标挑最优）。

### 4. masayakawamata/XGB-OvR 消融实验（CV 0.95036）⭐ 避坑指南

系统性配对消融（同折同种子，70k 初筛 + 690k 复核），结论摘录：

| 尝试 | 结果 |
| --- | --- |
| One-vs-Rest 拆解 vs 多分类 | **无效**（+0.00003，误差相关性 0.9998，纯噪声） |
| 逐类 scale_pos_weight（训练时类权重） | **负收益**（−0.0008~−0.0015），「β 的替代品，且更差」 |
| AUC/AUCPR 早停 | 负收益（过早停止欠拟合） |
| 逐类超参/逐类编码/逐类组合方式 | 全部无效 |
| **数值列逐值 TE（numdirect）** | **唯一正收益 +0.00028** |

- **β 决策规则**：`argmax(proba / prior^β)`，β 在 OOF 上调节。其称此为**本赛题第一杠杆**：raw argmax ~0.878 → β 校正后 ~0.950（+0.071）。
- 重要暗示：其模型**训练时不加类权重**（发现训练时类权重给定 β 后是 null/负收益），校正全部放在决策时。

### 5. robschieber/先验校正教学（CV 0.94908 / LB 0.95022）

- 把 β=1 的特例讲透：`argmax(p_c / π_c)` 数学上等价于损失中 `class_weight=1/π`，但**放在决策时不需要重训练、适用于任何输出校准概率的模型**。
- 无权重 LGBM + 决策时先验校正即可 0.950。

### 6. vad13irt/EDA+Ensemble（LB 0.95075，公开榜最高的"非提交融合器"）

- 优质 EDA（缺失指示建议、指标解读），但其"ensemble"实为 `0.6×kospintr栈输出 + 0.4×yekenot RealMLP 输出`——公开输出的加权，无新模型。

### 7. 其他（zoli800 seedbag / kospintr 栈 等）

- zoli800：XGB 多种子袋装 + 先验校正（种子平均，抢方差）。
- kospintr（前次已析）：HGBC/LGBM/CatBoost 栈 + Dirichlet 权重，HGBC 用 balanced_accuracy 早停。

### 8. masayakawamata/RepLeafGBM（单模 CV 0.94964，2026-07-03 巡视新增）

- **新模型家族**：RepLeafGBM——GBDT 骨架 + 每个叶子装「冻结 PLR 编码器上的小线性模型」（叶子不再是常数），分裂只用原始特征，类别与 NaN 原生路由；CPU 可跑（Rust 后端）。
- 参数：leaves 128 / lr 0.05 / 3000 树 ES50 / l2_leaf 5 / max_bins 2048；7 折。
- β 网格拉到 **2.5**（作者：极端多数类先验把 OOF 最优 β 推得很高）。
- 其消融证伪（树系）：缺失指示 flag 无效（NaN 路由已捕捉）、比值/乘积/多项式「特征汤」无效（在种子噪声内）。

### 9. masayakawamata/表格 NN 多样性包：GRN（CV 0.94951）/ LNN（0.94938）/ GANDALF（0.94931）（巡视新增）⭐

- 同一作者的系统性 NN 家族横评（自研 masamlp 库，LightGBM 式 API），全部 7 折 + β 决策校正。
- **NN 上验证有效的两个杠杆**：① PLR 数值嵌入（plr-lite）；② **显式缺失指示（逐列 na_flag + 行 n_missing）：+0.0025**——因为 NN 需中位数插补，插补抹掉了「哪些值缺失」的信息，树模型 NaN 原生路由则不需要（与其树系消融互证）。
- **NN 上证伪**：目标编码、训练时类权重、ordinal/one-hot 编码（嵌入更好）。
- **重要细节**：NN 的早停用 multi_logloss **优于**直接用 balanced accuracy 早停（作者：β 规则吃的是概率质量）——与 HGBC 恰好相反，说明「指标对齐早停」并非普适，取决于模型家族。

### 10. danushkumarv/cross-family ensemble + calibration（LB 0.95086，巡视新增）

- 三成员概率融合（0.6 栈GBM + 0.3 RealMLP + 0.1 AutoGluon 多家族袋装），前两者为公开概率文件（半融合器），AutoGluon 成员为原创。
- **特征洞察**：发现交互特征 `stress_level × physical_activity_level`「几乎单独决定目标」（接近但未完全逆向出生成规则）。
- **逐类乘性校正 via 坐标上升**：在 OOF balanced accuracy 上对每类乘子做坐标上升（比 β 标量严格更灵活）；未校正 0.880 → 校正后 0.950，「校正即模型」。
- **多样性 > 单模强度（定量证据）**：更强但与 GBM 更相关的 NN 变体反而**拉低**融合分——换成员前先测不一致率（disagreement rate），别浪费提交。

### 11. amerhu/EDA + LB-Guided Logit Ensemble（LB 0.95088，公开榜新高，2026-07-04 巡视新增）⭐ EDA 部分

- 融合部分是**提交融合器**（5 份公开概率文件的 LB 温度加权几何平均 + OOF 乘子），但 EDA 是全场最系统：
- **逐特征信号裁决表**：强 = stress_level 🏆（近确定性映射 low→fit / medium→at-risk / high→unhealthy 带交叉）、sleep_duration（散点图有 5~6h unhealthy 横带与高睡 fit 横带）、step_count（unhealthy 集中低端，fit 峰值 >12,500）；中 = bmi（仅尾部）、calorie（**双峰 ~1800/~2200，两个活动亚群**）、exercise_duration（**0 值尖峰 =「不运动」亚群**）、sleep_quality、activity、smoking；弱 = heart_rate、water、gender、diet。
- **缺失模式发现：缺失率最高的列恰好是最强预测特征**（stress ≈12%、sleep ≈11% 居首，弱特征 diet 最完整）——缺失非随机、自带信息。
- 相关矩阵近乎全零，唯一例外**活动簇**：cal×step r=0.40、cal×exercise 0.39、step×exercise 0.44。
- 其 LB 实验日志：几何 > 算术 +0.00012；掺入自训 GBDT 三重奏（与公开文件一致率 99.5%）**反而 -0.00035**——同质成员纯稀释；kirill0212 (OvO-LGBM) 是公开池中唯一异源声音（一致率仅 93.4%，异议方向 = 把边界行投回 at-risk）。
- 结论清单（其自述）：多样性是唯一约束；weight 微调已 flat-line；下一步值钱的是 TabM/FT-Transformer 级新家族成员。

### 12. masayakawamata/LogReg Stacker（stack CV 0.95052→0.95064，2026-07-04 巡视新增）

- cdeotte 式 GPU 多项逻辑回归堆叠：全成员 logit 输入、L2（C=0.1）自动压冗余成员、平衡类权重或交叉拟合 β 双变体。
- **诚实协议范本**：β 在训练折上选、只应用于持出折（cross-fitted β）；采纳门槛 =「比最佳单模 ≥+0.002 且 7 折全部同号」，不达标则 fallback 单模。
- 全成员（其 XGB/RepLeaf/GRN/RealMLP 等 7 折系列）堆叠后 CV 0.95064（版本更新，前为 0.95052）——仍与最佳单模同量级，**再证融合天花板 ~0.9506**。

### 13. nybbler/Estimating the score ceiling ⭐⭐ 全场最重要的分析（2026-07-04 巡视4 新增）

- **定量分解 ~0.05 gap = 三块**：① **标签噪声 ≈ 0.033（硬顶）**——合成在 sleep 阈值附近翻转了约 1% 标签，全特征已知也只能到 0.967，无人可越；② **缺失 ≈ 0.026**——主要来自 stress（缺失率最高 12% 且唯一不可救）；③ **代理恢复 ≈ +0.009**——step_count→activity、sleep_quality→sleep bin，把裸 0.941 抬到 ~0.950，**好模型已自动榨取**。
- **机制级新发现：stress_level 是独立采样的纯噪声**——用「增强版」源数据（含 academic_pressure、mental_health_status）验证：任何 stress 潜在驱动特征在各 stress 档上分布完全相同（~30/30/40），MI 全在噪声地板。stress 只是固定边际的独立随机抽取。
- **推论（为什么这是硬墙）**：fit/unhealthy 仅由 stress 区分（fit⟹low、unhealthy⟹high），故 12% stress 缺失行上 fit/unhealthy 无法超过先验，且**无外部数据/聚类能改变**（stress 与万物独立）。这也解释了为何 at-risk recall 永远最低——stress 缺失行上，balanced 最优决策会牺牲多数类 at-risk 去保 fit/unhealthy recall。
- **结论**：现实天花板 ~0.951，私榜获胜区 **0.951–0.952**；此刻已无多少真实空间。

### 14. georgymamarin/quit chasing ~0.950（37 票教学分析，2026-07-04 巡视4 新增）⭐

- **公开榜=幻象**：上季 S6E6 私榜前 20 名公开榜排 149–495 位，公开榜冠军未进私榜前 20；<0.0002 的差距下公开榜顶端纯噪声。
- **对抗验证**（我们此前未做）：train-vs-test 分类器 ROC-AUC ~0.65——存在肉眼看不见的轻度多元漂移（集中在 water_intake/calorie/bmi），但远不到 0.8+ 需重要性加权的程度，**安全可忽略**（OOF 0.9498→LB 0.94988 零 gap 佐证）。
- **类权重 vs prior-correction 是替代非互补**：两者单用都到 ~0.950；叠加会二次过校正，此处 **-0.045**。公开常见「训练类权重 + 事后乘子搜索」之所以不崩，是乘子搜索把第二重校正走回近乎恒等（**正是我们 v6/v10 的温和乘子 1.075~1.15 的来由**）。
- 阈值 MI 扫描技巧（broccoli beef）：对每个阈值 t 算 `x≤t` 与标签的 MI，生成器切点会「点亮」——sleep 峰值在 6.0h。
- 表征是唯一例外（引 Mark Susol 九连击 + nybbler）：一切融合/决策调参卡在 ~0.949，唯有**逐值 TE（精确值、交叉拟合）带来真实 +0.0009 且 LB 同步无 gap**——即我们 v6 的核心。

### 15. philippsinger/TabPFN-3 Starter（GM 作者，2026-07-04 巡视4 新增）

- **全新模型家族**：TabPFN-3 表格基础模型，在数百万合成表上预训练，做 in-context learning（训练行作上下文，一次前向出预测），TabPFN-3 可扩到 100 万行。
- 零特征工程、零调参：原始帧直接喂入，类别/缺失/缩放全内部处理；`balance_probabilities=True` 做事后概率平衡，`eval_metric=balanced_accuracy` + `tune_decision_thresholds`（starter 中注释掉）。
- 成本：需 T4×2 GPU，296k 测试集单次前向 ~1 小时；starter 未报分。**唯一尚未被公开验证多样性的异源家族**，但天花板论对它同样成立。

1. **决策时先验/β 校正是第一杠杆**（+0.07 量级），所有 0.950+ 方案殊途同归；训练时类权重反而多余甚至有害（与 β 冲突时）。实现可用 β 标量（`p/prior^β`，网格到 2.5）或逐类乘子坐标上升（严格更灵活，danushkumarv 验证）。
2. **逐值目标编码是第二杠杆**（约 +0.0003~+0.003）：本质是直接估计合成数据生成器的逐值条件概率，绕过树模型的分箱损失。**注意：仅对树/HGBC 系有效，masamlp 系 NN 上证伪**（嵌入已承担编码职能）。
3. **慢/浅/重正则操作点**：depth 4~6、大 L2、小 lr、几百轮——避免概率锐化。
4. **模型选择的早停指标分家族**（2026-07-03 修订）：HGBC 用 balanced_accuracy 早停有效；**NN 用 multi_logloss 早停更优**（β 校正吃概率质量，balanced accuracy 早停反而更差，masayakawamata NN 系验证）。
5. **跨家族融合**（GBDT × 神经网络）是融合增益的主要来源，几何/算术平均皆可；同家族 OvR/多种 GBDT 增益趋近于零。**多样性 > 单模强度有定量证据**：更强但更相关的成员会拉低融合分，换成员前先测不一致率。
6. **缺失指示特征分家族**（2026-07-03 修订）：树系无效（NaN 原生路由已捕捉）；**NN 系 +0.0025**（插补抹掉缺失位置信息，需显式补回：逐列 na_flag + 行 n_missing）。
7. **冻结共享 CV**（seed 42, 5/7 折 Stratified）让所有模型概率可对齐融合——社区事实标准。
8. 特征洞察：`stress_level × physical_activity_level` 交互近乎单独决定目标（danushkumarv）；睡眠时长是最强单特征（多家 EDA）；**缺失率最高的列恰是最强特征**（amerhu，缺失非随机）；活动簇（cal/step/exercise 两两 r≈0.4）是全数据唯一的特征间相关结构。
9. **天花板已定量锁定（2026-07-04，nybbler + georgymamarin 双独立验证）**：~0.05 gap = 标签噪声 0.033（硬顶 0.967）+ 缺失 0.026 + 代理恢复 +0.009（已自动榨取）。现实天花板 ~0.951，私榜获胜区 0.951–0.952。**关键机制：stress_level 是独立采样纯噪声，与万物无联合结构**——故 12% stress 缺失行是任何模型/外部数据都无法翻越的硬墙（fit/unhealthy 仅由 stress 区分）。
10. **公开榜排名不携带私榜信息**（georgymamarin：上季私榜前 20 = 公开榜 149–495 名）；<0.0002 的公开榜差距是纯子样本噪声。融合天花板 ~0.9506 获多处独立验证（stacker/amerhu/szymon 均 +0.0001 量级）。
11. **类权重与 prior-correction 是替代非互补**（georgymamarin/masayakawamata）：叠加二次过校正会崩（-0.045）；「训练权重 + 事后乘子搜索」安全的前提是乘子被搜回近恒等。
12. 已证无效的坑：OvR 拆解、逐类超参、AUC/AUCPR 早停、训练时逐类权重（与决策校正叠加时）、逐类 TE、比值/乘积/多项式特征汤（树系）、缺失指示（树系）、同质成员掺入公开池（-0.00035，amerhu LB 实测）、缺失规则字段的代理补全/显式边际化（stress 不可救 = 数学硬墙）。

## 附录：已调研清单（巡视 diff 基线）

| ref | 标题分数 | 状态 | 调研日期 |
| --- | --- | --- | --- |
| kospintr/health-stacked-hgbc-catb-xgb-lgbm-baseline | — | read | 2026-07-03 |
| anhadmahajan06/ps-s6e7-0-95095-hill-climbing-meta-modeling | 0.95095 | read（提交融合器） | 2026-07-03 |
| redamountassir/ps-s6e7-hgbc-baseline-lb-0-95034-cv-0-95026 | 0.95034 | read ⭐ | 2026-07-03 |
| szymonkapiski/health-risk-xgboost-realmlp-blend-lb-0-95070 | 0.95070 | read | 2026-07-03 |
| yekenot/ps-s6-e7-realmlp-pytorch | CV 0.95046 | read | 2026-07-03 |
| masayakawamata/s6e7-xgb-ovr-cv-0-95036 | 0.95036 | read ⭐（消融） | 2026-07-03 |
| masayakawamata/s6e7-xgb-1-cv-0-94986 | 0.94986 | read | 2026-07-03 |
| robschieber/s06e07-unweighted-lightgbm-prior-correction | 0.95022 | read | 2026-07-03 |
| vad13irt/ps-s6e7-eda-ensemble-lb-0-95075 | 0.95075 | read（EDA 优质，融合为公开输出加权） | 2026-07-03 |
| zoli800/health-risk-xgb-seedbag-prior | — | read | 2026-07-03 |
| masayakawamata/s6e7-repleaf-1-cv-0-94964 | 0.94964 | read | 2026-07-03（巡视） |
| masayakawamata/s6e7-grn-cv-0-94951 | 0.94951 | read ⭐ | 2026-07-03（巡视） |
| danushkumarv/ps-s6e7-cross-family-ensemble-calibration | 0.95086 | read | 2026-07-03（巡视） |
| anhadmahajan06/confidence-weighted-ensemble-with-score-0-95094 | 0.95094 | skip（提交融合器） | 2026-07-03 |
| anhadmahajan06/ps-s6e7-autonomous-ensemble | — | skip（提交融合器） | 2026-07-03 |
| makthanithin/ps-s6e7-eda-ensemble-lb-0-95075 | 0.95075 | skip（vad13irt 的 fork） | 2026-07-03 |
| zoli800/health-risk-public-blend-bias-jul2 | — | skip（public blend） | 2026-07-03 |
| mpwolke/at-risk-students-health-it-s-ok-asking-for-help | — | skip（弱相关） | 2026-07-03 |
| masayakawamata/s6e7-lnn-cv-0-94938 | 0.94938 | skip（同 GRN 系列，取最高分代表精读） | 2026-07-03 |
| masayakawamata/s6e7-gandalf-cv-0-94931 | 0.94931 | skip（同上） | 2026-07-03 |
| sohailkhanlml/realmlp-v1-starter-cv-0-94972 | 0.94972 | skip（yekenot 复刻） | 2026-07-03 |
| miooomiooo/catboos-xgboost-lightgbm-optuna-blending-0-94974 | 0.94974 | skip（常规 GBDT 融合，低于已析同类） | 2026-07-03 |
| gauravduttaiiitb/ex1-s6e7-autogluon-good-quality-gpu | — | skip（AutoML 跑分） | 2026-07-03 |
| gauravduttaiiitb/ex1-s6e7-autogluon-optimize-for-deployment | — | skip（AutoML 跑分） | 2026-07-03 |
| gauravduttaiiitb/ex1-s6e7-flaml-weighted-roc-auc-ovr | — | skip（AutoML 跑分） | 2026-07-03 |
| gauravduttaiiitb/s6e7-flaml-roc-auc-ovo-weighted | — | skip（AutoML 跑分） | 2026-07-03 |
| gauravduttaiiitb/s6e7-flaml-roc-auc-ovr-weighted | — | skip（AutoML 跑分） | 2026-07-03 |
| gauravduttaiiitb/s6e7-flaml-weighted-roc-auc-ovr | — | skip（AutoML 跑分） | 2026-07-03 |
| nina2025/ps-s6e7-catboost | — | skip（快扫：常规 CatBoost+Ordinal，无新方法论） | 2026-07-03（巡视2） |
| nina2025/ps-s6e7-micromodel-catboost-lightgbm-xgb | — | skip（常规三 GBDT 融合） | 2026-07-03（巡视2） |
| kirikiti/stacking-treeboost-e6s7 | — | skip（快扫：常规 stacking+线性元模型） | 2026-07-03（巡视2） |
| georgymamarin/student-health-risk-why-86-accuracy-scores-0-33 | — | skip（β 校正源头教学，结论已被 robschieber 节收录） | 2026-07-03（巡视2） |
| avikdas567/multi-gbdt-ensemble-for-student-health-profiling | — | skip（常规多 GBDT 融合） | 2026-07-03（巡视2） |
| thuandao/student-health-risk-eda-detail-catboost | — | skip（EDA+CatBoost 教学） | 2026-07-03（巡视2） |
| donmarch14/s6e7-cat | — | skip（常规 CatBoost） | 2026-07-03（巡视2） |
| daoviet/s6e7-baseline | — | skip（基线） | 2026-07-03（巡视2） |
| emanuellcs/student-health-risk-xgboost-lightgbm | — | skip（常规 XGB+LGBM） | 2026-07-03（巡视2） |
| mubashirulhassan00/predicting-student-health-risk-s6e7 | — | skip（教学基线） | 2026-07-03（巡视2） |
| guillermotorresj11/walkthrough-eda-cb-xgb-lgbm-0-9495 | 0.9495 | skip（教学 walkthrough，方法常规） | 2026-07-03（巡视2） |
| mikhailnaumov/student-health-risk-xgb | — | skip（常规 XGB） | 2026-07-03（巡视2） |
| ravi20076/playgrounds6e7-stacker-v1 | — | skip（常规 stacker） | 2026-07-03（巡视2） |
| adittoahosankabbo/s6e7-student-health-risk | — | skip（基线） | 2026-07-03（巡视2） |
| hmnshudhmn24/predicting-student-health-risk | — | skip（基线） | 2026-07-03（巡视2） |
| kirill0212/ps6e7-one-vs-one-lightgbm | — | skip（OvO 变体，OvR 消融已证此路无效） | 2026-07-03（巡视2） |
| yajatpawar/s6e7-optuna-catboost | — | skip（Optuna 调参 CatBoost） | 2026-07-03（巡视2） |
| flexonafft/field-trials-pipeline | — | skip（与赛题弱相关） | 2026-07-03（巡视2） |
| stephentarter/ps-s06e07-model-visualizer | — | skip（可视化工具） | 2026-07-03（巡视2） |
| stephentarter/ps-s06e07-xgboost | — | skip（基线） | 2026-07-03（巡视2） |
| stephentarter/ps-s06e07-feature-engineering | — | skip（常规 FE） | 2026-07-03（巡视2） |
| kimberlydawap/student-health-risk-prediction | — | skip（基线） | 2026-07-03（巡视2） |
| josephnehrenz/s6e7-student-health-risk | — | skip（基线） | 2026-07-03（巡视2） |
| koushikkumardinda/predicting-student-health-risk-s6e7-r-kernel | — | skip（R 基线） | 2026-07-03（巡视2） |
| amerhu/s6e7-eda-lb-guided-logit-ensemble | 0.95088 | read ⭐（EDA 优质；融合为提交融合器） | 2026-07-04（巡视3） |
| masayakawamata/s6e7-logreg-stacker-cv-0-95052 | CV 0.95052 | read | 2026-07-04（巡视3） |
| pavloivanin/log-odds-ensemble-lb-guided-calibration | — | read（logit 融合 + β，均为已知配方） | 2026-07-04（巡视3） |
| amanvishwakarma01/nans-are-features-s6e7-eda-blend | — | read（常规缺失指示 EDA+LGBM 基线） | 2026-07-04（巡视3） |
| n0rollback/s6e7-clean-eda-balanced-accuracy-insights | — | read（教学 EDA，无新信息） | 2026-07-04（巡视3） |
| n0rollback/s6e7-feature-engineering-model-shootout | — | read（比值特征 shootout，自证在折噪声内） | 2026-07-04（巡视3） |
| makthanithin/ps-s6e7-0-95095-hill-climbing-meta-modeling | 0.95095 | skip（anhadmahajan06 的 fork） | 2026-07-04（巡视3） |
| yogeshm01/health-stacked-hgbc-catb-xgb-lgbm-baseline | — | skip（kospintr 的 fork） | 2026-07-04（巡视3） |
| masayakawamata/s6e7-tabr-cv-0-94833 | 0.94833 | skip（NN 系列低分成员，GRN 代表已析） | 2026-07-04（巡视3） |
| masayakawamata/s6e7-danet-cv-0-94922 | 0.94922 | skip（同上） | 2026-07-04（巡视3） |
| biohack44/predict-health-student-fusion | — | skip（常规融合） | 2026-07-04（巡视3） |
| baseershah/pss6e7-stacker | — | skip（常规 stacker） | 2026-07-04（巡视3） |
| stephentarter/ps-s06e07-catboost | — | skip（基线） | 2026-07-04（巡视3） |
| stephentarter/ps-s06e07-lightgbm | — | skip（基线） | 2026-07-04（巡视3） |
| tharishreddy22/predicting-health-risk-using-light-gbm | — | skip（基线） | 2026-07-04（巡视3） |
| tharishreddy22/predict-health-risk-xg-boost-cat-boost-lightgbm | — | skip（基线） | 2026-07-04（巡视3） |
| n0rollback/s6e7-histgradientboosting-baseline-cv-0-949 | 0.949 | skip（HGBC 基线，配方已知） | 2026-07-04（巡视3） |
| amanatar/student-health-risk-realmlp-k-fold-ensemble | — | skip（RealMLP 复刻） | 2026-07-04（巡视3） |
| gauravduttaiiitb/ex1-s6e7-autogluon-high-quality-gpu | — | skip（AutoML 跑分） | 2026-07-04（巡视3） |
| gauravduttaiiitb/ex1-s6e7-autogluon-best-quality-gpu | — | skip（AutoML 跑分） | 2026-07-04（巡视3） |
| gauravduttaiiitb/ex3-s6e7-flaml-balanced-accuracy | — | skip（AutoML 跑分） | 2026-07-04（巡视3） |
| gauravduttaiiitb/ex3-s6e7-flaml-weighted-roc-auc-ovr | — | skip（AutoML 跑分） | 2026-07-04（巡视3） |
| gauravduttaiiitb/ex1-org-s6e7-flaml-balanced-accurac | — | skip（AutoML 跑分） | 2026-07-04（巡视3） |

| nybbler/s6e7-estimating-the-score-ceiling | 分析 | read ⭐⭐（天花板分解 + stress=噪声机制） | 2026-07-04（巡视4） |
| georgymamarin/s6e7-quit-chasing-0-950-like-everyone | 分析 | read ⭐（公开榜=幻象 + 对抗验证 + 权重/校正替代性） | 2026-07-04（巡视4） |
| philippsinger/tabpfn-3-starter-playground-series-s6e7 | starter | read（TabPFN-3 基础模型，需 GPU 未报分） | 2026-07-04（巡视4） |
| yunsuxiaozi/pss6e7-realmlp-cv-0-95063 | CV 0.95063 | read（RealMLP + 逐值 TE，7 折，无新杠杆） | 2026-07-04（巡视4） |
| amanatar/s6e7-student-hearth-risk-lb-0-95112 | 0.95112 | read（三文件多数投票融合器） | 2026-07-04（巡视4） |
| anhadmahajan06/s6e7-post-processing-ensemble-lb-0-95112 | 0.95112 | skip（提交融合器/后处理） | 2026-07-04（巡视4） |
| makthanithin/s6e7-post-processing-ensemble-lb-0-95112 | 0.95112 | skip（anhadmahajan06 的 fork） | 2026-07-04（巡视4） |
| stephennedumpally/confidence-weighted-ensemble-with-score-0-95108 | 0.95108 | skip（提交融合器） | 2026-07-04（巡视4） |
| tgmath/ps-s6e7-score-weighted-hard-vote-lb | — | skip（提交硬投票融合器） | 2026-07-04（巡视4） |
| godofthunder2407/confidence-weighted-ensemble | — | skip（提交融合器） | 2026-07-04（巡视4） |
| beicicc/student-health-risk-public-ensemble | — | skip（公开提交融合器） | 2026-07-04（巡视4） |
| yaaangzhou/top-3-kernels-integrated-ensemble | — | skip（提交融合器） | 2026-07-04（巡视4） |
| nawfeelrahman1124444/ps-s6-ep6-realmlp-0-95090 | 0.95090 | skip（RealMLP 复刻，无新方法） | 2026-07-04（巡视4） |
| aribaymane61/ps-s6e7-ft-transformer-single-model-lb-0-95033 | 0.95033 | skip（FT-Transformer 单模，NN 家族已充分调研，分数低于 RealMLP） | 2026-07-04（巡视4） |
| pcxxxxxx/realmlp-tree-blend-oof-ensemble | — | skip（RealMLP+Tree OOF 融合，方法已知） | 2026-07-04（巡视4） |
| razanihababdellatif/cracking-student-health-risk | — | skip（教学向，无新方法论） | 2026-07-04（巡视4） |
| thuandao/ps-s6e7-predicting-student-health-risk | — | skip（EDA+CatBoost 教学，43 票但方法常规） | 2026-07-04（巡视4） |
| flexonafft/health-field-trials-pipeline-0-95 | 0.95 | skip（管线跑分，与赛题弱相关） | 2026-07-04（巡视4） |
| gauravduttaiiitb/ex1-s6e7-best-quality-xgboost-r89-bag-l1 | — | skip（AutoGluon 跑分） | 2026-07-04（巡视4） |
| daoviet/s6e7-eda-baseline | — | skip（EDA 基线，daoviet/s6e7-baseline 已登记） | 2026-07-04（巡视4） |
| koushikkumardinda/advanced-health-risk-optuna-k-fold-ensemble | — | skip（Optuna 调参融合） | 2026-07-04（巡视4） |
| kostya138/health-risk-blueprint-catboost-0-949-score | 0.949 | skip（CatBoost 基线） | 2026-07-04（巡视4） |
| kostya138/notebook3ef526ce13 | — | skip（草稿本） | 2026-07-04（巡视4） |
| vedantpol/catboost-models-ensamble | — | skip（CatBoost 融合基线） | 2026-07-04（巡视4） |
| vedantpol/xgboost-ensembel | — | skip（XGB 融合基线） | 2026-07-04（巡视4） |
| taroshg/basic-lgbm-and-feature-eng-score-0-95 | 0.95 | skip（教学 LGBM+FE） | 2026-07-04（巡视4） |
| taroshg/ps-e6s7-basic-eda-w-feature-correlation-heatmap | — | skip（基础 EDA） | 2026-07-04（巡视4） |
| nikunjkatta/notebook1-baseline | — | skip（基线） | 2026-07-04（巡视4） |
| nikunjkatta/notebook2-univariate-analysis | — | skip（单变量 EDA） | 2026-07-04（巡视4） |
| nishant30488/ps6e7-eda-optuna | — | skip（EDA+Optuna 教学） | 2026-07-04（巡视4） |
| sarveshchhetri/xgboost-baseline-health-condition-prediction | — | skip（XGB 基线） | 2026-07-04（巡视4） |
| udaken10/multi-tree-mlp-grid-search | — | skip（网格搜索教学） | 2026-07-04（巡视4） |
| vladstud716373618/s6e7-scientific-investigation-of-data | — | skip（EDA 探索） | 2026-07-04（巡视4） |
| engineerfrabbi/predicting-student-health-risk-3 | — | skip（基线） | 2026-07-04（巡视4） |
