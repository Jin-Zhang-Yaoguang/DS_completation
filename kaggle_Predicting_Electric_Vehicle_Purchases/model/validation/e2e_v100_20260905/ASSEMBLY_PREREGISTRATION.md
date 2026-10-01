# 完整缓存装配、独立复算与评分预注册

本文件和 `assemble_e2e.py` 是独立补充，不修改运行中的CPU/GPU冻结代码或配置。先写本协议，再实现/测试。数据已用于历史开发，结果属于固定配方的端到端复核，不是新盲测。

## 先决条件

- 全部5个outer各有V80/V85/CTBoost，合计15份cache与manifest，同时要求GPU的`GPU_COMPLETE.json`和最终`gpu/remote_output/GPU_RUN_RESULT.json`成功状态、CPU的最终`supervisor_state.json`与`cpu_budget.json`成功状态。
- 缓存齐全不等于监督器成功：CPU须`CPU_CACHE_COMPLETE`、400原子、配置SHA正确且累计≤43200秒/RSS≤24GiB；GPU须`GPU_CACHE_RUN_COMPLETE`且最终`BEFORE_COMPLETE`预算检查、执行<7200秒/进程树RSS≤24GiB。最终状态/预算文件也纳入输入snapshot；失败或仍RUNNING绝不评分。
- 未齐全时只返回`NOT_READY`和缺失路径，不读取预测或标签，不计算任何真实partial分数。
- 装配前冻结独立assembler/test/本协议/公共paired_auc源码SHA，以及既有CPU/GPU configSHA、CPU splitsSHA。完整缓存齐备后再冻结精确cache/manifest快照，记录所有源文件SHA。
- GPU来源固定为已单次推送version1的`gpu/revision_01/`，同时核对`gpu/PUSH_RECEIPT.json`的成功返回、kernel身份、config与bundle SHA。初始`gpu/frozen_config.json`属于未启动实现，禁止误用。
- 对照官方train.csv的原始行ID逐数组核对train_idx/valid_idx/train_id/valid_id/atom_fold；CT折划分必须与CPU冻结splits的CT折一致。
- CPU每个原子prediction、model、manifest SHA均核验，OOF/valid均由40个原子重新拼接；GPU每个atom和fullfit SHA均核验，CT OOF按float32重建，U的五折均值/fullfit分别重建。三家族的最终cache必须逐元素一致。

## 元模型装配

- 每个outer只把T标签传给现有`fit_v100_meta`，训练所有ECDF/权重；U标签不在接口中。
- A保持原完整V100算法：V80/V85 40折均值→V90两成员元融合→CTBoost全量T-refit的V100元融合。
- B只替换CTBoost对U的预测为T内五个fold模型的均值；所有训练侧OOF、变换和权重与A相同。
- V90网格0..1步长0.05，误差≤1e-15视为并列，优先最接近0.5，再取更小值；V100网格0..0.5步长0.025，精确并列取更小CT权重。
- 各outer先保存A/B预测、U身份、元权重和输入快照SHA；五个outer全部完成才拼接全量OOF。保存的不是实际test预测，不生成submission。

## 独立复算与评分

1. `verify`使用独立写出的ECDF/两层权重公式，不调用原元模型fit函数，重建各outer A/B预测。与正式装配向量最大绝对误差≤1e-12；V90五个权重及CT最终权重必须相同。所有输入SHA再次核对。
2. `score`只有15份cache完成、五个装配输出完成且本次独立复算PASS后才能读取U标签计算分数。使用公共`model/research_runtime/paired_auc.py`，主要指标为B−A配对AUC、5个outer方向；另以sklearn ROC AUC复算整体与逐折AUC。
3. 固定研究晋级门槛：`delta >= 0.0001`且5/5正向并且独立复算通过。
4. 固定提交候选资格门槛：同协议`delta > 0`且5/5正向并且独立复算通过。这里只能产生“可另立实际test重建合同”的资格；本缓存没有比赛test预测，`allowed_for_submission=false`。
5. 条件影响函数CI只描述给定预测的样本不确定性，不覆盖训练重叠/历史开发/选模过程。历史V100 `0.9463981465`只保留作参考，不用于新A/B差值或晋级。
6. 缓存损坏、哈希漂移、身份错误、缺折、非有限值、复建不一致立即失败；不得删除不利折、反调权、使用Public/test标签或降低门槛。

装配与复算各预算30分钟、CPU最多2线程、RSS16GiB；不计C01，不训练，不提交。超预算保留失败并等待父任务处理。
