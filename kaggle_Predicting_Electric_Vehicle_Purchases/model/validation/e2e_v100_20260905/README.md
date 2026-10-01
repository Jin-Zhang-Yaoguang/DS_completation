# 完整 V100 端到端复核缓存预注册

状态：`ROOT_REVIEWED_CPU_RUN_AUTHORIZED`。用户已授权恢复研究；父任务已独立审查CPU实现和两层元模型标签边界，并明确授权在静态合同、合成测试、freeze/preflight通过后启动唯一顺序CPU监督器。GPU由父任务负责独立预注册、审查和执行，CPU状态不代表GPU状态。

- 目的：建立可复用的外层安全基础缓存，保留实际 V100 的 V80 / V85 / CTBoost 三原子家族与 V90→V100 两层元模型。
- 外层：5-fold StratifiedKFold，shuffle=True，seed **42437**。本数据已经用于开发，这不是新盲测。
- 每个外层训练 T 内：V80 40-fold seed104395303；V85 40-fold seed42；CTBoost 5-fold seed42；三路 OOF 均在 T 内重新生成，严禁加载历史 OOF作为新训练侧特征。
- 早停：每个 LGB 原子 fit F 内90%/10%一次固定分割，seed=`424370000+outer*1000+family_offset+atom`，V80 offset=0，V85 offset=100；只在该10%块选轮数，然后在整个F重建严格TE并按固定轮数无eval_set训练。TE内部5折和原家族模型种子保持。外层U标签不传给训练函数。
- 标签允许用于预先的分层划分；训练/早停/TE/权重只能使用相应训练块标签。静态无标签统计保留原配方的 train+test features-only 范围，A/B共享；original10k仅提供冻结原始先验。
- CPU累计预算12小时，最多8线程，peak RSS24GiB，一个全局flock，仅按缺失原子checkpoint续跑。每个外层单独输出，缺CT时只能报告CPU_CACHE_COMPLETE，不能输出完整V100分数。
- GPU单独私有Kaggle notebook，CTBoost0.1.58，固定1426树，执行预算≤2小时；其执行授权和状态由父任务管理，不提交比赛。
- A保持V100的CT全量T-refit；B只将对U的CT预测改成T内五原子模型平均；两臂共享原子OOF、V90及V100拟合状态和权重。B是待验证合同假设，不能据test KS反向调权。
- 与历史V100相比，新原子实际训练量最多为整体数据的`0.8*0.975=78%`，早停边界也变更。新旧OOF不可直接相减声称改进；只以本次新A/B配对比较为主。
- 验收：完整40/40/5覆盖、输入/行ID/seed/code hash、无标签泄漏隔离测试、概率有限、checkpoint一致。晋级仍由父任务冻结门槛决定。提交预算0，不修改历史文件或共享registry。

## 命令边界

`freeze`只生成固定配置/分层索引；`preflight`只核环境和哈希；`test_cpu_runner.py`只做小合成测试。父任务已授权的`cpu-all`顺序完成5个outer×2个家族×40个原子；`cpu --outer 1 --family v80`仅供同配置单范围恢复，不得与监督器并跑。`assemble-cpu`只从原子checkpoint重建CPU缓存。纯数组`fit_v100_meta`函数必须在三家族完整、CT来源核验后才接入正式评分。

所有路径、运行范围和SHA在`frozen_config.json`中冻结。`CPU_COMPLETE`不代表GPU完成、端到端评分完成或任何晋级。
