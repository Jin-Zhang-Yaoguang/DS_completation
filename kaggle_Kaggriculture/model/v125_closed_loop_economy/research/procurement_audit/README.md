# 实验 A：V22 土地采购的发单即销账反例

结论：**已在官方 1.32.7 完整解释器中证实。** V22 在土地订单发出时减少 `pending`，但实际现金不足时引擎会拒绝买地；后来现金恢复，原策略也不会重试。只在下一帧按土地数量确认成交、恢复未成交待办，就能让既定购买计划完成。本实验不说明这次买地提高终局金币或胜率。

本目录是 V125 的机制研究附件。诊断补丁以 V22 为父策略，**不是独立原创 HMoE，不是金牌候选**。本轮只改变土地采购确认；种子和动物的确认、估价预算、任务调度都未修改。

## 冻结与执行

- 冻结时间：2026-09-05 09:47:06 UTC。
- 原 V22 快照：`baseline.py`、`snapshot/v22_main.py`，SHA256 `0ad487e7244d24fbdf24fb20e6eb1994f8bea0a7fff41926733fac7be4cc9f43`。
- 确认补丁：`confirmation_agent.py`，SHA256 `6d607f739a61f391dd978e84d33d87c25a021f81c46cfb4525bace8694867e35`。
- 官方解释器 SHA256：`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`，源码与配置文件均在 `rules_snapshot/`。
- 只用 1 个进程，2 类人工场景 × 2 席位 × 2 版本 × 3 次解释器调用，共 24 次状态转换；15 个检查全部通过。
- 没有读取任何 Replay、训练集新内容或 Blind，没有新训练、大规模评测与线上提交。

复现命令（从仓库根目录运行）：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/run_microcases.py
```

脚本清空本进程的 `V15_PARAMS`，V22 默认 `tape_until_day` 未设置，因此不会加载 V10。策略快照与补丁只依赖标准库；微场景使用已安装并核对 SHA 的 `kaggle-environments==1.32.7`。

## 可复核的反例

人工设置第 18 天 3 点（step 435），双方各持有 80 单位仓内草莓；己方现金 100，已解锁 3 个区域，仍有 1 次土地采购待办。己方农场主带 20 单位甜瓜停在仓库入口，当步正常入仓，原市场层要到下一步才会看到这批甜瓜。商店字段设为 6 家可重复的 YARN_STORE，不依赖未来信息。

1. V22 根据草莓现价 120，把 `80 × 120 × 70%` 计入预算，预估可用现金 6820；因此发出 `SELL STRAWBERRY 80 → BUY_LAND → BUY_SEED WHEAT 36`，并立即把土地待办减为 0。
2. 对手同槽出售 80 草莓。官方按单位同步定价后，己方草莓实际销售额只有 1983；买地时现金 2083，4000 的土地订单被拒；后续 360 的小麦种子照常成交，期末现金 1723，区域数仍为 3。
3. 下一步仓内 20 甜瓜实际卖出 4976，现金已经足够买地。基线却没有待办，最终现金 6699、区域数仍为 3。
4. 确认补丁先看到区域数未增加，将 1 次土地待办恢复。该步仍执行相同甜瓜出售，然后重试买地，实际成交；再下一帧确认区域数增加，未重复恢复。最终现金 2699、区域数 4。

| 指标 | 原 V22 | 仅土地确认补丁 |
|---|---:|---:|
| 首步动作 | 与补丁完全相同 | 与基线完全相同 |
| 首步买地实际成交 | 0 | 0 |
| 未成交后恢复待办 | 0 | 1 |
| 现金恢复后区域数 | 3 | 4 |
| 3 步后现金 | 6699 | 2699 |

两个席位结果完全一致。补丁现金少 4000 正是成功购买土地的成本，不能写成收益增加。本实验只证明“既定投资承诺有机会因为记账时点错误永久丢失”。该人工状态在自然对局中的发生频率尚未测量。

## 正常成交控制

同日同小时、同样有土地待办，起始现金改为 6000，不设置价格冲击。基线和补丁均只买一次地，3 步全部动作精确一致，最终现金 1640、区域数 4。补丁没有在成功成交后重复买地。

## 代码证据

- 冻结 V22 将未成交销售额的 70% 纳入可支配现金。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/baseline.py:598]
- 同一分支把土地订单加入清单后立刻 `pend["land"] -= 1`。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/baseline.py:629]
- 官方 `_do_buy_land` 在现金不足时直接返回，不产生资产增量。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/rules_snapshot/kaggriculture.py:712]
- 补丁仅在连续下一帧用解锁区域增量确认发单；未确认数量恢复到原待办，再调用相同的冻结 `_agent`。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/confirmation_agent.py:14]

## 失败证据保留

初版微场景脚手架混用了 `Struct` 的字典字段赋值和属性赋值，导致第二、第三帧的 step 字段重复。发现后将那次输出保留为 `results_invalidated_clock_scaffold.json`，明确标记无效；修正后新增 `all_clock_transitions_exact`，重新执行全部场景。最终有效输出是 `results.json`，24 次 step / day / hour 转换一致。

## 对 V125 的直接用途

新策略可把“预留 → 发出 → 下一帧观测确认 → 完成/重试/过期”作为交易状态机。土地是单调增量，最容易严格确认；种子要同时扣除本步实际播种，动物要处理放置、搬运、夜间逃逸和仓溢，不能简单复制土地的计数差。确认成交解决执行账本，是否还值得继续这项投资应由剩余时间与产能回收判断，属于另一个需要单独验证的机制。
