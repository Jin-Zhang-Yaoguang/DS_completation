# Predicting Electric Vehicle Purchases：赛题讲解与社区补全

调研时间：2026-09-13 22:18，Asia/Taipei。比赛状态、主题及代码以本次 Kaggle CLI/SDK 返回为准；公开 OOF 为作者代码运行结果，不是本地重训成绩。Public 分数除榜首外按作者正文披露，未逐一查询对应提交。

## 赛题是什么

这是 Kaggle Playground Series Season 6 Episode 9，目标是根据个人属性预测 `Will_Buy_EV=Yes` 的概率。官方将目标描述为电动车兴趣预测，因此不能将标签直接解释为已核验的真实购车交易。

- 开始：2026-09-01；截止：2026-09-30 23:59 UTC，即台北时间 10 月 1 日 07:59。
- 评分：ROC AUC；比较随机一名正类与一名负类谁的预测分数更高，排对计1，并列计0.5。AUC 0.946不是94.6%的分类准确率。
- Playground练习赛，前三名获得Kaggle周边，不授予竞赛积分或奖牌。比赛尚未结束，当前榜单不是最终成绩。
- 本次CLI榜单首位 Chris Deotte，Public AUC **0.94672**。其9月3日论坛评论的单模CV0.94627/融合CV0.94639只是历史自报，不能解释9月11日榜首提交的当前训练配方。

