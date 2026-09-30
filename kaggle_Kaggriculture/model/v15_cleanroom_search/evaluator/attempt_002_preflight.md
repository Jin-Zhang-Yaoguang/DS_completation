# Attempt 002 评测治理预检

> 检查时间：2026-08-26 20:40 CST  
> 边界：未读取 `strategy_generator_002` 输出内容；未运行候选、比赛或 QA；未使用 `--execute`；未预约或消费 fresh source；未修改候选、私有注册表和 `state/private`。

## 结论

**评测端可用，但当前不能进入候选审计或正式 development。** `attempt_002` 的 input seal、匿名 feedback 和 evaluator/firewall 单测均通过；非消费式 dry-run 闭合为 2,800 局 development，且私有状态前后完全一致。当前硬阻塞是候选输出目录仍为空。

另有一个必须补上的 fail-closed 检查：三个 sealed read root 的文件目前仍是 owner-writable（`0644/0600`），而 `audit-candidate` 只验证 `input_seal.json` 自身摘要，不会重新散列当前输入闭包。因此生成器结束后，必须先复算 input closure；任何变化都永久拒绝本次候选。

## 预检结果

| 检查项 | 结果 | 证据/边界 |
|---|---|---|
| Input seal schema 与自身摘要 | PASS | `cleanroom/sessions/attempt_002/input_seal.json`；`seal_sha256` 复算一致。 |
| Firewall policy 绑定 | PASS | seal 中 `policy_sha256` 与当前 `firewall/generator_policy.json` 一致。 |
| 三个输入闭包 | PASS | official rules 8 文件、own prior work 7 文件、score feedback 1 文件；逐文件 SHA、大小和 closure SHA 均与 seal 一致。 |
| Allowlist root 隔离 | PASS | 四个 roots 均存在且互不包含。 |
| Score-only feedback | PASS | 唯一文件 `feedback.json`；字段集合、类型、范围和固定 gate 推导全部通过 `validate_public_feedback`。它是 `attempt_001` 的匿名聚合反馈，`overall_passed=false`，不含个局、seed、对手身份、margin、路径或自由文本。 |
| Generator output | **BLOCKED** | `candidates/attempt_002` 在 20:40 检查时为 0 项；无法执行 `audit-candidate`、private QA 或正式 development。 |
| Attempt 002 私有状态 | PASS/未消费 | `state/private` 中无 `attempt_002*` 文件；无 development/hidden panel、candidate binding、seal 或 result。 |
| 显式执行锁 | PASS | 不带 `--execute` 调用返回 `PermissionError: games are locked; pass --execute deliberately`，私有状态摘要不变。 |

## 单测与 dry-run

| 动作 | 结果 |
|---|---|
| Firewall 单测 | 7/7 PASS；覆盖 candidate mutation、feedback reducer、hidden single-use、import/introspection/symlink/denylist rejection。 |
| Evaluator 单测 | 13/13 PASS；覆盖去重、严格 scorecard、重复 key/缺行/额外反馈拒绝、source 与 hidden 状态机、dry-run 闭包及 resume 防重复。 |
| `attempt_002 --dry-run` | exit 0；`games_started=false`、`panels_reserved=false`、`test_sources_selected=0`。 |
| 私有状态前后对照 | 文件数 6→6、panel 数 1→1、attempt 002 记录 0→0；全文件聚合 SHA-256 完全一致。 |

Dry-run 闭包：

| 阶段 | Source | 模型 | 谱系 | candidate | P0 | 总局数 | 每个直接锚点 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development | 100 | 7 | 7 等权 | 1,400 | 1,400 | **2,800** | 200 |
| Hidden | 100 | 11 | 7 等权 | 2,200 | 2,200 | **4,400** | 200 |

当前 source 容量以 live `capacity_audit()` 和刷新后的 `source_capacity_audit.json` 为准：官方记录 2,090，允许 train/validation 1,880，历史已暴露 924，V15 已预约 100，尚余 **856**；按 development 100 + hidden 100，仍支持 **4 个完整 attempt**。当前唯一 V15 panel 是 `attempt_001 development`，attempt 002 尚未预约。

## 候选完成后的强制顺序

以下命令只在候选七个工件全部生成、generator 已停止写入后执行。

### 0. 先复算 sealed inputs

由于当前实现没有在 `audit-candidate` 内复算输入闭包，先用 firewall 同一实现重算三个 read class。必须全部相等：

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-attempt002-input-check-pycache .venv/bin/python - <<'PY'
import json
from pathlib import Path
from kaggle_Kaggriculture.model.v15_cleanroom_search.firewall import firewall

