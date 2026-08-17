# Kaggriculture 人机训练场

本地网页使用官方 `kaggle-environments==1.32.7` 作为游戏引擎。人类玩家通过网页逐回合提交动作，对手直接加载当前比赛版本：

`../model/v1_adaptive_market/main.py`

## 启动

从仓库根目录运行：

```bash
.venv/bin/python kaggle_Kaggriculture/playground/app.py
```

浏览器打开：<http://127.0.0.1:8765>

如果需要其他端口：

```bash
KAGGRICULTURE_PLAY_PORT=9000 .venv/bin/python kaggle_Kaggriculture/playground/app.py
```

## 界面能力

- 选择 1、3、5、10 或 30 天赛季，以及随机种子和玩家席位。
- 同时查看双方公开农场、金币、市场价格与城镇商店。
- 为主农民和每位临时工分别编排动作。
- 添加、排序和删除每回合最多 10 笔市场订单。
- 查看自己的仓库、种子与各单位随身库存。
- 训练模式显示双方上一回合动作和金币变化。
- 可让人类一方连续 `PASS` 1、6 或 24 回合进行快速观察。

对手私有仓库、种子和随身库存不会暴露，保持与正式环境相同的信息边界。

## 测试

```bash
cd kaggle_Kaggriculture/playground
../../.venv/bin/python -m unittest -v test_app.py
```
