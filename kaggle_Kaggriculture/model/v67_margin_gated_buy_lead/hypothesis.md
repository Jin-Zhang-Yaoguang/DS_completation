# V67 假设：固定支出槽位上的 BUY_PRODUCT 抢价

- 父代：V66。
- 机制：clone-like 状态下，若第 1 槽是可精确定价的固定支出、第 2 槽是 WHEAT/FERTILIZER 购买，则把购买提前一槽；候选先买、对手后买，利用共享库存下降造成的买价差。
- 合法信息：公开市场库存、公开农场 money/hires/land、自己的 shed 与已生成动作。
- 安全门：只跨 HIRE、BUY_LAND、BUY_SEED；要求现金足以同时执行两单、shed 容量足够、预测买价优势严格为正。
- 证伪：Smoke 无奖励变化、PGU 为负或出现任何负向翻转即淘汰；通过后 Development 为 64 source × 13 金牌 × 双座位 × 候选/父代 = 3,328 场，Confirmation 为 13,312 场。
