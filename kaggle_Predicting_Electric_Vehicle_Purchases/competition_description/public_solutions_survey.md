# 公开高分方案调研 — Predicting Electric Vehicle Purchases (Playground S6E9)

> 首次调研：2026-09-30 15:30 UTC（截止前约 8.5 小时）。方法：读取同日 15:23 UTC 由官方 Kaggle CLI 拉取并归档的证据（`strange-gates-ca18fe` 工作树 `competition_description/forum_review_20260930/evidence/`：榜单前 20、61 个论坛主题目录与 15 个主题正文、notebook 按分数/按运行时间各 100 条、9 份 notebook 源码与运行日志），精读其中的源码和日志。按票数排序的列表本次未单独拉取。目的：整理公开可复现的高分方法与已被证伪的方法。指标 ROC AUC。

## 更新日志

| 日期 | 内容 | 一句话结论 |
| --- | --- | --- |
| 2026-09-30 | 首次全量：精读 4 份源码、9 份日志、8 个论坛主题 | 公开最强单模是线性模型（岭逻辑回归，10 折 OOF 0.94640 / LB 0.94656）；「GBDT 从该线性模型的 logit 起步」再加诚实 OOF 融合到 OOF 0.94664 / LB 0.94675 |

## 一、公开榜格局（2026-09-30 15:23 UTC）

| 分数段 | 代表 | 方案类型 |
| --- | --- | --- |
| 0.94945 | Team Alicia（第 1） | 无公开配方；论坛普遍怀疑，作者只说「看私榜」 |
| 0.94682–0.94697 | 第 2–20 名（Paul Bryan Elefante=heuljax 0.94697、Chris Deotte 0.94692） | 自训多视角模型 + OOF 爬山融合；heuljax 自报单 XGB 10 折 CV 0.94671、集成 0.9468+ |
| 0.94675–0.94679 | goodpjw2008、abhirajhiwale、souvikdbiswas、nina2025 | 前者有完整 OOF 流程；后三者是对公开提交文件的再混合 |
| 0.94656–0.94663 | lucifer19 Grand Prix、jazivxt Zoom Zoom、nina2025、miickey 等 | 同一血缘文件的反复混合，互相秩相关 0.9995–1.0000 |
| 0.94637–0.94643 | Naji 单模、mikhailnaumov 单 XGB | 三重目标编码 + 数位特征的 GBDT 单模 |
| 0.9417–0.9455 | 各类入门基线 | 原始特征 → 数位 → 频次 → 折内目标编码 |

9 月 26 日第 2 名为 0.94679，四天内整体上移约 0.0002，时间点与 heuljax 9 月 29 日公开线性模型吻合。

## 二、逐个方案分析

### ⭐ heuljax — Generator-Aware Ridge Logistic Regression（10 折 OOF 0.946400 / LB 0.94656，调研 2026-09-30）

- **特征解读**：收入整数写成字符串后按 **GPT-2 BPE 分词**（` 92887` → ` 9|28|87`，` 30000` → ` 3|0000`），首 token（L1）、前两 token（L2）、末 token（LAST）、精确值（IV）构成层级。goodpjw2008 的对照：三层链式编码单特征 AUC，GPT-2 token 0.71758 > `//1000→//100→精确值` 0.71577 > cl100k/o200k 0.71498 > 首位数字→前两位 0.71093。
- **特征工程（316 列：163 个带标签、153 个无标签）**：
  - 平滑购买率取 logit：9 个键 × 平滑 5/50；
  - **链式先验**：每层购买率向上一层收缩（全局 → L1 → L2 → IV），强度 5/20/80；通勤同理（整数部分 → 精确值）；
  - token × 上下文（12 个列）、通勤整数 × 上下文、生成公式门控格（补贴×环保×焦虑×家充）× token/通勤/收入分位、类别两两组合 55 对、类别 × 收入 20 分位/通勤 10 分位；
  - 无标签：原始数值 + 5 个分位点折线（hinge）、one-hot、train+test 对数频次、生成公式值 `1.2·收入/1e5 + 0.6·环保 + 2·补贴 − 焦虑`；
  - **人群构成特征**：在每个收入 token 组内，对其余 16 个列做留一均值（train+test 合并计算，不用标签）。
