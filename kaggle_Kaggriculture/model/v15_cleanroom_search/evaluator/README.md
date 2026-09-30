# V15 evaluator

这是 V15 clean-room 的 evaluator-private 黑盒评测端。它完成历史强模型池去重、fresh source 分配、candidate/parent 严格配对、source-cluster bootstrap、固定阈值裁决和 score-only 输出。

关键工件：

- `PROTOCOL.md`：正式统计和状态机定义；
- `catalog.py`：官方 CLI 历史提交快照的冻结输入；
- `model_pool_inventory.private.json`：11 个归档的 SHA/serving/code 指纹；
- `lineage_seal.private.json`：11 个非重复模型、7 个谱系、development 代表/hidden 全量覆盖、父模型与锚点映射；
- `pool_registry.private.json`：实际运行用的匿名 registry；
- `source_capacity_audit.json`：历史 exposure 清除后的容量审计；
- `scorecard.py`：严格 task/schema/engine/reward 闭合、谱系内版本平均、谱系等权与 date-stratified source bootstrap；
- `run_evaluation.py`：显式 `--execute` 锁、attempt candidate binding、fresh panel 和 hidden single-use runner；
- `dry_run_report.json`：没有预约 panel、没有启动比赛的任务闭合结果。

重建模型池：

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-evaluator-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.evaluator.inventory
```

运行单测：

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-evaluator-pycache \
  .venv/bin/python -m unittest -v \
  kaggle_Kaggriculture.model.v15_cleanroom_search.evaluator.test_evaluator
```

非消费式 dry-run：

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-evaluator-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.evaluator.run_evaluation \
  --dry-run --attempt-id attempt_001
```

正式 development 命令需要候选归档、firewall 的 evaluator-private candidate seal 和 evaluator-private raw-loader QA，并且必须显式传入 `--execute`。`attempt_001` development 已经运行；以下使用 `attempt_002` 作为后续候选模板，不得据此重跑已消费的 attempt：

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-evaluator-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.evaluator.run_evaluation \
  --attempt-id attempt_002 \
  --stage development \
  --candidate-archive /clean/output/submission.tar.gz \
  --firewall-seal /evaluator-private/candidate_seal.json \
  --candidate-qa /evaluator-private/candidate_qa.json \
  --output-root /evaluator-private/runs/attempt_002/development \
  --feedback-output /evaluator-private/runs/attempt_002/development/score_only_feedback.json \
  --workers 12 \
  --execute
```

hidden 只允许 development 全门通过后的原字节候选；不接受 `--resume`，也不允许指定外部 feedback 输出。

正式矩阵固定为：development `100×7×2×2=2800` 局，hidden `100×11×2×2=4400` 局。计分先对每个版本合并双席，再在谱系内等权平均版本，最后对 7 个谱系各按 `1/7` 等权。development 的 clean resume 只接受当前 sealed task 的无重复 `DONE/DONE` 子集；hidden 永不 resume。
