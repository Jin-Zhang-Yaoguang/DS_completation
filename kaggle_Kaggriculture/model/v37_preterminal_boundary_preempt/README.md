# V37 Preterminal Boundary Preempt

V37 继承 V34，只把固定 stop=680 延伸到终局清仓 step=716 前，并要求原出售与偿还都发生在 716 之前。[VERIFY: main.py:49] [VERIFY: main.py:278]

- Development：64 source、6 个金牌门、1,536 场；PGU `+10.03pp`，95% CI `[+8.72,+11.20]pp`。
- Confirmation：另 256 source、6,144 场；PoolScore 92.61%，PGU `+10.87pp`，95% CI `[+9.77,+11.98]pp`，`617/2435/20`。
- 直接父代 V34 得分率 83.79%，95% CI `[80.86%,86.72%]`；灾难率不变，CVaR10 改善。
- package parity 16/16；官方 Python 1.32.7 parity 384/384，零错误。

决策：`PROMOTE_LOCAL_GOLD`，本轮第 4/8 个新本地金牌，未提交 Kaggle。