- **防泄漏**：外层训练行的带标签特征用内层 5 折交叉拟合；外层验证/测试行用整个外层训练折统计。
- **模型**：标准化后的 L2 逻辑回归，LBFGS 200 步，L2=10；T4 上 10 折共 4 分钟。
- **融合**：无，单模。
- 系数占比（goodpjw2008 移植版日志）：类别两两组合 3.72、token 链 1.90、平滑率 1.88、token×上下文 1.81、类别×连续分箱 1.71、人群构成 1.58；单项最大为首 token 购买率。

### ⭐ goodpjw2008 — LR-Margin GBDT + OOF Stack（5 折 OOF 0.94664 / LB 0.94675，调研 2026-09-30）

- **A 部分**：移植 heuljax 线性模型，5 折 OOF 0.94634；额外加十进制链、原始 1 万行按值均值、L2=30，各 ≤ +0.00001。关键新增：为训练行生成**内层交叉拟合的 logit**。
- **B 部分**：LightGBM `init_score` / XGBoost `base_margin` 从线性模型 logit 起步，特征为 25 个键 × 3 档平滑的折内目标编码。同折对比：不带起点的 LightGBM 0.94608 → 带起点 0.94646；XGBoost 0.94610 → 0.94646；树数从 1500–2500 降到 400–1300。参数：LightGBM depth 5 / 32 叶 / min_child 10 / colsample 0.3 / max_bin 1024 / lr 0.02；XGBoost depth 4 / colsample 0.6 / lambda 5。
- **C 部分**：直接使用 6 份公开 OOF+test 预测：heuljax LR 0.94640、heuljax XGB 0.94631、BlamerX 窗口编码 XGB 0.94621、megayak 视角 A 0.94628 / 视角 D 0.94608、RealMLP 3 种子 0.94618。
- **D 部分**：全部转百分位秩，OOF 上贪心爬山（步长 0.02），权重在 5 折嵌套内拟合后取平均。最终权重：残差 LightGBM 0.385、heuljax LR 0.154、heuljax XGB 0.154、BlamerX 0.138、RealMLP 0.062、megayak A/D 各 0.054。嵌套增益 +0.00021～+0.00026，5/5 折为正。
- **逐步增益表（固定折）**：自有 GBDT 融合 0.94614 → 线性模型 0.94632 → 线性起点 GBDT 0.94646 → 加公开 OOF 成员 0.94664 → 再加 3 种子线性/MLP 0.94667（LB 反而 −0.00001）。只用 6 份公开 OOF、不含自训模型即有 OOF 0.94662 / LB 0.94670。
- **证伪**：移植后的线性模型对通勤 token、门控×token 交叉、L2 3→100、换折种子均在 ±0.00001 内；同基底 MLP 0.94613；含验证折标签的伪标签 CV +0.0002～+0.0004 而 LB 增量为 0。

### heuljax — Logistic Regression Sample（10 折 OOF 0.946264，调研 2026-09-30）

229 个语义特征，用数字前缀层级、盒式平滑、加性逻辑坐标近似上面的 token 方案；cuML LBFGS 250 步多数折未收敛；292 秒。说明不用 GPT-2 分词也能到 0.9463，分词再加约 0.00014。

### heuljax — XGB Sample（10 折 OOF 0.946309，调研 2026-09-26 归档）

173 特征：donor 交叉拟合的邻域购买率、层级收缩、收入组人群构成反演、门控混合后验、GAM `base_margin`。作者私有版单 XGB CV 0.94652→0.94671，做法是把内层折基础模型（目标与非目标）的预测当特征。

### mikhailnaumov — Single XGB（OOF 0.946204 / LB 0.94643，调研 2026-09-30，仅读日志）

收入分位分箱、原始数据目标均值、10 折 GPU XGB（lr 0.01）。属 GBDT 单模上限附近。

### ou20040313 — single-model alternatives（10 折 OOF 0.946229，调研 2026-09-30）

自有 GPU XGB 74 基础列 + 34 键；对照复现的 Naumov 分位分箱版 0.944822。

