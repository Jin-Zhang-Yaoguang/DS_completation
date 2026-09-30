# V62 预注册：MILK/STRAWBERRY 强需求延迟

V61 证明 WOOL 的陡峭平方曲线没有稳定转化为胜局。MILK 与 STRAWBERRY 同时被 Ice Cream、Smoothie 等多家商店持续消费，需求恢复更分散，且价格曲线比 WOOL 平滑，较高延迟比例的仓容风险更低。

V62 只对 MILK/STRAWBERRY 且同回合公开需求强度至少 2 的 SELL 使用 37.5% 延迟，其余商品保持 V54 的 25%。

- 父代：`v54_terminal_water_bypass`。
- 烟测：内部 seeds `62001-62008`，12 个活动金牌门、双座位，共 384 场。
- 烟测硬门：实际奖励变化、PGU 不低于 0、负向翻转为 0、零错误。
- 通过后 Development 3,072 场；Confirmation 12,288 场；正式硬门不变。

证伪：仍出现负向翻转、机制不触发，或正式门控失败。
