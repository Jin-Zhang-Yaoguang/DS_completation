# V125 G1 机制审计

分析器冻结 SHA：`cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963`。

`analyze_trace.py` 只读取已有完整比赛产出的动作带，用同一版本完整官方解释器重放。它不导入或调用候选，不改变原候选、runner、数据、种子、商店序列或门控协议。重放仍属于来源那一局的机制诊断，不增加评测场次，不增加独立样本数。

来源运行必须已 `DONE`、719 个动作，并含 `--trace --audit-actions` 输出。输入的候选及引擎文件、冻结 runner、动作带 SHA 均验证；逐步应用同一动作后，来源已保存的终局 snapshot 全部字段、奖励、各商品实际采购/销售/采收总量必须一致。该来源 snapshot 是 runner 的终局摘要，并未保存全部田块内部标记或每步原始状态，因此这项校验不是逐帧源状态比对。物料守恒逐商品差额必须为 0。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/mechanism_analysis/analyze_trace.py \
  --run-dir kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/r0_pass_s0 \
  --game-index 0 \
  --output kaggle_Kaggriculture/model/v125_closed_loop_economy/research/mechanism_analysis/新的独立输出目录

.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/mechanism_analysis/derive_findings.py \
  kaggle_Kaggriculture/model/v125_closed_loop_economy/research/mechanism_analysis/新的独立输出目录
```

批量使用须在来源文件写入完成后串行运行，每个 `game-index` 使用不同输出目录，最多一个进程。已有 `analysis.json` 时拒绝覆盖。冻结分析器后不再覆盖源码；若要改口径，新增版本文件并保留旧版。`derive_findings.py` 是只读账本的派生统计，不运行引擎或候选。

产物：

- `audit_manifest.json`：运行前锁定原游戏、动作带、候选/引擎 SHA 和零候选调用边界。
- `analysis.json`：双席位分母、逐商品库存守恒、EOD 丢弃、动物放置、仓库买卖和终局资源。
- `events.jsonl.gz`：真实交易逐单位成交、采收、播种/水/肥/喂养、EOD 死亡与丢弃事件。
- `plant_lifetimes.json`：播种事件及首次水与播种当日 EOD 的可见结果，不包含策略未执行的任务承诺。
- `daily_states.json.gz`、`terminal_states.json`：官方引擎重放的完整状态，用于独立复查。
- `validation.json`：SHA、来源结果、采购/采收与库存守恒校验。
- `findings.json`：首次分岔、尾期退出候选、动物生产窗口、同一步买卖循环和末日真实销售。

口径边界：

1. `decision_step` 是动作读取的旧观测索引；动作执行后 `recorded_step=decision_step+1`。719 次执行为 `step=0..718`，终态 719；最后 day29/hour23 没有后续 EOD。
2. 种植当日水的分母是实际成功的 PLANT 且已观察到播种日 EOD；另报提交 PLANT、失败/原子阻断，避免只凭成功请求隐藏失败。策略“接受但未执行”的任务需要候选另行登记，动作带无法完整恢复。
3. 缺水消失和动物逃逸是机制事实；是否事先计划停止照护另需证据。不能在见到结果后把损失全部归为主动退出，也不能把自然寿命衰败混进照护失误。
4. 同报损失/生物体日、损失/播种事件等分母；不凭较小的比率选择有利口径。播种当日即未浇水会使初始计数1增至2，因此直接死亡。
5. 采购/采收/销售/喂养/施肥/动物放置与仓满销毁均使用实际引擎提交结果；状态变化本身不是经济收益。
6. 动物没有原生个体 ID。采购到放置的逐只时延采用同类全局 FIFO 归因；在途总量对时间的积分不依赖同类身份匹配。若出现动物库存销毁或初始动物库存，FIFO 个体时延仅能诊断，不能声称精确追踪。
7. 丢弃与终局残留的“价值”是同一时点报价乘数量，仅为资源标价。真实市场逐单位报价会变，采收/搬运有成本，不能将标价称为已实现利润或可保证挽回的现金。
8. 终局仓库和随身库存之外，成熟未收获产物、可收肥料也必须报告；未成熟产量、动物、种子不作现货。不得以整局积累现金轻易稀释终局清仓分母。
9. 此分析不授予 G1 或金牌资格。双席位新种子机制门、强对手门与真实线上证据另行裁决。