### abhirajhiwale — Ridge Tower（LB 0.94677，调研 2026-09-30）

三份提交文件的秩→正态分数加权（heuljax 线性 0.445、Grand Prix 两个快照 0.332/0.224）+ 4 条边界规则。作者自报失败项：子群校正 LB 0.94654、非线性堆叠 0.94674、TabPFN 0.94617、embedding NN OOF 0.93854、伪标签 XGB −0.00006。

### lucifer19 — EV Grand Prix（LB ≈0.94676，调研 2026-09-30，仅读日志）

最终混合 = jazivxt 混合文件 52.7% + heuljax 线性 47.3%，权重由各文件公榜分数反推；另附一份嵌套 OOF 0.946648 的「诚实对冲」文件。

### megayak — Reading And Fitting The Public Split（调研 2026-09-30，仅读日志）

用成对提交读出公榜 20% 的行，把公开文件从 0.94651 抬到 0.94656 而不训练任何模型；13.5 万行秩被改动。证明 0.9465–0.9466 段的排名差是几百个公榜行的拟合。

## 三、社区共识配方

1. **信号结构**：原始公式单独 0.9377；其余信号几乎全在「每个收入取值各自的购买率」。阶梯（hitarthjain0，LightGBM 5 折）：原始 0.94186 → 数位 0.94345 → 频次 0.94382 → 折内目标编码 0.94550。`//100`、`//1000` 粗粒度键去掉会掉 0.0003。
2. **生成器指纹是分词形状的**：收入按 GPT-2 BPE 切分的层级优于任何十进制规则（0.71758 vs 0.71577）。
3. **线性模型 + 高度非线性的率特征**是最强单模视角，且与树模型秩相关只有 0.991–0.992（树与树 0.998+）。heuljax 的口诀：线性模型喂非线性特征，非线性模型喂线性特征。
4. **从线性 logit 起步的 GBDT** 比与线性模型做融合更好：+0.00015（对线性）、+0.0003（对无起点 GBDT）。
5. **多样性来自特征视角而非学习器**：同特征换 XGBoost/LightGBM 权重为 0；窗口编码、无精确键阶梯、RealMLP 虽单模弱也拿到权重。heuljax 的入池标准：CV ≥ 0.9400 且与主模型 Spearman < 0.99。
6. **更多折持续有效**：10 折比 5 折对所有模型 +0.00013；学习曲线可外推到 20 折 +0.00005；全量重拟合对 GBDT +0.00005。
7. **目标编码先验强度**：先验 20 → 1 约 +0.00025（Marc Maldonado Lorca 消融，经 744248 帖转述）。
8. **避坑**：
   - 伪标签：教师见过被评分折的标签时 CV 虚高 +0.0003，严格做法只有 +0.00002；
   - 边界规则（收入 ≥170,537、31,004–41,970、通勤 ≥83 km、3 万收入无补贴格）OOF 仅 +0.000002，公榜 0 变化；
   - TabPFN 0.9378–0.9462、embedding NN、交互目标编码、直接追加原始数据均无稳定收益；
   - 0.9465+ 的公开混合文件彼此秩相关 ≈1，等权混合只得到均值；公榜分辨率约 0.00002；
   - 无 CV 的「盲混」notebook 被 Tilii、Chris Deotte 等明确警告私榜风险。

## 附录：已调研清单

