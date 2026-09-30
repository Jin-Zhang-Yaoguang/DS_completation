# V60 预注册：premium 强需求自适应延迟

V59 表明需求强度不足以对所有商品统一提高延迟。premium 商品具有更陡的市场价格曲线，强需求后的库存回落更可能补偿等待；WHEAT、CARROT、TOMATO、EGG、FERTILIZER 则保留 V54 的 25%。

V60 仅对 `_PREMIUM` 中且同回合公开需求强度至少 2 的 SELL 使用 37.5% 延迟，其余动作与 V54 完全一致。

- 父代：`v54_terminal_water_bypass`。
- 烟测：内部 seeds `60001-60008`，12 个活动金牌门、双座位，共 384 场。
- 烟测硬门：实际奖励变化、PGU 不低于 0、负向翻转为 0、零错误。
- 通过后 Development 3,072 场；Confirmation 12,288 场；正式门槛不变。

证伪：premium 限定后仍出现负向翻转，或任一正式门控失败。
