# V12A terminal branch guard

父策略是 Round 3 第一名 `r002_learned_router_topday_animal_throttle`。实现上继续运行同一冻结的 `learned_router` 完整专家，并复现 r002 的动物品节流；新增规则只决定该节流是否生效，以及最后一个可行动回合是否补遗漏清仓单。

## 机制

1. `step=72` 仍由冻结 Router 在 V1/V2/V5/V8 四个完整专家中选择一个，V12A 不改路线。
2. 仅第 10/17/24 天、且 Router 选择 V5/V8 时，才考虑把已有 EGG/MILK/WOOL SELL 减半。
3. 再按本局实际解锁商店逐商品判断需求洞：MILK 只在 PIZZA/ICE_CREAM/SMOOTHIE 已出现时节流，WOOL 只在 YARN 出现时节流，EGG 只在 BAKERY/BRUNCH 出现时节流；没有对应商店的动物品保持父销量。
4. 同回合存在 DROP/PLACE、具备商店需求的动物品总出售量小于 4，或节流后预计仓库占用超过 90 时，不节流，原样返回父动作。
5. agent 实际在 step 0–718 被调用；仅最后一个可行动回合 step 718 使用空闲市场槽补卖 shed 中父策略未覆盖的可售库存，不改已有订单顺序，不超过 10 单。step 717 明确不触发。
6. 任一残差异常立即返回本回合父动作。无价格下限、无 `premium_floor_guard`、不修改 farmer/hands。

## 已知风险

- Router 的 V5/V8 分支标签来自一次性 step-72 选择；若 Router 选择错误，新守卫只能减少残差伤害，不能修复路线选择。
- 商店需求门来自引擎的公开 `SHOPS` 商品映射；它不估计共享市场中对手的未来销量，仍可能错判最优出售时点。
- 仓库阈值 90 是保守规则，不是经正式留出集优化的参数；可能错过部分 r002 收益。
- 最后一个可行动回合的补单可能以较差价格成交，但只处理父策略遗漏库存，范围小于提前扣留商品。
- 小规模 smoke 只验证闭环、方向和动作边界，不构成上线收益证据。

## 验证

本地通用 registry 可直接追加 `registry_entry.json`；其 `make_agent()` 每次返回独立的 episode-local 实例。

```bash
PYTHONPYCACHEPREFIX=/tmp/kaggriculture-v12a-pycache \
  .venv/bin/python -m unittest \
  kaggle_Kaggriculture.model.v12a_terminal_branch_guard.test_main

PYTHONPYCACHEPREFIX=/tmp/kaggriculture-v12a-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v12a_terminal_branch_guard.smoke

PYTHONPYCACHEPREFIX=/tmp/kaggriculture-v12a-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v12a_terminal_branch_guard.build_submission
```
