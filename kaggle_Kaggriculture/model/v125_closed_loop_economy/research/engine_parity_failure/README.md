# 本地引擎槽位修复与已有 trace 核验

结论和验证范围见 `REPORT.md`。可用评测入口为 `../../evaluation/run_match_v3.py`，参数保持 v2 不变；其引擎指向本目录 `slotfix_build_v2/`，不覆盖原快引擎。入口与引擎 SHA 已冻结于 `v3_engine_fingerprint.json`。

对已有 official 运行目录补纯状态 parity：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/engine_parity_failure/verify_saved_trace_parity.py \
  --run-dir kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/已有运行目录 \
  --output kaggle_Kaggriculture/model/v125_closed_loop_economy/research/engine_parity_failure/新的核验目录
```

`--run-dir` 可以重复，默认核对每个目录全部已保存游戏；`--game-index` 可指定同一索引。开始前冻结来源清单、源 SHA 和新引擎 SHA，拒绝重复源游戏键与 trace SHA，拒绝覆盖已有输出。源 DONE 必须有 719 个动作，源 ERROR 只重放已保存前缀。遇首差记录双方状态并停止，不假装剩余局完成。若源 DONE，还会核对官方重放末态摘要、现金与源记录完全相同。

所有动作来自原 trace，不调用候选或对手，因此只证明同一已有动作序列在两个引擎中一致，**不能称为新独立比赛，也不能由固定动作重放断言自适应策略重新运行会不变**。输出 `games.jsonl` 保留 `source_status_retained`，不会修改源结果。

主要文件：

- `replay_failure.py`：原引擎首差重现；结果在 `r5_balanced_reproduction/`。
- `price_sequence_proof.json`：商品、库存、实际官方价与压缩队列解释。
- `build_local_v2.py`：使用现有缓存头文件编译本地隔离模块；拒绝覆盖现有二进制。
- `validate_slotfix_v2.py`、`slotfix_validation.json`：425 动作和 12 个双席微场景。
- `test_runner_v3.py`、`runner_v3_validation/`：8 项 runner 回归；不写旧测试输出。
- `verify_saved_trace_parity.py`：通用已存动作带核验入口；仅在调用时运行。
- `v3_saved_trace_interface_smoke/`：通用入口对已有 425 动作失败前缀的验证。

原 `run_match.py`、`run_match_v2.py`、`analyze_trace.py`、`summarize_g1.py`、社区原 C++ 代码/二进制、候选和错误结果均未修改。本目录保留初始构建/导入失败证据；不安装依赖、不提交、不读新官方 Replay/Blind。
