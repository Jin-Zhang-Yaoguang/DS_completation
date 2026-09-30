# V12 修复包 raw-loader 独立红队结论

时间：2026-08-23（Asia/Taipei）  
范围：只验证线上加载/运行/等价性；未改策略、未读取正式面板、未提交 Kaggle。

## 结论

| 包 | 归档 SHA-256 | 结论 |
|---|---|---|
| `v12a2_no_shop_gate` | `e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8` | **GO** |
| `v12_incumbent_r002` | `6ff786cbba1a6440f844f9c77da934f6dd10b55e43f57b2bd852753cd21ae136` | **GO** |

只允许提交表中这两个新 SHA；旧归档分别已经在线上证实为 silent no-op 和 import ERROR。

## 独立验证结果

两包都满足：

- 通过实际 `kaggle_environments.agent.get_last_callable(read_file(main.py), path=main.py)` 加载；被选中的最后 callable 均为 `agent`。
- raw exec 的 globals 确实没有 `__file__`，两包仍能从干净解包目录加载 bundled runtime。
- 隔离进程启动前无法 import `kaggle_Kaggriculture`，运行后也没有任何项目源码模块被加载。
- Python `3.11.14` 对归档内全部 `.py` 执行 `py_compile` 通过。
- 3 个既有 QA seed × 双席位，共 6 局/包；每局均为 720 状态、719 次候选调用、`DONE/DONE`。
- 719 次 raw action 均严格只有 `farmer/hands/market` 三个字段且类型正确；每局都有有效非 no-op 动作。
- 干净 raw-loader 轨迹与当前 source factory 逐步 action 完全一致，终局 reward 完全一致。
- stdout/stderr 均为空。

## 审计文件

- verifier：`verify_raw_loader.py`，SHA-256 `9ca63d5f8876d7816a7b818fdb813b1115a0488d225266d421a368031209f05d`
- A2 报告：`v12a2_no_shop_gate_report.json`，SHA-256 `bc8ad95f3c3e7d1043b0c5318b84d7d388b31defcd26e5cfd0ca657ff364c3fc`
- r002 报告：`v12_incumbent_r002_report.json`，SHA-256 `1128d0767cda4f45e64c298dd1bea58b37283b2e73629d7688e01e79bb2e72f5`
- 线上旧包根因与原始 Replay/log：`online_failures/ROOT_CAUSE.md` 及同目录证据文件。

