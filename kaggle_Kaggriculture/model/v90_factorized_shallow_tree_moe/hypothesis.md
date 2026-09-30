# V90：因子化浅树行为克隆 Hierarchical MoE

## 原创身份

- `strategy_parent=null`；V76 只作冻结强度比较器。
- 训练数据为 lucaskna submission `55803928` 的 50 场公开胜局，episode 是最小隔离单元。
- 运行时不包含 Replay 动作流、案例检索器或历史完整 agent；只包含离线训练后导出的决策树节点与动作标签。

## 架构

1. `regime_router`：step 72 后按首个公开商店选择一个专门模型；此前使用 opening/global 模型。Router 本身是公开规则，不学习 seed 或私有状态。
2. `unit_expert`：角色条件浅树，根据时间、actor index、位置、脚下 tile、携带物、农场资产、商店、种子和棚库存预测 farmer/hand 动作。
3. `market_expert`：同一 regime 下的市场浅树按 10 个 market slot 分别预测订单，再按槽位顺序组合。
4. `conflict_executor`：候选自有的合法性、种子总量、PICKUP 总量和 action schema 仲裁器；不决定生产组合。

主消融关闭首店 Router，所有时段都使用全局单位树和市场树。full 与消融共享特征、训练数据和安全执行器。

## 训练与门控

- 全局模型先做 5-fold GroupKFold，group 为 episode；报告单位动作 accuracy、市场槽 accuracy、非空市场槽 accuracy。
- 最终模型只在 OOF 评估结束后用全部 50 个训练 episode 拟合；Development/Confirmation episode 不进入训练。
- 树最大深度 18、最大叶节点 4096、最小叶样本 3；不看闭环结果调参。
- 构造前要求 576 局零错误；full 相对 global-tree 消融 MCU > 0、正翻转多于负翻转、PanelScore >= 60%、对 V76 >= 50%、灾难率相对 V76不恶化超过 1pp。

任一门失败即淘汰 N 谱系，不在同一版本调树深、叶数或类别权重。

