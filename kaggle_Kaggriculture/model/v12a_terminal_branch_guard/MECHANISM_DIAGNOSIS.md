# V12A frozen_v3/v4 机制诊断

结论：frozen_v4 对 `baseline_v8` 的 -2.78pp 回撤不是 shed headroom 或 step718 fill 造成的；两者在 v3/v4 共 576 条候选 screen 轨迹中均零触发。可复现回撤来自“按已解锁商店逐商品选择性节流”的 WOOL/MILK 路径。删除整个 shop-product gate 能精确修复关键失败源，因此首选因果修复为 `v12a2_no_shop_gate`。

## W→L 定位

| 对手 | source | 席位 | r002 margin | V12A margin | 首个动作分歧 |
|---|---:|---:|---:|---:|---|
| baseline_v8 | 2026-08-18 / episode 94345544 / seed 1356333904 | 0、1 | +1610 | -6 | step 412；V12A `SELL WOOL 2`，r002 `SELL WOOL 1` |
| learned_router | 同上 | 0、1 | +1610 | -6 | step 412；同一 WOOL 分歧 |
| v5_topdays | 2026-08-19 / episode 94561433 / seed 126457903 | 0 | +26 | -33 | step 413；V12A `SELL WOOL 2`，r002 `SELL WOOL 1` |

前两个失败源中，V12A 全局 diagnostics 只记录 1 次 WOOL 节流；也就是说它在同一 top day 内部分 WOOL 单跳过、部分 WOOL 单节流，形成不一致的库存/价格反馈路径。关闭 shop-product gate 后，seed 1356333904 对 baseline_v8 和 learned_router 的双席位结果都恢复为 r002 的 +1610。

## 预注册组件消融

所有数字只来自已经暴露的 frozen_v3/v4 screen；未读取 formal/test。

| 方案 | panel | 对 r002 直接得分率 | 7 对手汇总净得分 | 最差单对手净得分 | 对 baseline_v8 净得分 |
|---|---|---:|---:|---:|---:|
| 原 V12A | v3 | 77.78% | +3.97pp | 0pp | 0pp |
| 原 V12A | v4 | 69.44% | +3.97pp | -2.78pp | -2.78pp |
| 删除 shop-product gate | v3 | 77.78% | +3.97pp | 0pp | 0pp |
| 删除 shop-product gate | v4 | 75.00% | +6.35pp | 0pp | +2.78pp |
| 删除 WOOL 节流 | v3 | 80.56% | +7.54pp | 0pp | +11.11pp |
| 删除 WOOL 节流 | v4 | 69.44% | +9.13pp | 0pp | +16.67pp |

- `shed_headroom_guard`：576 局中 skip reason 次数为 0，屏内动作等价于关闭该守卫；无法解释任何回撤。
- `terminal step718 fill`：576 局中 added order/quantity 均为 0，屏内动作等价于关闭 terminal；无法解释任何回撤。
- `shop-product gate`：删除后 v4 的直接亲子、共同对手汇总、最差对手和 baseline_v8 四项同时改善，并精确恢复主要 W→L 来源；这是有因果支持的单组件修复。
- `no-WOOL`：两个 panel 的汇总得分更高，但它是在观察商品级失败后选择，选择偏差更大。已保留为开发 challenger，不取代因果优先 A2。

## 产物

- 首选 A2：`../v12a2_no_shop_gate/submission.tar.gz`，292,554 bytes，SHA256 `53fda5ec6773a339fb181e2102c5e6e266620ecd0616a7034ea117587e20bd0b`。
- 首选 A2 package QA：3 个既有 QA seed × 双席位，全部 720 states / 719 calls / DONE-DONE / 零 stderr / 零 fallback，源码与干净归档逐动作及 reward 完全一致。
- 开发 challenger：`../v12a2_no_wool_throttle/submission.tar.gz`，292,696 bytes，SHA256 `e362f6f077f1a3117edd509e4a63c0f16fdb988f05affef9d5e1466fb9f26680`；同样通过 package QA，但不作为首选。
- 原始消融结果：`mechanism_ablation/no_shop_full/v3/report.json`、`mechanism_ablation/no_shop_full/v4/report.json`、`mechanism_ablation/v3/report.json`、`mechanism_ablation/v4/report.json`。

验收状态：`v12a2_no_shop_gate` 在 v3/v4 均满足“相对 r002 总体正、任一主要对手不低于 -2pp、直接父策略至少 50%”。它只获得进入独立 formal 的资格，不代表已经通过 formal，更不代表可以直接提交。
