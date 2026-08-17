# Kaggriculture 赛题说明

> 最后核对：2026-08-17。比赛方可能更新环境与规则，提交前必须再次核对 Kaggle 官方页面。

## 基本信息

- 比赛名称：Kaggriculture
- 官方链接：https://www.kaggle.com/competitions/kaggriculture
- 主办方：Google LLC
- 承办平台：Kaggle
- 类型：Featured Simulation Competition
- 任务：构建自主农场经营 Agent，在双人仿真对局中管理生产、劳动力、土地与动态市场，以赛季结束时的银行余额击败对手。
- 总奖金：50,000 美元；最终第 1～10 名各 5,000 美元。
- 队伍上限：5 人。

## 当前参赛状态

截至 2026-08-17，Kaggle API 返回 `userHasEntered: true`，比赛规则已由用户接受。官方比赛包已下载到 `data/`，其中保留原始 `kaggriculture.zip`，并解压出 `README.md` 与 `AGENTS.md`。

## 核心赛制

- 每局由两个 Agent 对战，各自经营一座独立农场。
- 一个赛季共 30 个游戏日，每日 24 回合，总计 720 回合。
- 默认初始资金为 3,000 金币；地图为 10×10，开始时只解锁一个 5×5 象限。
- Agent 可以种植小麦、胡萝卜、番茄、草莓和甜瓜，也可饲养鹅、牛和羊，生产鸡蛋、牛奶、羊毛与肥料。
- 可以移动、种植、浇水、施肥、收获、照料动物、雇佣临时工、购买土地以及买卖资源。
- 双方共享动态市场与城镇需求。出售会增加市场库存并可能压低价格；商店消费和购买会减少库存并可能推高价格。
- 赛季结束时，银行余额较高者获胜；未出售的库存不计入最终余额。

更详细的状态、动作与资源机制见 [game_mechanics.md](game_mechanics.md)。

## 评测与排行榜

- 每次提交先与自身副本进行 Validation Episode；运行失败会被标记为 `Error`。
- 通过验证后，Bot 会进入匹配池，与技能评级接近的 Bot 持续对局。
- 评级只取决于胜、负、平以及双方赛前评级；最终金币差额不影响单局评级变化。
- 每天最多提交 5 次；最新两个提交会持续参与评测，排行榜展示其中评级更高者。
- 截止提交后还会继续运行约两周对局，并使用 Bradley–Terry tournament 生成最终排行榜。
- Simulation 比赛没有传统预测赛的 Private Leaderboard。

## 提交形式

- 单文件方案：根目录为 `main.py`，其中定义 `agent(obs)`。
- 多文件方案：打包为 `tar.gz`，并确保 `main.py` 位于压缩包根目录。
- 可使用 `kaggle-environments` 在本地运行，并与内置的 `pass`、`random`、`starter` Agent 对战。
- 正式评测期间禁止网络输入和输出；提交必须自包含，不能在运行时调用外部 API 或云端 LLM。

示例本地运行方式：

```python
from kaggle_environments import make

env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=True)
env.run(["main.py", "starter"])
env.render(mode="ipython", width=1200, height=800)
```

## 时间线

所有官方截止时间均为 UTC；台北时间需加 8 小时。

| 事项 | UTC | 台北时间 |
| --- | --- | --- |
| 报名与组队截止 | 2026-09-23 23:59 | 2026-09-24 07:59 |
| 最终提交截止 | 2026-09-30 23:59 | 2026-10-01 07:59 |
| 截止后继续评测 | 2026-10-01 至约 2026-10-15 | 同期加 8 小时 |

## 规则摘要

- 每人只能使用一个 Kaggle 账号参赛。
- 外部数据、模型和工具须符合公平可得与合理成本要求。
- 获奖者须提供可复现的方法说明与完整代码，并按比赛规则授予相应许可。
- 正式提交前，以官方 [Rules](https://www.kaggle.com/competitions/kaggriculture/rules) 页面为准。

## 官方资料

- 比赛主页：https://www.kaggle.com/competitions/kaggriculture
- 比赛规则：https://www.kaggle.com/competitions/kaggriculture/rules
- Kaggle Environments：https://github.com/Kaggle/kaggle-environments