| ref | 标题分数 | 状态 | 调研日期 |
| --- | --- | --- | --- |
| heuljax/kps6e09-generator-aware-ridge-logistic-regression | OOF 0.94640 / LB 0.94656 | read | 2026-09-30 |
| goodpjw2008/s6e9-lr-margin-gbdt-oof-stack-lb-0-94675 | LB 0.94675 | read | 2026-09-30 |
| heuljax/kps6e09-logistic-regression-sample | OOF 0.94626 | read（说明+日志） | 2026-09-30 |
| heuljax/kps6e09-xgb-sample | OOF 0.94631 | read（09-26 归档） | 2026-09-26 |
| mikhailnaumov/electric-vehicle-purchases-single-xgb | LB 0.94643 | read（日志） | 2026-09-30 |
| ou20040313/s6e9-single-model-alternatives | OOF 0.94623 | read | 2026-09-30 |
| abhirajhiwale/s6e9-0-94677-ridge-tower-4-stable-rules | LB 0.94677 | read（文件混合，记录其失败项） | 2026-09-30 |
| megayak/s6e9-reading-and-fitting-the-public-split | — | read（日志；公榜拟合） | 2026-09-30 |
| lucifer19/ev-grand-prix-48-engine-cpu-pit-stop-blend | LB ≈0.94676 | skip：提交文件混合器 | 2026-09-30 |
| souvikdbiswas/geodesic-rank-manifold-0-94679-fast-ev-ensemble | LB 0.94679 | skip：三份公开文件混合 | 2026-09-30 |
| nina2025/fork-of-ps-s6e9 | LB 0.94679 | skip：公开文件混合 | 2026-09-30 |
| nina2025/fork-of-ps-s6e9-round-robin | — | skip：公开文件混合 | 2026-09-30 |
| nina2025/ps-s6e9-rank-ml | — | skip：公开文件混合 | 2026-09-30 |
| rohitt94/s6e9-ensemble-notebook | — | skip：未读，标题为融合 | 2026-09-30 |
| shawncsx/pevp-s6e9-ens5-fusion-f | — | skip：文件混合 | 2026-09-30 |
| jazivxt/single-model-zoom-zoom | LB 0.94658 | skip：未读（被他人证实与 Grand Prix 秩相关 0.99999） | 2026-09-30 |
| jazivxt/zoom-zoom-r-edition | — | skip：同上血缘 | 2026-09-30 |
| crystalbaby/ev-grand-prix-48-engine-cpu-pit-stop-blend | — | skip：Grand Prix 复制 | 2026-09-30 |
| crystalbaby/ev-blend | — | skip：文件混合 | 2026-09-30 |
| crystalbaby/s6e9-does-breaking-ties-help | — | skip：复制 | 2026-09-30 |
| crystalbaby/pseudo-labels-without-lying-to-cv-15-teachers | — | skip：未读，伪标签结论已由 743298 帖覆盖 | 2026-09-30 |
| miickey/s6e9-kaggle-ready-0-94657-micro-blend | LB 0.94657 | skip：文件混合 | 2026-09-30 |
| chinzorigtganbat/s6e9-does-breaking-ties-help | — | skip：文件混合 | 2026-09-30 |
| thisray/s6e9-fisher-blend-from-leaderboard-scores | — | skip：按公榜分数定权 | 2026-09-30 |
| harishyadav0506/s6e9-my-own-model-nina-blend-comparison | — | skip：文件混合对比 | 2026-09-30 |
| kozykappa/electric-car-lb-0-94657 | LB 0.94657 | skip：未读 | 2026-09-30 |
| amanatar/s6e9-samart-sota-meta-blend-lb-0-94656-champion | LB 0.94656 | skip：文件混合 | 2026-09-30 |
| amanatar/s6e9-sota-meta-blend | — | skip：文件混合 | 2026-09-30 |
| talhatursun/s6e9-best-public-blend-tracker | — | skip：文件混合 | 2026-09-30 |
| megayak/s6e9-0-94656-reading-the-public-split | LB 0.94656 | skip：公榜拟合，结论已记 | 2026-09-30 |
| megayak/s6e9-where-the-0-94651-comes-from | — | skip：未读 | 2026-09-30 |
| megayak/s6e9-what-the-0-94650-actually-is | — | skip：未读 | 2026-09-30 |
| megayak/s6e9-the-ceiling-test-is-circular | — | skip：未读 | 2026-09-30 |
| megayak/s6e9-0-94650-forkable-no-private-inputs | LB 0.94650 | skip：未读 | 2026-09-30 |
| megayak/s6e9-0-94645-from-oof-files-only | LB 0.94645 | skip：未读 | 2026-09-30 |
| denpugovkin/fifteen-teachers-fewer-voices-s6e9 | — | skip：未读 | 2026-09-30 |
| denpugovkin/the-gain-needs-an-interval-s6e9 | — | skip：未读 | 2026-09-30 |
| denpugovkin/the-0-94656-ranking-has-1-000-small-rooms | — | skip：未读 | 2026-09-30 |
| denpugovkin/s6e9-nested-te-lightgbm-original-table-dgp-rej | — | skip：未读 | 2026-09-30 |
| sometimessubodh/0-94651-breaking-0-94650-lasso-meta-stack | LB 0.94651 | skip：元融合 | 2026-09-30 |
| jakiduy/electriccar-purchase-ensemble-model-tripete | — | skip：未读 | 2026-09-30 |
| sumitsarkar969/public-rank-blending-playground-series-s6e9 | — | skip：文件混合 | 2026-09-30 |
| vinay24baghira/s6e9-the-art-of-weighted-blending | — | skip：文件混合 | 2026-09-30 |
| rafanikitas/s6e9-memory-aware-recipe-residual-lgbm | — | skip：未读 | 2026-09-30 |
| tamerlanomralinov/s6e9-lb-0-94649-blend-custom-hirge-net | LB 0.94649 | skip：未读 | 2026-09-30 |
| najiama/oof-power-two-single-models-blend-lb-0-94638 | LB 0.94638 | skip：未读 | 2026-09-30 |
| evgendvorkin/s6e9-single-xgb-cv-0-94608 | CV 0.94608 | skip：未读 | 2026-09-30 |
| sergeyqt2024/lr-squeeze | LR 65 特征 0.94490 | skip：未读（分数来自 742904 帖） | 2026-09-30 |
| hitarthjain0/s6e9-feature-ladder-what-moves-cv | 0.94550 | skip：结论取自 744600 帖 | 2026-09-30 |
| hitarthjain0/ev-adoption-interactive-visual-insights | — | skip：可视化 | 2026-09-30 |
| hitarthjain0/s6e9-ev-purchase-fast-eda-feature-eng-lightgbm | — | skip：基线 | 2026-09-30 |
| hitarthjain0/s6e9-ev-adoption-fast-baseline | — | skip：基线 | 2026-09-30 |
| souvikdbiswas/chase-top-40-in-0-5s-grand-prix-x-round-robin | — | skip：文件混合 | 2026-09-30 |
| slimypunk03/hill-climb-algorithm-gm-ensemble-signal-hunting | — | skip：未读 | 2026-09-30 |
| anthonytherrien/ev-purchase-xgboost-feature-engineering | — | skip：未读 | 2026-09-30 |
| anthonytherrien/ev-purchase-lightgbm-feature-engineering | — | skip：未读 | 2026-09-30 |
| mohamedabder/01-eda-predicting-electric-vehicle-purchases | — | skip：EDA | 2026-09-30 |
| riyaraj9/s6e9-electrical-vehicle-purchase | — | skip：基线 | 2026-09-30 |
| prathameshmore07/ev-purchase-prediction-xgboost | — | skip：基线 | 2026-09-30 |
| jonibekabdurahmonov/stacking-vs-blending | — | skip：未读 | 2026-09-30 |
| aparnasi13/notebook25871b7078 | — | skip：无标题 | 2026-09-30 |
| keyadobriyal/lgbm-xgboost-v2 | — | skip：基线 | 2026-09-30 |
| ksmashhero/s6e9-live-leaderboard-explorer-meta-analysis | — | skip：榜单工具 | 2026-09-30 |
| tarunsingh2002/ev-purchase-prediction-complete-eda-optuna-hgb | — | skip：基线 | 2026-09-30 |
| jimgruman/buy-an-ev | — | skip：未读 | 2026-09-30 |
| parthsarnobat/s6e9-ev-purchase-prediction-catboost-xgb-blend | — | skip：基线 | 2026-09-30 |
| animeguylrn/submissions-playground-series-s6e9 | — | skip：提交文件集 | 2026-09-30 |
| jakomina/ev-baseline-ipynb | — | skip：基线 | 2026-09-30 |
| goutamsharma12/model-2-using-lightgbm-catboost | — | skip：基线 | 2026-09-30 |
| mehrankazeminia/s6e9-ev-skip-training | — | skip：文件混合 | 2026-09-30 |
| mdnaimislam165436/who-will-buy-an-ev-eda-4-model-comparison | — | skip：基线 | 2026-09-30 |
