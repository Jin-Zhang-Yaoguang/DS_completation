# V66 Margin-Gated Sell Bubble

父代 V54。候选只在 clone-like 队列中的异商品 `BUY_PRODUCT → SELL` 交换被官方逐单位价格曲线预测为严格正净 margin 时，才把 SELL 前移；其他生产、Router、终局和安全执行逻辑保持不变。

- Smoke：384 场，PGU `+3.646pp`，`14/178/0`。
- Development：3,072 场，PGU `+2.279pp`，95% CI `[+1.823,+2.734]pp`，零错误。
- Confirmation：12,288 场，PGU `+2.759pp`，95% CI `[+2.523,+2.987]pp`，PoolScore `90.60%`，`332/5812/0`。
- 工程 QA：提交包 16/16 逐动作等价；官方 Python 1.32.7 为 768/768 奖励精确一致。
- 决策：`PROMOTE_LOCAL_GOLD`，当前 Goal 第 10/15 个新金牌；未自动提交 Kaggle。
