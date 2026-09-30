# V114 Day-SMDP Hierarchical MoE PPO

V114 是 `strategy_parent=null` 的独立强化学习谱系。它从 V113 Stage17–37 的失败证据中
学习，但不继承 Stage37 checkpoint，也不把任何历史规则 Agent 作为在线动作源或回退。

完整预注册方案见 [PPO_V4_PLAN.md](PPO_V4_PLAN.md)，当前执行状态见
[run_state.json](run_state.json)。源码、测试和训练入口全部保存在本目录；训练数据、
checkpoint 和逐局证据统一保存在 `model_data/v114_day_smdp_hmoe_ppo/`。

当前阶段是 V4-0：建立日级/事件级 SMDP Manager、稳定职责专家、有界 Residual PPO、
三 critic、动态对手联赛和可复现 seed ledger。未通过全部 Development 与一次性
Gold-Blind Confirmation 前，V114 不是金牌模型，未经用户授权不得提交 Kaggle。
