# V122 Top20 Contract HMoE

状态：`RESEARCH_ACTIVE / CLOSED_LOOP_GATE_FAILED / NOT_PROMOTABLE / NOT_SUBMITTED`。

V122 不复制冠军逐步动作带。它从当前排行榜 Top20 的公开 Replay 中学习三层合同，再由自有状态恢复执行器生成原子动作：

1. 三日 Router：8 个由真实三日资源组合聚类得到的合同专家；
2. 日级 Router：20 个日级生产、移动和畜牧合同专家；
3. 全局层：三日资金差 critic 与双方卖出预测专家；
4. 空间层：训练集日初状态蒸馏出的逐格畜牧/作物概率，不含动作序列；
5. 执行层：中心畜牧、外圈作物、回仓和市场任务均从当前观测重建。

## 数据

- Kaggle CLI 固化当前 Top20，每位 12 条训练、4 条开发，最新 4 条只记元数据、不下载；
- Top20 辅助面板去重后 255 局、320 条教师轨迹，训练/开发均覆盖 20/20；
- 合并 own-online 与 official-daily 后，最终为 339 局、407 条教师轨迹；
- 数据按 episode 隔离，任何 split 冲突整局归开发；
- Top20 CLI 数据只作训练辅助，不替代 own-online 主面板或 official-daily 确认面板。

## 当前结果

离线开发集：三日合同损失相对固定合同下降 `70.68%`，日级合同下降 `77.25%`；资金差 critic 相对均值 RMSE 改善 `12.00%`。

闭环开发烟测对 V120 仍为 `0%`。空间先验版本 4 局 `0/0/4`；不同小麦库存阈值的 7 组搜索也全部 `0/0/4`。因此没有运行完整 64-seed 确认门，没有生成提交包，也不能称为 V122 候选模型。

失败点已定位为执行器的多工人任务调度与共享市场博弈：合同能被识别，但无法把 Top20 的约 14 个畜牧、59 格作物和卖出压价节奏同时兑现。

## 复现

```bash
python3 sync_top20_replays.py
python3 augment_top20_cli.py
python3 build_contract_dataset.py
/opt/anaconda3/bin/python3 train_contract_hmoe.py
python3 build_spatial_priors.py
python3 audit_no_tape.py
/opt/anaconda3/bin/python3 evaluate_vs_v120.py --seeds 2
```