来源：[官方概览](https://www.kaggle.com/competitions/playground-series-s6e9/overview)、[榜单](https://www.kaggle.com/competitions/playground-series-s6e9/leaderboard)、[历史评论](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739049)。榜单快照见 evidence/leaderboard.txt。

## 数据与任务难点

本次重新读取本地官方CSV：train为668,665×15，test为286,571×14。输入13个特征，另有id和训练标签。Yes为116,779条（17.4645%），No为551,886条；训练与测试全部字段无缺失。

| 属性 | 字段 |
|---|---|
| 人口经济 | 年龄、性别、年收入、城市类型 |
| 出行用车 | 日通勤距离、已有汽车数量、当前车型 |
| 充电条件 | 家附近及工作地附近充电站数量、能否家充 |
| 态度政策 | 环保关注等级、补贴、里程焦虑 |

提交CSV两列：`id,Will_Buy_EV`；按测试ID提供Yes概率，不输出Yes/No硬标签。全部猜No虽有82.54%准确率，恒定预测AUC仍为0.5。

数据有两层：公开的1万行 `EV Adoption Behavior and Range Anxiety` 源数据，以及比赛再次合成的训练/测试数据。源数据本身的生成公式是社区研究对象，不能把本题当真实消费者调查或把源数据还原等同于比赛标签还原。

本次重算：无补贴组Yes率0.5757%，有补贴组27.4695%。这是合成数据的条件关联，不是补贴的因果效应。收入的精确取值、分箱、重复频率也包含明显预测信息。普通树模型往往把数值理解成连续趋势，而本题强方案还需要识别离散取值的购买率变化。

目标编码（TE）可理解为：把某个收入值或分箱替换为训练样本中的购买率，并对小样本作平滑。三重TE同时提供auto、10、100三个平滑尺度，让模型兼顾细粒度和稳定性。训练行必须用内层折外统计，外层验证和测试只用外层训练标签。

数据细表见上一层 data.md；来源：[官方数据](https://www.kaggle.com/competitions/playground-series-s6e9/data)、[源数据](https://www.kaggle.com/datasets/itzzomkar/ev-adoption-behavior-and-range-anxiety)、[生成公式讨论](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739303)。

## 社区方案：哪些有实质进展

### 1. Naji XGBoost：本轮值得优先复现的强单模

[源码](https://www.kaggle.com/code/najiama/xgboost-triple-te-dynamic-pruning-lb-0-94639)，最新运行UTC 09-12 23:19。

- 十折运行日志最终OOF **0.94624**，正文Public **0.94639**。
- 多尺度收入键、数字位、频次、原始数据目标统计；三重嵌套TargetEncoder；depth=4的XGBoost。
- 题名“Dynamic Pruning”在当前源码实际为一份手工固定的88项删除列表，按作者说法由此前gain筛选得到。没有看到每个外折内独立重新选这份列表的流程，因此不能把当前OOF当完整特征选择程序的无偏验证。
- 当前数字位生成仍使用浮点负指数整除。复现原配方与修正数字位应作为两个独立实验，不能把两者同时改动的差异归因给XGBoost。

### 2. Four Feature Views：有训练、有OOF的表示多样性

[四视图训练源码](https://www.kaggle.com/code/megayak/s6e9-four-feature-views-one-ensemble-lb-0-94639)，UTC 09-12 05:54。

日志实测：A=0.946264，B=0.946258，C=0.946223，D=0.946077；融合 **0.946339**，等权 **0.946337**。正文Public **0.94639**。

A是三重TE+多尺度键+数字位LGBM；B在同样特征上换XGB；C移除数字位，加入收入/通勤邻域购买率、原始数据频率比；D移除精确收入键，换成10/50/500/5000分箱并加入邻域统计。四模型同十折，导出各自OOF/test，训练特征使用内层交叉拟合。

这说明可研究“不同表示的边际贡献”，但不能仅凭相关系数认定互补。相对A的融合增量只有0.000075；0.3/0.3/0.2/0.2与等权只差0.000002。源码没有独立验证视图设计及权重选择的全流程。外折内排名归一化也使其分数口径与直接概率OOF不同。

[0.94645版本](https://www.kaggle.com/code/megayak/s6e9-0-94645-four-feature-views-beat-the-blend)另混入70%的公共预测，正文明确试过20%、30%、50%等权重；不能将0.94645归为四视图自身的独立验证成果。

### 3. RealMLP：更新后的神经模型证据

[RealMLP PyTorch](https://www.kaggle.com/code/yekenot/ps-s6-e9-realmlp-pytorch)，UTC 09-13 01:02。

本次官方运行日志的五折OOF为 **0.94601**，高于9月10日归档日志0.94587。最新训练循环约9分21秒；PBLD周期数值嵌入、8成员、256×3隐藏层、三类重要交叉及TE、2 epochs。

更新不能归因给PBLD单一机制，因为特征等也发生变化。源码即使 `use_early_stopping=False`，仍保存验证分数最好的epoch并输出 `best_val_probs_`，因此这是开发OOF，不是未参与选epoch的独立确认分数。值得用固定特征和内部选epoch的方式检查其对强树模型的增量。

### 4. 新架构：RPU与HiRGE-Net

[RPU论坛](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/740739)、[源码](https://www.kaggle.com/code/ern711/rpu-a-flexible-relational-pattern-unit)：9月11日台北时间公开。独立特征变换→与可学习参考模式比较→小神经网络。作者报告RPU上接XGBoost可增加约0.0005，但没有提供同口径强基准胜出证据；本次日志只有转换信息，没有完整训练成绩，属于探索实现。

[HiRGE-Net](https://www.kaggle.com/code/tamerlanomralinov/s6e9-hirge-net-and-doubly-nested-maxcv-stack)：支持度门控、四个语义残差专家与8成员神经头。正文自报神经单模OOF0.942010、CatBoost0.945322、嵌套融合0.945508；需要附带的数据集脚本才构成完整训练环境，本次未扩展审计全部依赖。没有超越本轮强公开单模的证据。

旧路线[Replication-Aware Newton Boosting](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739910)依然是研究候选，先前公开日志0.94538455；本轮未重新下载该模型日志，没有把旧成绩写成新突破。

## 9月11—13日新增的研究发现

### 数字位特征的浮点错误：已在本地复核

[740824原帖](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/740824)指出 `(x // 0.1) % 10` 不是可靠的十分位提取。23.4得到3，5.0得到9。本地全训练集复核，与正确十分位不同的行数 **599,298 / 668,665 = 89.626%**，与帖子一致。

当前通勤数据精度为1位小数，可先 `scaled=np.rint(x*10).astype(np.int64)`，十分位取 `scaled%10`。保留原浮点伪影、正确十分位、是否整数三个解释不同的候选分别作消融。语义修正不是收益保证，旧错误特征仍可能是有用的取值映射。

[741117新帖](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/741117)仍把负指数数字位全部解释为生成器指纹，报告数字位+频次+Triple TE的LGBM Public0.94590；该解释需要结合上述修正看待，属于已有配方的整合，不是新的高分上限。

### OOF与测试平均的差异：值得验证的新归因

[740769及9月13日评论](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/740769)：普通K折OOF每行只由一个折模型预测，test由K个折模型平均。噪声大的成员在test平均后可能改善更多，导致单次OOF上学到的融合权重与部署时不匹配。

评论作者报告重复另一套折划分后，精确值TE路线+0.00019，另一损失路线+0.00006；两条路线存在其他差异，尚未隔离TE的因果贡献。其六成员折外选权仅+0.00006。可测试“每个成员重复交叉拟合再融合”，需先冻结同样训练预算与比较方法。

[11次提交台账](https://www.kaggle.com/code/georgymamarin/s6e9-what-the-board-paid-for-eleven-submissions)对照特征改变与融合改变在OOF/Public的不同表现，提供归因线索；单作者台账不是“所有融合必然无效”的证明。评论的KS/CDF差异也不能替代带标签的折外边际增益。

### 分组AUC分解和所谓上限

[740775](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/740775)按环保×补贴×焦虑分组，作者报告组内正负对占6.2%、AUC0.743；跨组占93.8%、AUC0.960。分组isotonic/Platt校准均为负增量。

这支持先定位跨组和组内错排，不支持宣布已达到理论最优。几个模型结果相似、或按自己的预测概率重新模拟标签，只能检查自身假设，不能证明真实数据不存在额外信号。全局严格单调映射不改变AUC；isotonic可能制造并列，分组单调映射还会改变跨组顺序。

### Lexsort高分标题：机制陈述存在错误

[Lexsort原Notebook](https://www.kaggle.com/code/taeyangg4/s6e9-094649-multi-paradigm-lexsort-master)正文报告Public0.94649，但其表中基础anchor已经0.94649，打散并列后仍是0.94649。代码读取上游预测并进行90/6/4组合、边界处理与lexsort，没有在该Notebook训练全部上游模型。

[最新跟随Notebook](https://www.kaggle.com/code/chinzorigtganbat/s6e9-does-breaking-ties-help)标题/正文报告0.94650，明确默认模式直接导出下载的公共结果；独立anchor和anchor_lexsort模式没有此次评分。因此0.94650不是打散并列产生增益的对照证据。

数学上，lexsort能保持原来不并列的顺序；对原来并列的正负样本，次模型可能把0.5变成1，也可能变成0。随机破并列期望收益为0。并列行数不是并列正负样本对数，也不能直接折算AUC增益。源码所谓“数学保证AUC提升”错误。训练观察到某收入区间全0或全1，也不能保证测试标签确定如此。

## 建议的研究顺序

1. **低成本核查表示**：正确数字位、浮点伪影、整数标志分开；检查当前强基准已包含哪些TE和邻域表示。
2. **优先复现Naji XGB并做同特征对照**：冻结删除列表或在训练内部筛选，不能同时改编码、引擎和折数后归因。
3. **测试表示互补**：以现有强模型加一个缺少精确收入键的视图，使用独立元验证比较最佳单成员、等权及拟合权重；不照搬公共0.94645混合配方。
4. **RealMLP更新与重复交叉拟合**：分别回答神经表示是否补错、OOF/test平均差异是否导致权重偏移，避免混为一次实验。
5. RPU、HiRGE、复制感知树暂列探索；生成公式反演、强制边界、Public扫权重没有足够新增证据。

本轮仅调研、数据核验与资料归档，没有训练新模型、改动现有实验、提交或发布。当前项目既有NO_GO结论不因社区标题更新而自动撤销。

## 覆盖范围与可追溯性

- 官方SDK按new分页20+11+0，31个当前主题；相对9月10日列表新增6个ID，739689不再出现在本次列表，不能据此认定删除。
- 初次4个旧主题遇到429，稍后顺序重试成功；31个正文均已保存。评论递归返回及分页状态见manifest，不包含图片OCR、私有和已删除材料。
- Code区最近运行100项、按分数排序50项，去重数量见manifest；抽查9份当前公开源码、4份运行日志。排序API没有返回具体score字段，因此不把标题分数当API核验分数。
- 最新运行时间不是首次发帖时间。源码pull与output日志分开获取，无法保证上游在两次请求之间绝无更新；保留快照与SHA-256供核对。
- 继承的背景参考是项目9月10日README及本地data.md；新的核心结论均对应本次API、源码、日志或本地复核。未对所有公开OOF逐行重算，也未证明所有上游选模过程无偏。
