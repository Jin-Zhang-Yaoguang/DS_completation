# V98：随机扰动—状态图生产 Hierarchical MoE

- `strategy_parent=null`；提交包不含 Replay 动作流，不调用任何历史 agent。V76 只作强度比较器。
- 每回合从当前地块构造可达任务图，任务节点为 `DIG / PLANT / WATER / HARVEST`，边由地块前置状态定义；全局任务 Router 按距离将互斥任务分配给 farmer/hands。
- 商店需求 Router 在 `feed_grain`、`quick_root`、`demand_perennial`、`premium_melon`、`terminal_quick` 生产专家之间选择作物；市场控制器从当前 shed、seeds、money 和土地状态自行生成 SELL、BUY_SEED、HIRE、BUY_LAND。
- 主消融关闭商店 Router，使用固定坐标哈希作物组合；任务图、市场控制器和执行器保持相同。
- 预构造使用 16 个全新 synthetic seed、6 个冻结对手、双座位、full/ablation/V76 共 576 局；要求四类生产专家中至少三类各覆盖 8 局、MCU >0、正翻转多于负翻转、PanelScore ≥60%、直接 V76 ≥50%、灾难率恶化 ≤1pp、零错误。

