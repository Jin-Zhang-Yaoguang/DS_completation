# v1_adaptive_market

首个以公开强基线为起点的 Kaggriculture 竞争版本。策略主体来自 Tetsutani 的公开
`Adaptive Farming Strategy for Kaggriculture`，本目录保留单文件提交形式，并针对
`kaggle-environments==1.32.7` 修正了市场价格模型。

## 策略结构

- 两条完整的 720 回合生产路线共享开局。
- 观察前 168 回合的城镇商店；适合羊毛的需求组合选择高价值畜牧路线，否则使用平衡路线。
- 路线之外只做局部执行修复：杂草、喂养、仓库容量、出售排序、终局清仓和种子冗余控制。
- 最终入口是文件中最后一个可调用对象 `agent`，提交包根目录仅含 `main.py`。

## 本地改动

- 将 CARROT、TOMATO、EGG 的稀缺侧价格曲线更新为 1.32.7 的 `hinge` 模型。
- 使用与官方环境相同的 `HINGE_GAIN=8.0` 和按资源 `T` 归一化公式。
- 将版本标记更新为 `market-route-moe-v3-hinge`。

这次改动主要修复市场订单延迟损失的估价。它不会凭空增加番茄或鸡蛋产能；针对新
稀缺机制增加生产路线属于下一轮实验，必须通过双席位 holdout 后再纳入。

## 来源与验证边界

- 公开来源：<https://www.kaggle.com/code/tetsutani/adaptive-farming-strategy-for-kaggriculture>
- 官方平衡说明：<https://www.kaggle.com/competitions/kaggriculture/discussion/735311>
- 本地金币和胜率不是 Kaggle 排行榜评级；只用于版本间相对筛选。

## 本地运行

从仓库根目录执行：

```bash
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v1_adaptive_market/smoke_test.py

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v1_adaptive_market/build_submission.py
```
