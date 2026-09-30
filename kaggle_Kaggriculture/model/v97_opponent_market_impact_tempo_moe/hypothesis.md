# V97：对手市场冲击—槽位节奏 Hierarchical MoE

- `strategy_parent=null`；V76 只作冻结强度比较器。
- 候选只使用公开 market inventory/price、自身上一回合已知订单、公开商店与 step，维护逐商品冲击残差；不读取对手私有库存或当前动作。
- 上层 Router 将逐商品状态分成 `opponent_buy_pressure`、`opponent_sell_pressure`、`town_demand_pressure`、`uncertain`；下层选择 `same_slot_compete`、`one_step_wait`、`demand_boundary_preempt` 三个出售节奏专家，最后由候选自有库存执行器封顶。
- 主消融关闭冲击残差，只按候选固定出售时钟执行。任何完整 V76/历史 agent 调用、父代默认动作后处理或 Replay 动作流拼接都直接判同谱系补丁并终止。
- 构造前先证明：在 synthetic 对局中，扣除自身订单和规则固定消费后的残差与对手上一回合真实买卖方向有正向预测力；若 balanced accuracy 不高于多数类基线 5pp，整条谱系在写提交模型前淘汰。
