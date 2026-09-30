# V76 假设：动态买单跨一个安全固定支出槽

- 父代：V73。
- 唯一改动：clone-like 局面中，保留重复 WHEAT 完全合并，并将一笔 WHEAT/FERTILIZER 买单向左跨过一个相邻 HIRE、BUY_LAND 或 BUY_SEED。
- 规则依据：固定支出不改变公开市场库存；候选先独占买入会降低库存，使同构对手在后续槽位承担更高动态买价。只跨一个相邻槽，且不跨 BUY_ANIMAL，控制现金与棚容量风险。
- 证伪：544 场 Smoke 若无奖励变化、PGU 为负或出现负翻转即淘汰；通过后进入 4,352 场 Development 和 17,408 场 Confirmation。
