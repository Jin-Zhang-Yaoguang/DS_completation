# V120 Top5 Episode Distilled Gold Candidate

状态：`GOLD_GATE_PASS / SUBMIT_READY / NOT_UPLOADED`。

最终冻结候选从当前 Top5 的 13 个唯一 Public Replay、19 条 teacher-seat 轨迹中进行完整路线
专家筛选；development 后冻结 OceanMix Episode `104547425` 的 route expert，随后在未参与选模
的 64 fresh seed × 双座位 blind 上验收：对 V76 `114/0/14`，对 V20 `114/0/14`，两者胜率
均为 `89.0625%`，通过用户定义的各自 `>=65%` 金牌门槛。

V120 用公开 Replay 学习可泛化的状态到 option 映射，禁止复用 V119 的单局
`_ACTIONS[step]` 动作带。首轮目标是验证三种时间尺度的数据契约和可学习性，不生成 Kaggle
提交包。

## 三层定义

1. **商店刷新层（72 turn / 3 天）**：输入当前商店多重集、新刷新商店、资产、市场和双方生产
   结构；输出未来三天的生产、雇佣、扩地、购买与销售组合，以及相对上一周期的策略变化。
2. **日级移动层（24 turn / 1 天）**：输入日初状态与商店层 option；输出一天内的任务组合、
   中心往返距离、有效动作/移动比和日级 route option。
3. **全局层（全赛季视角，日级更新）**：输入赛季进度、金币差、双方公开资产和最近一天市场变化；
   输出己方提前卖出向量及对手下一日销售向量，用于后续全局风险/市场 Router。

推理时的依赖方向是 `全局风险 -> 商店周期 -> 日级移动 -> 独立低层执行器`。编号表示用户指定的
研究层次，不表示控制调用顺序。

## 数据边界

- 只读取官方 Public Replay，实际日期必须不早于 2026-08-20。
- 动作标签严格按 `steps[t].observation -> steps[t+1].action` 对齐。
- 全局去重键为 `episode_id + replay_sha256`。
- 训练/验证按 episode 分组，禁止把同一局的 turn 随机拆到两侧。
- Top5 Public Replay 是本次用户明确指定的 teacher-only 训练面板；它不替代本账号 own-online
  主评测面板，也不替代官方 daily confirmation 面板。
- 模型必须拥有自己的 Router、专家、状态契约和主动作生成；V17/V76/V119 完整 agent 不得作为
  serving wrapper。

## 运行

```bash
.venv/bin/python kaggle_Kaggriculture/model/v120_hierarchical_top5_distillation/download_pilot_replays.py
.venv/bin/python kaggle_Kaggriculture/model/v120_hierarchical_top5_distillation/build_hierarchical_dataset.py
.venv/bin/python kaggle_Kaggriculture/model/v120_hierarchical_top5_distillation/train_pilot.py
```

`pilot_sources.json` 固定首轮数据身份；`dataset_manifest.json`、`pilot_training_report.json` 和
`pilot_model.json` 分别记录数据、分组验证和模型参数。

## 首轮结果

- 13 个唯一 Public Replay、19 条 Top5 teacher-seat 轨迹。
- 商店层 190 行、日级层 570 行、全局层 570 行。
- Dev 固定为 3 个完整 episode，覆盖五位 teacher；没有 turn 级交叉泄漏。
- 商店层宏平均召回 `0.6752`，多数类宏基线 `0.3333`；日级层为 `0.5698` 对 `0.25`。
- 全局层 RMSE `29.5202`，优于训练集均值基线 `31.7166`。

早期三层 pilot 指标只保留为研究记录，不参与最终金牌判定。正式判定只使用冻结 `main.py` 的
fresh-seed 双座位闭环 `gold_gate_results.json`。`submission.tar.gz` 已完成源码/归档逐字节一致
封装，但未获得本轮上传授权，因此没有提交 Kaggle。
