# V116 RC2：日级聚合目标 + 在线劳工执行器

## 结论

本轮原型是原创闭环策略，但**没有通过强度门槛**，不得注册
`golden_model`。

冻结 smoke（seed 7100–7103、双座位、8 局、idle 对手）：

- 平均 bank：`67,603`，低于预设的 `70,000` 继续门；
- 中位 bank：`70,423.5`；区间：`[56,308, 72,155]`；
- 日级聚合目标平均兑现率：`80.62%`；
- 8/8 胜 idle，但这不等价于战胜金牌模型；
- 每局 719 次调用，零 schema 错误；
- 8 局完整逐局数据见 `smoke_results.json`。

因此本轮停止进入金牌 arena。当前证据只能说明执行器比旧版约 60% 的
目标兑现率更高，不能说明是金牌模型。

## 原创性边界

`main.py` 只保存一个紧凑 genome：土地启用日、每块土地的作物数量、
动物购买波次、劳工和现金参数。`compile_daily_goals()` 只生成 30 条日级
聚合记录，不生成坐标或动作。

每次 `act(obs)` 都重新执行：

1. 从当前农场计算资产缺口；
2. 从当前空地动态选择可建/可种位置；
3. 生成浇水、收获、喂食、建造、放置、补种任务图；
4. 用全局 unit-job auction 分配任务；
5. 按当前现金、仓库、种子、动物和价格生成购销动作。

代码不导入 Island-GA 的 compiler/executor，不含 `_ACTIONS`、Replay、父
agent、逐步坐标或 719 长度 payload。静态检查和资金扰动检查均通过。

## 失败诊断

- 劳工层已不是唯一瓶颈：平均目标兑现率从旧实验约 `70.0%`
  （joint-MPC）提高到 `80.62%`，但 bank 仍只有 `67,603`。
- 尾部不稳：seed 7103 的两座位只有 `60,585 / 56,308`，说明当前固定
  crop mix 对市场路径敏感。
- 末期作物结构偏科：动态补种总是优先 WHEAT/MELON，STRAWBERRY 和
  CARROT 容易被持续轮作缺口挤出。
- 动物基本能兑现（大多数局 `6 SHEEP + 4 COW`），下一轮继续堆劳工或
  动物的边际价值有限。

下一轮研究应把重点转向“商店需求 Router + 价格阈值出售专家 + 公平补种
队列”，先在 idle/fresh-source 同时把尾部 bank 拉过 70k，再进入金牌池。
不能通过修改目标口径来抬高兑现率。

## 复现

```bash
.venv/bin/python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/labor_planner_rc2/smoke.py \
  --seed-start 7100 --seeds 4 --workers 4
```

最多使用 4 个 worker。

