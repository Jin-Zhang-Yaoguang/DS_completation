# V65 预注册：异商品 SELL 跨 BUY_PRODUCT 前移

市场按 slot 交替处理双方订单。V54 允许 SELL 跨越 HIRE、BUY_LAND、BUY_SEED、BUY_ANIMAL，却禁止跨越任何 BUY_PRODUCT。若前序是购买 WHEAT、后序是出售另一个商品，两者的市场库存彼此独立；SELL 前移还能先获得现金、先释放 shed 容量，并在同质竞争中抢占更早 slot。

V65 只在 clone distance 不超过 6、且 BUY_PRODUCT 商品与 SELL 商品不同时允许稳定交换。同商品买卖、SELL 相对顺序、非 clone 局面及其余策略全部保持 V54。

- 父代：`v54_terminal_water_bypass`。
- 烟测：内部 seeds `65001-65008`，12 个活动金牌门、双座位，共 384 场。
- 烟测硬门：实际奖励变化、PGU 不低于 0、负向翻转为 0、零错误。
- 通过后 Development 3,072 场；Confirmation 12,288 场；正式门槛不变。

证伪：跨 slot 后出现任何负向翻转、机制不改变奖励，或正式门控失败。
