# V13 双基线封存验证协议

## 结论先行

V13 只能在完全未暴露的 `2026-08-18` 至 `2026-08-20` 官方 `train/validation` source 上开发，且每个候选必须在同一 source、双席位下同时直接对战：

- `v12_incumbent_r002`
- `v12a2_no_shop_gate`（A2，主要改进基线）

`test` 被硬性禁止。筛选集 36 个 source，确认集 100 个 source；两者互斥，也与 Router-fit、V11 全部已落盘评测、V12 screen/formal/QA/消融等所有可发现的 source 互斥。

赛前候选集合固定为 `v13a_a2_no_wool_throttle`、`v13c_a2_v8_no_wool_throttle`、`v13d_a2_public_winrisk_gate`；terminal716 因 18 次探测零新增订单，在打包前否决。不得看完部分 screen 后追加或替换候选。

## 冻结顺序

1. `candidate_slate.json` 已把候选 ID、父策略、机制、registry entry、源码 main、当前 GO archive、manifest、QA 和每个 clean-package member 全部绑定。
2. 运行 `python freeze_protocol.py --verify`，任何 hash、暴露集合或 panel 变化都立即失败。
3. 所有候选只使用 `screen_seed_manifest.jsonl`。每个候选恰好运行一次 144 场：36 source × 2 anchor × 2 席位；原子 consume lock 禁止换输出路径重跑。
4. 按 `evaluation_contract.json` 的预注册门槛选出最多一个 finalist。筛选集 CI 只做诊断，不作为显著性声明。
5. 三名候选全部完成后，`seal_finalist.py` 按预注册排序生成唯一 finalist seal；确认集只允许该 finalist 打开一次。运行 400 场：100 source × 2 anchor × 2 席位。
6. 确认集失败后不得在该 panel 上调参、重命名或重跑另一个 finalist；只能建立新的、诚实标记为 post-confirmatory 的研究周期。

## 评测实现约束

复用 `v10_replay_lolo_router/pairwise_evaluate.py` 的闭环执行器和任务函数。五个模型均从当前 GO archive 安全解包，registry 显式使用 `entrypoint=agent`，并绑定包内 main、A2/base、runtime、weights、policy 和完整专家文件；不允许 repository import 路径替代线上包路径。

```text
candidate vs v12_incumbent_r002
candidate vs v12a2_no_shop_gate
```

run fingerprint 必须绑定：

- `evaluation_contract.json` 的文件 hash；
- 当前 panel 的 `records_sha256`；
- combined registry 与所有 reachable serving code 的 hash；
- V10 evaluator/agent factory/router/runtime implementation fingerprint；
- 精确的两个定向 pair、候选 ID、双席位和 source 列表。

resume 仅允许相同 run fingerprint。任何旧 fingerprint 行、重复 task、缺失 task、未知 source、未知模型、非有限 reward、非 `DONE/DONE`、`error != null` 都按失败处理，不得从统计中静默剔除。

审计器还会从封存 manifest 重算 fingerprint 和每个 task ID，并逐行核对 schema、engine、closed-loop、trace 标记、seat_models、rewards、reward_a/reward_b、margin_a 和 score_a；伪造一致任务数量但语义矛盾的行不能进入统计。

## 指标口径

“胜率”与 Kaggle 对局得分率分开报告：

- 纯胜率：`W / (W + T + L)`；
- 对局得分率：`(W + 0.5T) / (W + T + L)`；
- margin：候选终局 reward 减 anchor 终局 reward。

每个 source 的两个相反席位是一个统计 cluster。95% CI 使用按日期分层、source-cluster 重采样的 10,000 次 percentile bootstrap。还必须逐日期、逐候选席位报告 W/T/L、纯胜率、得分率和平均 margin。

## 完整性命令

冻结或重建（只允许在任何候选比赛开始前）：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/freeze_protocol.py
```

评测前只读核验：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/freeze_protocol.py --verify
```

封存执行器会生成同一个 run fingerprint 下的两个定向 pair，并在结束后自动审计：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/run_dual_anchor.py \
  --phase screen \
  --candidate CANDIDATE_ID \
  --registry /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/clean_screen_registry.json \
  --jsonl /absolute/path/to/games.jsonl \
  --run-manifest /absolute/path/to/run_manifest.json \
  --audit-output /absolute/path/to/audit.json \
  --workers 12
```

确认阶段还必须显式传入 `--execute-confirmatory`。若只需对已完成结果做只读复核：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/audit_dual_anchor.py \
  --phase screen \
  --candidate CANDIDATE_ID \
  --games /absolute/path/to/games.jsonl \
  --run-manifest /absolute/path/to/run_manifest.json \
  --registry /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v13_dual_anchor_search/protocol/clean_screen_registry.json \
  --output /absolute/path/to/audit.json
```

确认阶段把 `--phase screen` 改成 `--phase confirmatory`。审计器要求每个 source 对两个 anchor 都恰有两个相反席位，且全部 `DONE/DONE`。

## 封存产物

- `exposure_inventory.json`：保守暴露审计及每个证据文件 hash；
- `screen_panel.json` / `screen_seed_manifest.jsonl`：36-source 筛选集；
- `confirmatory_panel.json` / `confirmatory_seed_manifest.jsonl`：100-source 一次性确认集；
- `evaluation_contract.json`：指标、筛选和确认门槛；
- `candidate_slate.json`：精确候选、锚点、包与完整 serving closure；
- `clean_screen_registry.json` / `clean_submissions/`：与当前 GO archive 字节一致的本地评测入口；
- `run_dual_anchor.py`：绑定代码/registry/evaluator/panel/门槛指纹的定向闭环执行器；
- `seal_finalist.py`：三份 screen 闭合后确定唯一 finalist；
- `protocol_seal.json` / `protocol_assets.sha256`：协议完整性封印。
