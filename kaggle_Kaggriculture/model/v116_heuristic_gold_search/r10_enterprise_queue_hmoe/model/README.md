# R10 Enterprise Queue HMoE（P0 通过 / P1 部分）

状态：`REJECT_P2_ECONOMIC_HEALTH / NOT_GOLD`。这是从零实现的可执行候选与机制原型；已完成 48 局 719-step 双座位 idle 经济健康面板，但数量级失败，未进入金牌池。

## 冻结接口

```python
executor = build_executor(params=None, mode="router")
action = executor.act(obs)
diagnostic = executor.diagnostics()
```

支持四个 mode：

- `router`
- `fixed_root_exchange`
- `fixed_dairy_berry`
- `fixed_fiber_grain`

三个固定专家都从 step 0 独立编译生产目标并经营，不包装其他 agent。`main.py` 只依赖 Python 标准库，可直接作为候选入口。

## 设计

- **程序化布局 lease**：专家只给日级聚合作物/动物目标；执行器依据当前已解锁空地、现有资产、仓库入口距离与生产频率生成/保留 lease，不保存历史逐步坐标。
- **持久工作队列**：`TaskTicket` 跨 step 保存 owner、deadline、resource、retry 与状态；`ActorState` 保留角色、分区和活动任务。每天只解除 owner 并重绑，不每步全量重拍任务。
- **资源闭环**：当前 shed、seed、随身库存和 pending market receipt 分账；PLANT 在本轮对实际种子做原子预留，避免多个 actor 同时超卖同一种子。
- **执行状态**：任务按需要经过 `WAIT_RESOURCE → ACQUIRE → TRAVEL → EXECUTE → DELIVER` 的适用子链。FEED/PLACE 从仓库取资源后执行；HARVEST 在执行后进入 DELIVER，只有观测到 shed DROP 才完成。
- **资本采购**：按当前任务缺口购买饲料、种子、动物、土地和劳工；现金 reserve、剩余生产日、当日剩余工时与土地 day cutoff 形成 payback guard；订单写入 pending receipt，下一 step 对账。
- **商品出售控制器**：逐商品状态为 terminal liquidation、capex finance、capacity relief、known-demand hold、scarcity release 或 operating reserve；先估计同轮 DROP/PICKUP 后的 shed 再决定市场订单。
- **Router**：开局使用当前价格做低承诺 optionality 组合；首个实时可见 shop 出现后，只使用公开需求、价格、自身资产和对手公开产能评分，一次性提交到完整专家，之后不改路。

`SHED_GATES` 是 10×10 规则中的四个固定仓库入口，不是历史路线坐标。专家表只含三个日级聚合阶段，不含逐步动作表、Replay、父 agent 或玩家数据。

## 已完成验证

在本地 bit-exact `kagsim 1.32.7` 上完成：

- `py_compile`；
- 静态原创性预检：`strategy_parent=null`、标准库导入、无 Replay/父 agent/历史动作表引用；
- 合成机制：四 mode 接口、三固定专家、Router 单次提交、成熟作物 HARVEST 路径、种子原子预留、HARVEST→DELIVER→DROP、diagnostics JSON；
- 真实引擎：四 mode one-step；四 mode × seed 7100 × idle × 96-step 短程，各 95 次 agent call，动作 schema 与运行错误均为 0。

短程终值（仅 smoke）：router `263`、root `560`、dairy `577`、fiber `353`。这些局在第 96 step 截断，大量资本尚未回收，既不是 30 日 bank，也不是强度指标。

复现：

```bash
PYTHONPATH=kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/build/lib.macosx-12.1-arm64-cpython-312 \
/opt/anaconda3/envs/quant_d1_2026/bin/python3.12 -B \
kaggle_Kaggriculture/model/v116_heuristic_gold_search/r10_enterprise_queue_hmoe/model/test_r10.py
```

## 判定

`REJECT_P2_ECONOMIC_HEALTH`。48/48 局完成、全部 719 calls、候选 schema/ERROR 为 0，但 Router 平均 bank 仅 `682.67`、CVaR25 `237.67`；三个 fixed expert 平均 bank 仅 `201.17/1958.58/469.42`，最低末局生产资产为 `0`。完整证据在 `../evaluation/runs/r10_p2_exposed_001/`。本版本已淘汰，不进入 P3/Replay，不登记 `golden_model.md`。
