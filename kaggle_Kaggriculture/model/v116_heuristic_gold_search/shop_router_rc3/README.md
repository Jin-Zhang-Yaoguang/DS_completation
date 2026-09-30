# V116 RC3：首店需求 Router + 四生产专家

## 决策

RC3 没有同时通过两项冻结健康门，停止研究，不进入金牌池：

- 平均 bank：`69,882.125 < 70,000`；
- 平均日级目标兑现率：`89.9222% < 90%`；
- 结论：`FAILED_RC3_HEALTH_GATE_DO_NOT_RUN_GOLD_ARENA`。

两项都非常接近门槛，但预先冻结的口径不能事后取整或放宽。

## 冻结证据

seed 7100–7103、双座位、idle 对手，共 8 局：

- 中位 bank `71,443.5`，区间 `[49,659, 82,001]`；
- 8/8 胜 idle；
- 末个可观测日最低兑现率 `90.28%`；
- 全季平均绝对生产资产 `51.16`；
- 末局绝对生产资产最低 `63`，逐局最大值最高 `68`；
- 每局 719 次调用，零 schema 错误；
- 完整逐局数据见 `smoke_results.json`。

四个专家的最终作物目标都固定为 59，没有通过缩小目标抬高兑现率。

## 实现边界

候选包自包含，不依赖 RC2、父 agent 或外部策略模块。只保存四个紧凑
genome，每个 genome 编译成 30 条日级聚合目标，不保存逐步动作或坐标。

首次 shop 在 step 72 可见后，Router 整局冻结：

- `YARN_STORE → wool`
- `SMOOTHIE_SHOP / ICE_CREAM_SHOP → dairy_berry`
- `PIZZA_SHOP / FARMERS_MARKET → tomato_crop`
- 其他或未出现 shop → `balanced_root`

执行链为：当前状态缺口 → 公平补种 → 任务图 → 持久 role 与全局 auction
→ unit 后 projected shed → 商品级市场控制器。市场控制器使用 32 单融资压力、
12 单普通估值压力、55% 普通出售地板、88 容量压力阈值、动态现金储备和
step 712 终局清算。

公平补种约束：每批买种最多 12；每个正缺口先获 1；单品最多占一批 40%；
每次 PLANT 分配都会更新 virtual-have，避免 WHEAT/MELON 长期饿死其他作物。

## 失败诊断

- 绝对资产和末期兑现率已明显健康，失败主要来自前中期阶段目标切换的建设
  延迟，以及 seed 7101 的 `PET_CAFE → balanced_root` 市场尾部。
- seed 7101 双座位只有 `49,659 / 63,621`，拉低了 bank 均值；不能用删除
  坏 seed 或改 Router 映射来通过本轮冻结门。
- 下一轮若继续，应单独验证阶段目标的渐进 ramp 和 balanced_root 的价格
  尾部控制；本轮不追加参数搜索。

## 复现

```bash
.venv/bin/python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/shop_router_rc3/smoke.py \
  --seed-start 7100 --seeds 4 --workers 4
```

未运行金牌池、未注册 experiments/golden_model、未提交 Kaggle。

