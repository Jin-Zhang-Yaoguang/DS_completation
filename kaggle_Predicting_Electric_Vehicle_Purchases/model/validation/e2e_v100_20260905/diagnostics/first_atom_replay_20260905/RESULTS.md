# 首原子真实回放结果

最终监督结果 PASS。outer_01/v80/atom_01 的保存模型，以冻结特征配方及 F 标签重建 TE 后，在固定 100 个 OOF 行与 100 个外层 U 行上的预测均与 checkpoint 逐元素完全一致；两组最大绝对差均为 0，满足预注册 <= 1e-12。

- F 训练行数：521,558。只解析 F 标签；所有查询标签行先由 CSV skiprows 排除。
- 查询行数：200，特征数：113，保存模型轮数：2,057。
- 来源、splits、model、prediction SHA 通过；官方 ID、F/query 分离、F 标签 SHA、早停 F 内切分、特征名、模型参数与轮数均通过。
- 单次监督耗时：10.449704 秒；父子进程树峰值 RSS：2,542,616,576 字节，约 2.37 GiB；数值库与 predict 使用 2 线程。
- 未训练、未计算 AUC、未解析查询标签、未生成新的正式 OOF/test；CPU/GPU/assembler/pipeline 冻结源均未改动。

frozen_config.json SHA：`251c0b6c8a239416ca094fd721caab60dfaa3994bf1b18fbb3916b13437c58d1`。

evidence.json SHA：`ea22466c5812cf49c8c45682445f63b3dc265e527bf4ebacb3db87df56ca4f4a`。

最终状态见 result.json；evidence.json 的 `REPLAY_VALUES_MATCH_UNSUPERVISED` 是 worker 写出的中间证据，最终成功以完成资源检查后的 result.json 为准。

日志包含 LightGBM 在载入已有模型时忽略构造器 params 的提示；预测调用显式传入 num_threads=2，并处于 threadpool_limits(2) 内，不改变保存模型的训练参数。

本检查只证明一个真实原子、200 个固定查询的模型序列化与特征重建一致。它不是完整端到端评分、泛化提升或新盲测，也不能替代剩余原子与完整 V100 复算。
