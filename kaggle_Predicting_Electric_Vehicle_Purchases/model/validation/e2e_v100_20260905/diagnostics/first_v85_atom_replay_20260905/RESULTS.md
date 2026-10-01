# 首个 V85 原子真实回放结果

最终监督结果 PASS。同一 CPU PID 24797 继续运行，首个 V85 checkpoint 在 8 分钟观察上限内落盘，未重启训练。

outer_01/v85/atom_01 的保存模型，以冻结 Naji 特征配方及 F 标签重建 TE 后，在固定 100 个 OOF 行与 100 个外层 U 行上的预测均与 checkpoint 逐元素完全一致；两组最大绝对差均为 0，满足预注册 <= 1e-12。

- F 训练行数：521,558。synthetic 目标列只解析 F 标签；所有查询标签行先由 CSV skiprows 排除。原始 external 标签仅用于冻结配方已有的边际先验。
- 查询行数：200；特征数：148；重建矩阵精度：float64；保存模型轮数：1,693。
- 来源、splits、model、prediction SHA 通过；官方 ID、F/query 分离、F 标签 SHA、早停 F 内切分、TE/model seed、特征名、模型参数与轮数均通过。
- 单次监督耗时：37.544208 秒；父子进程树峰值 RSS：7,827,406,848 字节，约 7.29 GiB；数值库与 predict 使用 2 线程。
- 未训练、未计算 AUC、未解析查询标签、未生成新的正式 OOF/test；CPU/GPU/assembler/pipeline 冻结源均未改动。

frozen_config.json SHA：`841cc5185c25e944f870ed05f3299a866d9a895740452aac19627e39a84aeb54`。

evidence.json SHA：`01f364ecb1ad42042c1f94b6c0ab86240c134211643c438176c0414573bf128e`。

最终状态见 result.json；evidence.json 的 `REPLAY_VALUES_MATCH_UNSUPERVISED` 是 worker 中间证据，最终成功以完成资源检查后的 result.json 为准。日志中 LightGBM 载入已有模型忽略构造器 params 的提示不改变预测线程：predict 显式传入 num_threads=2，且处于 threadpool_limits(2) 内。

V80 与 V85 各一次真实保存模型回放均通过，按任务边界不追加逐折回放。本检查不是完整端到端评分、泛化提升或新盲测；完整缓存审计与 V100 复算仍须等待训练和监督成功完成。
