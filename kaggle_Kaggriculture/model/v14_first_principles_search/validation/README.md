# V14 全新双锚点验证协议

## 当前状态

本目录目前只封存 source 元数据与执行协议，**没有启动任何新游戏，也没有读取 test outcome**。候选包尚未最终生成，因此 `sealed_runtime/` 有意不存在；任何 screen dry-run、screen 执行或 confirmatory 执行都会因为缺少 exact archive seal 而 fail-closed。

## 数据隔离

- 数据源：官方 `2026-08-18` 至 `2026-08-20` daily manifest 中的 `train/validation` source identity 与 environment seed。
- 继承隔离：绑定 V13 已审计的 652-seed 暴露账本，覆盖 V10 Router-fit、V11 Round1--3、V12 screen/formal/QA/消融。
- 增量隔离：重新扫描所有 V13 文本产物，以及 V14 当前 `dev_runs/oracle/alternatives` 等本验证目录之外的文本产物；只要出现官方 seed token 就隔离。
- 本协议不打开 daily replay payload，不读取历史 reward/action，不选择 test。
- `screen36` 为每日 12 个 source；`confirmatory100` 为 34/33/33 个 source。两者互斥，且都与完整暴露 union 互斥。
- 每次 dry-run/执行前都会重新扫描当前 V13/V14 证据；新增旧-panel开发文件会被记录为 evidence drift，但只有当前证据触及已选 screen/confirm source 才硬失败，避免“同一已隔离 seed 被重复落盘”造成无意义换 panel。

## 候选与任务闭包

候选最多 3 个。每个候选必须先完成独立 package QA，再把精确 `submission.tar.gz`、manifest、QA、registry entry、source main 和安全解包后的每个 member 全部 hash 绑定。评测只从 clean archive 的 raw `agent` entrypoint 加载，不允许仓库源码路径替代线上包。

每个候选 screen：

- candidate vs `v12a2_no_shop_gate`：36 source × 双席 = 72 场；
- candidate vs `v12_incumbent_r002`：36 source × 双席 = 72 场；
- 合计 144 场；每个 sealed candidate 只能消费 screen 一次。

唯一 finalist confirmatory：

- 每个 anchor：100 source × 双席 = 200 场；
- 合计 400 场；
- 必须显式传 `--execute-confirmatory`，并且全协议只有一个原子 confirmatory consume lock。

## 硬门与统计口径

- A2：`wins / all games >= 0.65`；
- r002：`wins / all games > 0.50`；
- tie 留在分母中但不计 win；
- Kaggle 对局得分率 `(W + 0.5T) / games` 只报告，绝不代替纯胜率门槛；
- 95% CI 按日期分层、以同一 source 的双席位为 cluster 做 10,000 次确定性 bootstrap；
- 同时输出逐日期、逐候选席位的 W/T/L、纯胜率、得分率和 margin。

## 完整性边界

每行结果都重新校验：JSON schema、task ID、run fingerprint、pair、source identity、engine、closed-loop、trace flag、candidate seat、`seat_models`、`DONE/DONE`、error、finite rewards，以及由席位重算的 `reward_a/reward_b/margin_a/score_a`。重复/缺失/未知 task、未知 source、非有限 reward 或任意语义矛盾都直接失败，不能静默剔除。

## 使用顺序

只读复核已封存 panel（此命令不会启动游戏）：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v14_first_principles_search/validation/verify_protocol.py
```

候选最终打包并通过 QA 后，一次性封存 1--3 个 exact archive：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v14_first_principles_search/validation/seal_candidates.py \
  --candidate MODEL_A=/absolute/path/to/MODEL_A_PACKAGE_DIR \
  --candidate MODEL_B=/absolute/path/to/MODEL_B_PACKAGE_DIR
```

封存后先 dry-run 核对任务数量与 fingerprint；缺任何 artifact 时 dry-run 也会失败：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v14_first_principles_search/validation/run_dual_anchor.py \
  --phase screen --candidate MODEL_A --dry-run \
  --jsonl /absolute/new/run/MODEL_A/games.jsonl \
  --run-manifest /absolute/new/run/MODEL_A/run_manifest.json \
  --audit-output /absolute/new/run/MODEL_A/audit.json
```

所有 sealed candidate 各完成一次 screen 后，派生唯一 finalist：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v14_first_principles_search/validation/seal_finalist.py \
  --screen-root /absolute/screen/run/root
```

最后才允许一次 confirmatory：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v14_first_principles_search/validation/run_dual_anchor.py \
  --phase confirmatory --candidate FINALIST --execute-confirmatory \
  --jsonl /absolute/new/confirm/games.jsonl \
  --run-manifest /absolute/new/confirm/run_manifest.json \
  --audit-output /absolute/new/confirm/audit.json
```

确认集失败后，不允许换 candidate、调参或在同一 panel 上重跑。
