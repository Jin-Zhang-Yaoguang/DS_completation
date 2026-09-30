# V31 决策

结论：`REJECT_MECHANISM_INERT_WITHOUT_CONSUMING_DEVELOPMENT`。

冻结的机制烟测执行 2 个内部种子、双座位、共 4 场 V31 对 V21。影子每场最终连续符合 718 步，`shadow_faults=0`、`shadow_update_errors=0`，说明私有状态影子能够精确复现 V21；但 4 场合计安全重排为 0，候选与父代逐局金币差均为 0。

V21 当前的等量竞争冲击排序在 V21 镜像场景已经把可利用 SELL 顺序吃完；严格影子门又会在非 V21 对手上回退，因此该机制没有可观测动作支持，不满足 `loop_model.md` 的真实性门。按预注册直接淘汰，不读取官方 Replay Development，也不消费 Confirmation source。

代码和自包含包保留用于审计，但不得加入 `golden_model.md`，不得提交 Kaggle。
