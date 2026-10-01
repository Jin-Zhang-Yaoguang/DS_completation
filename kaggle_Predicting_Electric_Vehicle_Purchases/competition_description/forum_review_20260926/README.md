# Predicting Electric Vehicle Purchases：2026-09-26 增量调研

结论：公开资料里最值得新增验证的是**按原始字段分组的树交互约束**；其次是 **composition-adjusted income encoding（校正收入组人群构成）**。前者已有两个种子的配对改善，后者有具体公开源码但缺单独消融。重复切分、普通生成公式先验、周期神经编码并非本地空白。榜首 0.94945 尚无公开可复现配方，不能据此宣称社区解决了新的机制。

本轮仅调研、读代码及归档，没有训练、提交、修改历史模型或恢复停止的研究。

## 1. 赛题与证据口径

[官方比赛](https://www.kaggle.com/competitions/playground-series-s6e9/overview)是 2026 年 9 月 Playground 二分类赛。目标 Will_Buy_EV，提交购买概率，指标 ROC AUC，截止 9 月 30 日 23:59 UTC。数据是合成数据，不能把变量关联解释为现实购车因果。训练集 668,665 行、测试集 286,571 行；任务是概率排序，不是用固定阈值优化准确率。

证据分层：运行日志可证实该运行输出；仓库实验表和论坛数字是作者报告；同一套 OOF 调权属于开发结果；只对固定 OOF 矩阵再做嵌套验证，只能验证融合层，不能自动消除基模型训练及前期选择泄漏。跨折数、种子、特征和调参次数的绝对 AUC 不直接判胜负。

截至本次 CLI 快照，[榜单](https://www.kaggle.com/competitions/playground-series-s6e9/leaderboard)第一名 Team Alicia 0.94945，第二名 Prior 0.94679，第三名 Chris Deotte 0.94672。第一名记录时间 2026-09-26 01:37:29.793 UTC。社区讨论没有提供第一名的可核验训练配方，因此这是一项观察到的 Public 跃升，既不是可复现方法证据，也不是作弊证据。

## 2. 真正新增的优先候选

### P1：按“原始字段家族”约束树交互

来源：[canaryigo 仓库](https://github.com/canaryigo/kaggle-s6e9-ev-purchase-prediction)，固定提交 `8b1ceacfc3ebffebfa97d25e158c8c2c08d3b86a`。

作者的两种子实验：

| 配置 | seed 42 | seed 20260918 |
|---|---:|---:|
| 原 F | 0.94605253 | 0.94605825 |
| 仅提高收入分箱精度 | 0.94606548 | 0.94605083 |
| 高精度 + 分组约束 | 0.94615852 | 0.94615019 |
| 所有列 max_bin=1024 + 分组约束 | 0.94615563 | 0.94614755 |

最后一行相对原 F 分别 +0.00010310、+0.00008930。仅提高收入精度不能稳定改善。作者最终将原 F 与约束 F 固定 50:50，报告最终 ensemble 两种子均 5/5 折改善，Public 0.94635→0.94636。这些是仓库公开的实验记录，本轮未复跑。

实现已核对：`src/reproduce.py` 的 `origin()` 把 raw、digit、TE、frequency、original mean 按来源字段归组，再构建 LightGBM `interaction_constraints`。同一字段的不同表达可以共同分裂，禁止树路径跨原始字段组交互。

为什么值得新试：本地 singleton interaction 把各派生列逐个隔离，损失 -0.000392173，0/5 折；这里允许“收入原值 × 收入 TE × 收入频率”在组内交互，机制不同。源购买公式近似加法结构也给出动机，但竞赛再次合成可能引入交互，所以不能只凭公式定论。

建议实验：冻结本地 V85 特征、fold、参数、bin 设置和训练预算，对照 unconstrained / singleton / source-group；先单模配对，再固定 50:50 检验与原模型互补。若新特征无法唯一归入原字段，必须预先规定分组，不能看结果后移动。不要将本地五折结果直接同社区或本地四十折绝对值比较。

### P2：校正收入分组的人群构成

来源：[heuljax 公开 XGB 样例](https://www.kaggle.com/code/heuljax/kps6e09-xgb-sample)，以及[作者讨论](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/742317)。

样例日志 pooled OOF = **0.946308910839**，10 外折、5 内折。作者另在讨论里报告更强的私人版本 XGB CV 0.94652、LR 0.94640；不能把这两个数字算给当前公开样例。

样例不仅使用普通收入 TE。`DonorState` 在 donor 数据内训练 GAM、条件组模型及收入曲线；`CSHIFT` 根据通道概率反求潜在位移，`CCORR` 再减去收入 GAM 分量。`fit_donor_state` 有 donor/query 不相交断言，内层验证和外层验证分别建 donor 状态。

直观解释：某个收入值的历史购买率较高，可能是这个收入组恰好有更多高环保意识、有补贴、低焦虑人群。直接 TE 混合了“收入值自身信息”和“人群构成”。候选思路是先计算已知构成能解释的购买率，再提取该收入组的剩余信号。

这不是简单重复 GAM init_score，也不是任意添加收入×场景交互。它仍需验证是否超出现有 TE 的信息。公开样例包含 173 个特征及多个模块，**没有 composition 单独消融**，因此它是可实现的新假设，尚非已归因的性能突破。外折用于早停也意味着该 OOF 仍是开发评估。

建议实验：固定现有收入 TE、GAM 先验和模型，只加一小组 composition residual / inverse-shift 特征；全部 donor-only，平滑先验与校准也不能接触验证标签。先残差形式，再决定是否有理由测试复杂反演，避免整套复制导致无法归因。

## 3. 最近出现，但不能当作本地新突破

### 重复切分与多模型平均

[Quantum Forge II](https://www.kaggle.com/code/lucifer19/ev-quantum-forge-fusion-ii-partition-bagged-s6e9)记录四套五折划分，最终开发 OOF 0.946398，等权 logit 0.946384，最佳单模 0.946342。相对上一版的增加还同时更换了配方，不能全部归因于 partition bagging。

[Quantum Forge IV](https://www.kaggle.com/code/lucifer19/ev-quantum-forge-fusion-iv-neural-views-s6e9)增加三种神经视图，但最新日志最终仍为 0.946423，新增视图权重全部为零，保留了旧 RealMLP。不能把“更多 epoch、更宽网络、多视图”称为新突破。固定第一次划分进行融合层 gate，也不是整个多切分训练流程的端到端嵌套评估。

本地 v83 三切分平均已 +0.000081585；后续在 v90 上加入重复切分族仅 +0.000018136，未达到推广标准。所以纯粹“更多折、更多种子”降为低优先级。

### 原始生成脚本与收入身份记忆

[源数据作者 9 月 24 日公开脚本](https://www.kaggle.com/code/itzzomkar/the-complete-original-generator-script)：原始 10,000 行、seed=101；焦虑由通勤、家庭充电和充电站等生成，购买得分主要由收入、环保、补贴、焦虑及高斯噪声决定。

这解释了为何加法先验、精确收入值、分箱及 TE 有效。**它不是竞赛再次合成器的代码**，不能还原 668,665 行比赛标签。本地已做原始生成公式和 GAM，公开源码是机制确认，不是本地第一次发现。

[9 月 21 日 source-memory 研究](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/742385)报告 97.9% 训练收入值可在源数据中找到；但强 TE 后加入原始标签只约 +0.00003，income×recipe cell 反而 -0.0004。身份记忆已有证据，直接拼源数据不等于还能有大收益。

[分箱研究](https://www.kaggle.com/code/dariushafshar/s6e9-income-needs-1782-bins-lightgbm-gives-255)把弱 raw LGB 从 0.941522 提至 0.943521；强模型上细粒度修正仅约 0.000024–0.000047。大幅提升主要解决弱基线的信息分辨率问题。

### GitHub 强融合工程

[happyc0der](https://github.com/happyc0der/kaggle-s6e9-ev-purchases)有较完整的 190+ 实验记录。报告最好自身开发 OOF 0.946484/Public 0.94642；更高 0.94649 的公开提交包含外部 public anchor。`scripts_megablend2.py` 最终 headline 仍在同一 OOF 上 hillclimb 后回算；嵌套检查不等于 headline 已独立验证。自身重跑组合另为 OOF 0.946410/Public 0.94636。

[Agnuxo1](https://github.com/Agnuxo1/s6e9-honest-ceiling) JSON 中固定 OOF 矩阵的 meta-nested AUC 0.946419549797，Public 自报 0.94638。这里的 nested 是融合层。它的 47,679 个残差程序搜索没有确认有效程序，但统计功效主要检查约 0.002–0.005 的扰动，不能排除 0.00005–0.0001 的可用空间。用自身预测采样标签得到的“理论上限”不是真实比赛上限。ROADMAP 的 partial pooling、graph、non-mean readout 是计划，不是成果。

[tankajoshi122](https://github.com/tankajoshi122/Predicting-Electric-Vehicle-Purchases)明确只使用原始 10,000 行，约 0.905 的结果不能与比赛 0.946 比较。[ferreret](https://github.com/ferreret/kaggle-playground-s6e9)主要验证 raw→income TE/count 的既有路径；其他入门仓库没有新增强证据。

## 4. 本地重要结论：防止换名字重做

主要依据 `model/experiments.md`、具体诊断结果及冻结报告。历史 Public 数字来自归档，不声称是本轮查询到的当前账户最佳提交。

| 本地方向 | 已记录结论 | 本轮判断 |
|---|---|---|
| v90 / V100 | v90 OOF 0.946372075；V100 0.946398147，历史 Public 0.94635；V100 增量约 0.000027，未达 +0.0001 门槛 | 保留比较主线，开发调权不当独立证据 |
| v83 / v90 split bag | +0.000081585 / +0.000018136 | 非空白方向，不按“新社区技巧”重开 |
| v97 原始公式 init_score | 匹配对照 +0.000059430，但低于 v90 | 有信号，尚无足够组合收益 |
| v98 监督 GAM | 科学指标约 +0.000093500；正式验收超时且日志/哈希违规，47 产物作废 | 不可把无效产物并入模型 |
| 更好的 joint GAM→残差树 | GAM 自身 +0.000149086；最终残差树反而 -0.000060017，0/5 | 先验更准不保证最终模型更强 |
| singleton interaction | -0.000392173，0/5 | 拒绝逐列隔离，不否定来源字段分组 |
| 原始收入先验 m=2 | -0.000010407，0/5 | 不重做固定平滑强度邻域 |
| 收入 rank-4 场景交互 | -0.000152807，0/5 | 不重复低秩交互 |
| source frequency/lift/novelty | 匹配 v96 +0.000025137 | 小信号，未达推广门槛 |
| TabM LinearReLU | 较普通 TabM +0.000046673，仍低于匹配 V85 0.000462568 | 非替换候选 |
| 9/10 RealMLP 周期 cos vs tanh | 同预算 +0.000033289，5/5；仍低于 V85 0.000160925 | 普通周期编码已经试过 |
| 9/10 收入 support geometry | -0.000023830，0/5 | spacing/gap 特征不列首选 |
| HPMN | 有结果文件，但停止时尚无独立复核 | 不作为已确认结论 |

NO_GO 有时意味着小幅正收益不足以达到门槛，不等于机制完全无效。v85 五折匹配基线 0.946062752 与正式四十折 0.946270227 的训练量不同，不能跨表直接减。

另一个目录 `kaggle_s6e9_harness` 的 9/15 transfer 仍是独立冻结三折的早期 raw CatBoost 基线（约 0.9410）：800 轮比 400 轮 +0.000134840，log_income -0.000010059，双种子平均 +0.000049879。它不代表旧赛题主线退化，也不能替代 v90/V100 的强基线判断。

## 5. 必须更新的社区认识

[9 月 25 日伪标签对照](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/743298)：使用含验证标签影响的 all-fold teacher 看似 +0.00032，严格外折训练 teacher 后只 +0.00002。应先审计 teacher 的训练路径，不应把伪标签结果直接列为突破。同帖报告 TabM/RealMLP 融合约 +0.00006，交互 TE、直接追加原始数据等未稳定改善；均为作者报告。

[9 月 17 日更正](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/741447)：该作者之前关于融合层结果的数字更新为 nested LGB -0.000059、bagged hillclimb +0.000066、rank averaging +0.000063、CatBoost stacker -0.000057。旧帖数值必须以更正后为准。其 OOF 单折预测与 test 多折平均不一致的诊断值得保留，但不是已证明适用于本地的根因。

不要把单独 AUC 的标准误当作配对 AUC 差异的标准误。固定数据上的微小差异需要配对分析；多次搜索后的同折置信区间仍不等于独立确认。

## 6. 下一轮建议顺序（尚未执行）

1. 分组约束：最有对照依据，成本低、机制明确，先冻结同特征同 bin 配对。
2. composition 编码：现有强收入 TE 上检验条件构成校正，先小规模可归因特征块。
3. 只有前两项产生稳定增量后，再看与既有神经模型或重复切分组合的互补；不要优先盲目扩深/扩宽/增加 seed。

所有候选沿用本地主线的事前门槛；外层验证标签不能参与编码、teacher 或训练内部校准；记录 pooled OOF、逐折差值、配对区间和完整运行成本。若基模型共同使用外层验证做早停，结果应标为开发结果。最终融合、复核及提交是后续单独阶段。

## 7. 覆盖与局限

本轮通过官方 Kaggle CLI/SDK 获取 52 个主题目录，39 个主题正文及返回的完整评论页；相对 9/13 新增 21 个主题正文全部获取。13 个旧主题正文读取遭遇 429，保留旧归档作背景，不声称全文全部刷新。当前成功返回均无下一页 token。

Notebook 最近和高分各取 100，去重 184 个；重点下载 12 份源代码和 6 份运行日志。GitHub 两个检索分别返回 45、50 项，去重 88 仓库；第二个达到检索上限，不代表穷尽 GitHub。重点检查 8 仓库，保存 README、目录与 commit；对关键实现另按 commit 下载源码。

本轮网络信息截至 2026-09-26，动态榜单和 Notebook 后续可能更新。所有归档文件 SHA256、时间及计数见 `manifest.json`。外部实验本轮没有本地复跑；没有发现公开可复现的 0.94945 方法不等于证明不存在。