seal_path = Path("kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/input_seal.json")
seal = json.loads(seal_path.read_text(encoding="utf-8"))
assert seal["seal_sha256"] == firewall.sha256_object({k: v for k, v in seal.items() if k != "seal_sha256"})
assert seal["policy_sha256"] == firewall.sha256_file(firewall.POLICY_PATH)
for name, group in seal["read_classes"].items():
    rows = firewall.regular_file_rows(Path(group["root"]), immutable_inputs=True)
    assert rows == group["files"]
    assert firewall._closure(rows) == group["closure_sha256"]
print("attempt_002 sealed inputs: PASS")
PY
```

### 1. `audit-candidate`

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-attempt002-firewall-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.firewall.firewall \
  audit-candidate \
  --output-root kaggle_Kaggriculture/model/v15_cleanroom_search/candidates/attempt_002 \
  --input-seal kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/input_seal.json \
  --denylist kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/generator_denylist.private.json \
  --seal kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/state/private/candidate_seals/attempt_002.json
```

它必须确认恰好七个普通文件、归档只有 `main.py`、manifest/attestation/log/hash 全闭合、零 import/runtime I/O/denylist 命中。

### 2. 立即 `verify-candidate-seal`

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-attempt002-firewall-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.firewall.firewall \
  verify-candidate-seal \
  --output-root kaggle_Kaggriculture/model/v15_cleanroom_search/candidates/attempt_002 \
  --seal kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/state/private/candidate_seals/attempt_002.json
```

### 3. 再做 evaluator-private raw-loader QA

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-attempt002-qa-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.evaluator.qa_candidate \
  --archive kaggle_Kaggriculture/model/v15_cleanroom_search/candidates/attempt_002/submission.tar.gz \
  --output kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/state/private/candidate_qa/attempt_002.json
```

QA 固定运行 3 个公开 smoke seed × 2 orientation = 6 局 self-play；必须 `DONE/DONE`、每席 719 calls、720 states、stderr 0、未访问 test source。这不是 fresh development panel。

### 4. QA 后再次 verify，再进入 development

重复第 2 步，确认 QA 没有改变候选闭包。正式 evaluator 入口还会再次执行同一 seal 校验，并绑定 private QA 文件 SHA。

顺序不得交换为“先 QA、后 firewall”：未经静态 firewall 通过的候选不应先执行。任何 seal、closure 或 QA 不一致都应终止 attempt，不得修补原 seal 后继续。

## 正式 development 的准确命令（本次未执行）

`evaluator/README.md` 的示例已落后于当前 CLI：代码现在强制要求 `--candidate-qa`。Attempt 002 应使用：

```bash
PYTHONPYCACHEPREFIX=/tmp/v15-attempt002-evaluator-pycache \
  .venv/bin/python -m kaggle_Kaggriculture.model.v15_cleanroom_search.evaluator.run_evaluation \
  --attempt-id attempt_002 \
  --stage development \
  --candidate-archive kaggle_Kaggriculture/model/v15_cleanroom_search/candidates/attempt_002/submission.tar.gz \
  --firewall-seal kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/state/private/candidate_seals/attempt_002.json \
  --candidate-qa kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/state/private/candidate_qa/attempt_002.json \
  --output-root kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/runs/attempt_002/development \
  --feedback-output kaggle_Kaggriculture/model/v15_cleanroom_search/evaluator/runs/attempt_002/development/score_only_feedback.json \
  --workers 12 \
  --execute
```

注意：以上只是经源码核对的未来正式命令，本预检没有执行。`--execute` 会先写 candidate binding，再独占预约 100 个 development source；预约即消费。正常启动前应再次确认：候选停止写入、seal/QA 均 PASS、attempt 002 私有路径仍不存在、output-root 与 feedback-output 均不存在。

## 阻塞与风险

1. **当前硬阻塞**：candidate output 为空；不能开始任何会执行候选或消费 source 的步骤。
2. **输入不可变性缺口**：sealed inputs 是 owner-writable，且后续 audit 不会自动重算；必须执行步骤 0。若要求对恶意生成器形成真正安全边界，只能改用独立用户、容器或 VM。
3. **文档漂移**：`evaluator/README.md` 的正式命令缺少当前必需的 `--candidate-qa`；不得照抄旧示例。
4. **状态字段语义**：`source_capacity_audit.json.games_started=false` 表示容量审计本身没有启动比赛，不代表 V15 历史从未运行；attempt 001 已有 development 结果和 100-source 预约。

