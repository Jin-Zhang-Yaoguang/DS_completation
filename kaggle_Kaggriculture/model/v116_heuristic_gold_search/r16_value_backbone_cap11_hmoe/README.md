# R16 Value-backbone Cap-11 HMoE

状态：`NOT_GOLD_KILLFAST_REJECT`。

R16 基于 R15 的自包含源码，`strategy_parent=null`，保留五个完整生产专家及 R15 的三项结算修复：step≥696 禁购、WHEAT 逐单位递减 inventory 报价、真实 harvest 链接入市场。运行时不导入或包装历史模型。

## 限定增量

- hands 固定硬上限 11，不使用复杂自适应劳工公式。
- 按 R13 P2 暴露开发证据修改浅树：`PET_CAFE -> dairy_berry`、`PIZZA_SHOP -> wool`，其他路由保持原逻辑。
- 仅调整离散 genome 参数：五专家都以至少 18 MELON、至少 6 SHEEP/COW 为价值骨架。
- 专家未坍缩：root 保留 CARROT≥8，tomato_market 保留 TOMATO≥6，grain_egg 保留 WHEAT≥24 与 GOOSE≥2；五个终局聚合目标和机制市场动作均不同。

## 门控证据

机制检查 27/27 通过。唯一一次 seed7100/router/seat0/idle killfast：

- bank：97,030，低于 105,000 门槛；
- step144 assets：22，通过 12 门槛；
- terminal assets：63，通过 58 门槛；
- calls：719；runtime/schema/invalid/missed-water 均为 0；
- 仅 bank 门失败，最终判定淘汰。

未运行 P2、P3 或 Replay。该版本不得注册 golden_model，不得提交 Kaggle。
