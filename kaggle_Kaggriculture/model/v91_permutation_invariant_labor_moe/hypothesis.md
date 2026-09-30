# V91：置换不变劳动力匹配 Hierarchical MoE

## 原创身份

- `strategy_parent=null`；V76 仅为冻结强度比较器。
- 单条公开强轨迹只提供每回合“任务集合”和参考状态，不提供可调用 agent。
- 与 V88 不同：V88 把历史 hand index 当作固定身份并在失败后恢复；V91 每回合先重建当前 worker 与任务槽的对应关系，不存在历史 hand 身份。

## 机制

1. `task_router` 把参考回合拆成 farmer 固定任务与 hand 任务集合；
2. `matching_expert` 以当前位置、携带库存、目标位置和动作前提构造 worker—task 代价；
3. 对全部合法/可恢复组合做确定性全局贪心匹配，每个 worker 和任务最多使用一次；
4. `execution_expert` 执行已匹配且合法的任务，冲突任务进入 `safe_idle`；
5. 市场任务保留参考计划，不调用历史策略。

主消融按历史 index 直接分配 hand 任务，但共享同一合法性和库存仲裁器。构造前要求 full 相对消融 MCU > 0、正翻转多于负翻转、至少 8 局发生真实重分配、面板 >= 60%、对 V76 >= 50%、灾难率相对 V76不恶化超过 1pp。

