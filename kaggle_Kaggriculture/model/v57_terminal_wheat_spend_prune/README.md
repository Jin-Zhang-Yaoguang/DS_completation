# V57 Terminal Wheat Spend Prune

V57 将 V54 在 step 712 的固定 38 单位 WHEAT 购买置零，并保留原 market slot。

- 烟测：384 场；触发 192 次、清零 7,296 单位。
- PGU `+1.04pp`，`8/180/4`，平均 margin `+4.46`。
- 负向翻转说明该购买仍有末段小麦价格支撑价值，违反烟测“零负向翻转”硬门。

决策：`REJECT_MECHANISM_SMOKE`。未消费官方 Replay。
