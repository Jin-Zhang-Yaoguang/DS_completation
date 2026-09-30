# V36 Price-Floor Cap

V36 尝试把 V34 的前置数量限制在价格仍高于 1 的单位。内部烟测 192 场实际触发 911 次上限，但相对父代为 `0pp`，翻转 `4/90/2`，违反零负翻转门。

决策：`REJECT_MECHANISM_SMOKE`。未消费官方 Replay，保留可提交失败包，未提交 Kaggle。
