# V14 alternatives：S0 / S1 证伪记录

> 日期：2026-08-24（Asia/Taipei）  
> 范围：只使用已经暴露的 V13 `screen36`；没有读取或运行 confirm/test，没有修改正式协议，没有提交 Kaggle。

## 结论

| 候选 | 继承 | 静态不变量 | 真实 smoke | screen36 双锚 | 决策 |
|---|---|---|---|---|---|
| S0 hour23 fertilizer | A2 | 受控可拾取状态下，EOD 后公开状态完全相同，仅私有 `FERTILIZER +1` | 8 局、实际触发 0 次 | 未运行 | **淘汰**：父路线已在日内收走肥料，screen 轨迹没有剩余覆盖 |
| S1 inventory-neutral WHEAT squeeze | A2 | 价格逐点对齐；31,160 组交易保持净小麦与最终市场库存一致，自成本不升 | 8/8 局触发，8 次执行，0 unwind / 0 fault | 144/144 完成；双锚 `98/12/34` | **保留为有效机制**，但对 A2 纯胜率 62.5%，尚未达到 65% 目标，不能直接提交 |

## S0：为什么淘汰

S0 只在 `hour=23` 时，把会被 EOD 重置的位置动作 `PASS/NORTH/SOUTH/EAST/WEST` 替换成 `COLLECT_FERTILIZER`。仓容门使用：

```text
当前 shed + 全部携带
+ 父动作 HARVEST / 既有 COLLECT 的最坏新增
+ 父市场 BUY_PRODUCT / BUY_ANIMAL 的最坏新增
+ 新拾取数量
<= 90
```

官方引擎单步检查通过：在真实 screen seed 的日末状态上，将动物的 `fertilizer_available` 控制为 `True` 后，父动作与 S0 动作的下一日 `farms/market/town/day/hour` 完全一致，唯一私有差异是肥料 `+1`。

但覆盖率检查更重要。screen36 前 2 个 source、候选双席位、对 A2/r002 共 8 局中：

- `s0_eligible_actors = 0`
- `s0_collected_units = 0`
- `s0_residual_fallbacks = 0`
- 日末检查 232 次，全部为 `no_resettable_animal_actor`

父策略已在当天更早时点收走可用肥料，或日末脚下没有仍可收肥料的动物。机制正确但没有真实覆盖，因此按预先约定停止，不跑完整 screen36。

## S1：最小实现

触发决策树：

```text
step 72..699，且当前/下一时点都不靠近日界？
  否 -> A2 原动作
  是
  └─ 自己与对手 Router 均预测 baseline_v8？
       否 -> A2 原动作
       是
       └─ 双方公开生产状态完全镜像？
            否 -> A2 原动作
            是
            └─ 当前父 market 与两侧 V8 原路线 market 均为空？
                 否 -> A2 原动作
                 是
                 └─ 下一回合两侧都是同槽、同量 BUY WHEAT(q)，且无 PICKUP？
                      否 -> A2 原动作
                      是
                      └─ 枚举 r∈{1,2,4,8,min(12,q),q}
                           ├─ 精确整数价格下自成本不升、对手成本不降、现金差至少 +1
                           ├─ shed + q+r <= 90
                           └─ cash >= prep_cost + 1500
                                否 -> A2 原动作
                                是 -> 本回合 BUY(q+r)，下一回合 BUY(q) 原槽改 SELL(r)
```

下一回合任何分支、路线、数量、公开镜像或可售库存不一致，原型就尝试卖回完整 `q+r`；无法无损 unwind 时永久禁用本局残差。完整 screen36 中没有发生一次 mismatch、unwind 或 fault。

## S1：验证结果

### 静态与真实交易闭环

- 自写 WHEAT 价格函数与官方引擎在库存 `8000..12000` 的 4,001 个整数点逐点一致。
- 31,160 组 `(inventory,q,r,drain)` 组合全部满足：
  - 我方两回合净小麦仍为 `q`；
  - 目标回合后市场库存与父策略一致；
  - 局部我方成本不高于父策略；
  - 局部对手成本不低于父策略。
- screen36 首个 source 的双锚、双席位共 4 局真实闭环审计：4 个触发事件中，对手实际动作全部是预测的 singleton `BUY_PRODUCT WHEAT(q)`，下一状态 WHEAT 市场库存全部精确回到推导值。

### 完整已暴露 screen36

| 对手 | 局数 | 胜/平/负 | 纯胜率 | 得分率 | 平均金币差 | 配对得分率 95% CI |
|---|---:|---:|---:|---:|---:|---:|
| A2 | 72 | 45/12/15 | **62.50%** | 70.83% | +5.11 | [62.50%, 79.17%] |
| r002 | 72 | 53/0/19 | **73.61%** | 73.61% | +70.88 | [63.89%, 83.33%] |
| 合计 | 144 | 98/12/34 | **68.06%** | 72.22% | — | — |

机制诊断：

- 触发局：`78/144 = 54.17%`
- `prepared = 198`
- `executed = 198`
- `unwinds = 0`
- `pending_faults = 0`
- 局部预测自成本改善合计：`258`
- 局部预测对手成本增加合计：`478`
- 局部预测现金差改善合计：`736`

触发分层仅作诊断，不能当因果估计，因为触发本身选择了 V8 镜像上下文：

| 对手 | 触发局胜/平/负 | 未触发局胜/平/负 |
|---|---:|---:|
| A2 | 35/0/4 | 10/12/11 |
| r002 | 35/0/4 | 18/0/15 |

## 风险与下一步边界

1. 这是已经暴露的开发 screen，不是独立 holdout；62.5%/73.61% 不能外推成线上胜率。
2. S1 对 A2 的纯胜率为 62.5%，低于当前要求的 65%；双锚合计超过 65% 不能替代对 A2 单独门槛。
3. 局部现金不等式成立，不代表整季严格支配。对手少付/多付几元可能改变后续 affordability；本次结果支持机制，但仍需未见数据验证。
4. 不应继续用同一 screen 调 `cash_reserve/max_r`，否则会把已暴露 panel 直接过拟合。下一合理动作是把 S1 作为冻结组件交给更高层候选组合，并在新的、预先冻结且经授权的数据门上一次性验收。

## 产物与哈希

- `s0_eod_fertilizer/main.py`：`2a0b4351e1ca98e8bac7986c29956e82fdbb7739a90b1392eb882c954ea3f2ec`
- `s1_wheat_squeeze/main.py`：`48f71c63d9b5b4574e93467413f8a70b488d1ea045cf3d5fab15efbc80b33291`
- `static_invariants.json`：`863e83b2efbbcd83936d9cc2869635686d1cd61a194e20cfaa5fd45590b25a74`
- `s1_transaction_audit.json`：`0be36ce4b7e47c991ecfa47f70f7f23c74a3166fd90555fb5205a12323c17595`
- `runs/smoke_s0_2/summary.json`：`91774ff91aa281b1422c0553f61135bc729893ea13eaf3fe0a8f61a327b09213`
- `runs/smoke_s1_2/summary.json`：`18a1533ccd3b42ecf36af8f24c05e52311e02a382d59a0c165f8d69a14ec39c7`
- `runs/screen36_s1/summary.json`：`bf019dfcd7e69d2ae712a2c6b50b80204072f58f022758cd77df80a00ae52e62`

