# R18 semantic-bundle restore HMoE

R18 是独立的规则/浅树 Hierarchical MoE 候选，`STRATEGY_PARENT=None`。它保留五个完整生产专家、
首店 Router、cap11、商品出售控制器和 step696 结算禁购，并试验语义目标锁、同格唯一 owner、
确认式有限作物补种链及 day27 资产恢复。

## 结果

- 静态与机制测试：22/22 通过；
- `main.py` SHA256：`55fa7ba1aa6f8791cf208441b3d9ed740e6f99e48038dd3c71580d2e93bf2511`；
- 唯一 seed7100/router/seat0/idle kill-fast：bank 91,959、方向移动 3,981、终局资产 40；
- 719 calls，runtime/schema/invalid/漏水检查均为 0，但终局仍有 5 个 weed；
- 决策：`NOT_GOLD_KILLFAST_REJECT`。

R18 未运行 P2、P3 或 Replay，也未注册金牌。`evaluate_killfast.py` 只复用统一评测检查，不属于
Kaggle 提交包；提交包只能包含候选运行所需源码。

