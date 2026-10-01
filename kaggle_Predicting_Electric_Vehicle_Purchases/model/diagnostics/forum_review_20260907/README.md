# S6E9 论坛今日总结（2026-09-07，台北时间）

结论：两篇今日新技术帖；一项值得小规模验证的新机制，但没有新证据支持直接替换 V100。另有一份旧帖今天补充的原始数据重建代码。

## 1. Replication-Aware Newton Boosting

- [论坛](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739910)，Ern711，今日13:56发布。
- [代码及运行日志入口](https://www.kaggle.com/code/ern711/replication-aware-newton-boosting)。先按全节点Newton gain选48个候选，再在16个随机互斥子组中按更新方向一致性、候选排名与稳定性选分裂；固定replication_weight=1。这是分裂选择正则化，不是CT五折推断平均，也不是独立验证集。
- 当前可获取日志：五折 OOF **0.94538455**，折均值0.94539393，T4约9039秒。不同切分seed21，不能把它与本地seed42分数作配对增量；也没有本地独立复现或同引擎关闭replication的对照。
- 建议：中等研究优先级，低上线优先级。若继续，只先在相同自定义树实现、特征、折、候选阈值、叶约束下对比分裂选择规则。纯Newton控制必须绕开replication资格过滤，否则仅把weight设0仍不是纯Newton消融。控制数值阈值只有64，避免将分辨率或引擎差异误归因于replication。通过后再与V85/V100比较。

## 2. LGBM、XGB、Voting、TabM复盘

- [论坛及作者补充](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739897)，今日11:10发布，11:30补充。
- 作者报告最佳单LightGBM Public0.94572，LGBM+XGB+TabM为0.94565。最新补充改用最强单模比较：LGBM OOF0.945401513，95/5 LGBM+XGB为0.945401646，仅+0.000000133、3/5正向；测试的TabM组合都低于最佳LGBM。
- 价值在纠正比较基准：低相关性不能保证有效融合。不是新的优胜配方，不建议据此重新调TabM混合权重。
- 本地新记录也已核对：LinearReLU TabM五折OOF0.945600184597，仍低于同切分V85的0.946062752333。该帖子不提供重开已关闭本地方案的证据。

## 3. 旧帖今日新增：原始数据精确重建

- [新增回复](https://www.kaggle.com/competitions/playground-series-s6e9/discussion/739303#3521813)，今日15:47，链接到[完整重建代码](https://www.kaggle.com/code/yhay81/exact-reconstruction-of-the-ev-source-dataset)。
- Notebook报告RandomState(101)重建原始10000行、15列、150000单元格，包含标签与缺失值，零差异。当前只静态阅读，未本地运行核验。
- 代码明确排除“重建比赛train/test”的说法：比赛还经历另一个生成过程。适合补齐源数据机制认知，不能直接恢复测试标签或据此重开旧原始标签增强方案。

## 不列为新方案的更新

GPT-6-Astra话题今天只是询问使用体验；Simpson悖论和5km聚集帖今天的新增评论没有提供新算法或可检验结果。

## 范围与边界

官方CLI读取最新发布/最近活跃各20项；读两篇新帖，以及最近活跃前8帖中相关正文和嵌套回复。今天按台北时间从UTC9月6日16:00算起。检索截至时间见evidence.json。搜索引擎正文与浏览器加载失败后使用官方SDK正文接口，不以搜索摘要代替今日事实。公开算法数值来自作者与运行日志，未当作本地复现。账号最佳已刷新为V100 Public0.94635；公开OOF与该Public分数不直接比较。本次未训练、未提交。
