# Kaggriculture V11：迭代联赛

本目录实现“完整模型联赛 → 回放诊断 → 新候选 → 下一轮验证 → 淘汰”的可恢复闭环。它不会读取历史选手动作作为模型输入；官方 2026-08-18、19、20 Replay 只提供真实比赛 seed、日期和数据来源。每场评测仍由 `kaggle_environments.make("kaggriculture")` 创建新环境，让两个模型闭环行动。

## 固定实验协议

- 初始池必须是 V10 预注册的 14 个模型：4 个 baseline、8 个规则变体、`rule_router`、`learned_router`。
- V10 Router 最终 fit 使用的 200 个开发 seed 由 metadata-only exclusion 文件永久排除；编排器拒绝含 reward/score/feature/action 等 outcome 字段的 exclusion 输入。1,880 个 `train + validation` seed 因此剩余 1,680 个联赛开发 seed。
- 每轮按日分层抽取 100 个全局唯一 seed。日期配额为 34/33/33，额外的一个配额随轮次轮换。
- 首个 cycle 固定 16 轮，cycle 内不放回。若目标仍未达则开启下一 cycle：先按每个日期内的全局最小使用次数选 seed，同层再由 salt 打散；新 cycle 内仍不放回，且禁止重复历史完整 panel。若本轮首次评测 pending 候选，还要永久排除它的上一轮设计 panel，即使正好跨 cycle。报告记录 cycle、cycle_round、全局/分日 min-max reuse 和 exclusion SHA-256。
- 每轮 salt 由根 seed、轮次、cycle、manifest 和 exclusion SHA-256 计算，`panel.json` 保存完整来源和哈希。
- 每个无序模型对使用同一批 100 seed，交换先后手，因此恰好 200 场。N 个模型一轮运行 `N×(N-1)/2×200` 场。
- 胜 1 分、平 0.5 分、负 0 分。轮次总分用于排序。
- 同分顺序依次比较：同分组直接对战积分、全局平均金币差、最差单一对手得分率、未解决错误数、`model_id` 字典序。
- 只有当本轮实际参赛池超过 16，才淘汰本轮排名最后者。V1/V2/V5/V8 baseline 没有永久保护。

## Pending 防泄漏机制

策略优化器读取第 r 轮结果后提出的新策略，不能再用第 r 轮已经见过的 panel 补赛并据此决定生死：这会产生自适应泄漏。

因此流程固定为：

1. 第 r 轮完成并生成 `league_summary.json`、`games.jsonl` 和 `report.md`。
2. 策略优化器生成并完成 720 回合 `DONE/DONE` smoke 的候选。
3. `add-candidate` 只把候选记为 `pending_candidate`，不让它使用第 r 轮成绩，也不立即淘汰任何模型。
4. 第 r+1 轮开始时激活该候选；它和全部模型在一批全新 100 seed 上完成矩阵，并硬验与第 r 轮设计 panel 的 seed 交集为 0（跨 cycle 也不例外）。
5. 若本轮有 17 个模型，包括新候选在内全部按本轮成绩公平排序，淘汰最后一名。
6. 当池中恰好 16 个模型且四个 baseline 都已离池，实验结束，终止轮不再要求生成无用候选。

## 输出

每轮目录为 `runs/round_NNN/`：

- `panel.json`：日期分层 seed、split、episode 和 panel SHA-256。
- `round_meta.json`：模型与代码指纹、评测器指纹、manifest 指纹、任务数和运行指纹。
- `games.jsonl`：V10 原生 append-only 闭环逐局结果；失败记录保留，完全一致的成功重复可审计去重，冲突成功直接 hard-fail。
- `pairwise_summary.json`：V10 完整性、双席位配对和错误审计。
- `league_summary.json`：总积分、W-D-L、N×N 有向矩阵、排名和淘汰规则。
- `report.md`：以 `# 第 N 轮迭代` 开头的中文报告。矩阵单元格格式为 `胜-平-负 / 得分`。
- `attempt_audit.json` / `failure_audit.json`：每个 task 跨进程恢复累计最多三次；第 4 条记录或三次后仍无严格成功都会 hard-fail，不插值、不把技术错误记为负场、不淘汰。

全局 `pool_state.json` 是唯一状态源，采用原子写入和自身 SHA-256 校验，记录 active/pending/retired 模型、cycle 内已用 seed、跨 cycle 复用计数、永久 exclusion、每个模型的不可变 serving 指纹、Router ancestry、联赛/独立准入实现哈希和历史轮次。registry seal、模型源码、权重、评测器、manifest、exclusion 或编排实现被未授权修改时，恢复会显式拒绝。

## 使用方式

V10 的 `final_registry.json` 只有在 learned Router 正式训练并冻结后才存在。正式链还会重算其 serving 指纹，并要求与 `freeze_chain_final14_audit.json` 中审定的有序 14 模型完全一致；同名替换实现会被拒绝。

第一步先运行正式 FastRouter 等价评测。它只使用冻结的 100 个 validation 开发 seed，不读取 test：`rule_router / learned_router × V1/V2/V5/V8 × 100 seed × 双席位 = 1,600` 个比较任务，每个任务分别运行原 Router 和 Fast Router，因此实际为 3,200 局。JSONL 是 append-only，可按 `task_id` 恢复；外来指纹和冲突成功记录会 hard-fail。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/verify_fast_router.py \
  --registry kaggle_Kaggriculture/model/v10_replay_lolo_router/final_registry.json \
  --training-report kaggle_Kaggriculture/model/v10_replay_lolo_router/learned_router_training_report.json \
  --fit-exclusions kaggle_Kaggriculture/model/v10_replay_lolo_router/router_fit_source_exclusions.json \
  --split validation --formal --workers 20 \
  --games kaggle_Kaggriculture/model/v11_iterative_league/fast_router_equivalence_formal.jsonl \
  --output kaggle_Kaggriculture/model/v11_iterative_league/fast_router_equivalence_formal_report.json
```

第二步只读重开 report 和 JSONL，重算 1,600 个任务的覆盖、逐动作哈希、状态、奖励、选择、前缀、异常、源 registry/模型/权重/代码/manifest/exclusion 指纹：

```bash
.venv/bin/python -c "from pathlib import Path; from kaggle_Kaggriculture.model.v11_iterative_league.verify_fast_router import validate_formal_report; print(validate_formal_report(Path('kaggle_Kaggriculture/model/v11_iterative_league/fast_router_equivalence_formal_report.json'), Path('kaggle_Kaggriculture/model/v10_replay_lolo_router/final_registry.json')))"
```

第三步运行独立 fresh challenge。它从正式 report 文件 SHA 确定性抽取 4 个 validation source，重新执行 `2 Router × 4 opponent × 双席位 = 64` 个 comparison（128 局），并把完整 fresh 原始证据与正式 JSONL 逐行对照。所选 source 必须属于 Router-fit exclusion，test access 必须为 false：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/audit_fast_router_challenge.py \
  --report kaggle_Kaggriculture/model/v11_iterative_league/fast_router_equivalence_formal_report.json \
  --sources 4 --workers 20 \
  --output kaggle_Kaggriculture/model/v11_iterative_league/fast_router_fresh_challenge.json
```

第四步才允许物化。materializer 会再次严格重读正式 report/JSONL 和 fresh challenge，并把两份报告绝对路径、实际 SHA、独立实现 SHA 和 serving 指纹注入 registry seal；缺失或伪造任一证据都会拒绝：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/materialize_fast_registry.py \
  --source kaggle_Kaggriculture/model/v10_replay_lolo_router/final_registry.json \
  --equivalence-report kaggle_Kaggriculture/model/v11_iterative_league/fast_router_equivalence_formal_report.json \
  --challenge-report kaggle_Kaggriculture/model/v11_iterative_league/fast_router_fresh_challenge.json \
  --output kaggle_Kaggriculture/model/v11_iterative_league/fast_registry.json
```

快速 Router 在 step 0–72 仍同步全部专家；选择完成后只运行被选专家。若被选专家异常，它返回显式 PASS 并暴露错误，不使用状态已经滞后的 anchor。旧 `fast_router_equivalence.json`（schema v1）及旧延迟文件仅是历史 smoke，不是正式门禁证据，不能用于 materialize 或 league init。

初始化联赛：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/league.py init \
  --registry kaggle_Kaggriculture/model/v11_iterative_league/fast_registry.json \
  --manifest kaggle_Kaggriculture/model/v10_replay_lolo_router/evaluation_seed_manifest.jsonl \
  --excluded-sources kaggle_Kaggriculture/model/v10_replay_lolo_router/router_fit_source_exclusions.json \
  --state kaggle_Kaggriculture/model/v11_iterative_league/pool_state.json
```

运行或恢复一轮；成功任务不会重跑，失败或非 `DONE/DONE` 任务最多自动重试三次：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/league.py run-round \
  --state kaggle_Kaggriculture/model/v11_iterative_league/pool_state.json \
  --workers 20 --max-attempts 3
```

## 策略优化器交接协议

优化器应读取当前轮的 `league_summary.json` 和 `games.jsonl`，输出 `proposal.json` 以及包含新条目的 `registry_next.json`。`proposal.json` 至少包含：

```json
{
  "model_id": "candidate_r001_x",
  "registry_path": "registry_next.json",
  "registry_entry": {
    "id": "candidate_r001_x",
    "kind": "python",
    "path": "../../candidate_agent.py",
    "factory": "create_agent",
    "factory_kwargs": {
      "parent_registry": "runs/round_001/strategy/registry_next.json",
      "parent_id": "baseline_v1",
      "mutation_name": "value_slot_priority",
      "mutation_params": {"min_sell_orders": 2},
      "candidate_id": "candidate_r001_x"
    },
    "code_paths": ["../../candidate_agent.py", "../../mutation_catalog.py"],
    "parent_models": ["baseline_v1"]
  },
  "parent_models": ["baseline_v1"],
  "hypothesis": "可证伪的改进假设",
  "change_scope": "精确描述代码和行为改动",
  "code_paths": ["candidate_agent.py", "mutation_catalog.py"],
  "source_round": 1,
  "first_evaluation_round": 2,
  "same_panel_performance_claim": false,
  "smoke_evidence": {
    "path": "/absolute/path/candidate_smoke.json",
    "sha256": "...",
    "passed": true,
    "functionality_only": true,
    "performance_evidence": false,
    "source_panel_reused_only_for_smoke": true,
    "source_round": 1,
    "first_evaluation_round": 2,
    "seeds": 6,
    "candidate_games": 12,
    "parent_control_games": 12,
    "all_done": true,
    "all_720_steps": true,
    "zero_stderr": true,
    "real_action_difference": true,
    "changed_games": 1,
    "action_difference_steps": 1,
    "done": true,
    "statuses": ["DONE", "DONE"],
    "steps": 720
  }
}
```

上述相对路径只示意字段结构；正式文件由 `strategy_optimizer.py` 生成，不要手写或改写 wrapper、factory 与父 registry 路径。

准入命令：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/league.py add-candidate \
  --state kaggle_Kaggriculture/model/v11_iterative_league/pool_state.json \
  --proposal path/to/proposal.json \
  --registry-next path/to/registry_next.json --workers 12
```

候选必须使用全新的 immutable `model_id`，直接父模型必须仍 active 且等于本轮 leader。准入只接受白名单 `candidate_agent.py + mutation_catalog.py` 市场残差包装器，并解析其运行时 `parent_registry`，确认实际父策略 serving 指纹没有陈旧或替换。optimizer 的 smoke report 必须以绝对路径和 SHA 绑定 proposal、registry、candidate/parent serving 指纹及设计 panel 的 6 个真实来源；`add-candidate` 还会独立重跑候选与父版本各 12 局，不能信任 proposal 中的布尔值。候选 registry 可追加条目，但必须跨多代原样保留 Fast/V10 的 manifest、exclusion、equivalence 和 pre-test seals。

实际调用策略优化器：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/strategy_optimizer.py \
  --games kaggle_Kaggriculture/model/v11_iterative_league/runs/round_001/games.jsonl \
  --summary kaggle_Kaggriculture/model/v11_iterative_league/runs/round_001/league_summary.json \
  --registry kaggle_Kaggriculture/model/v11_iterative_league/fast_registry.json \
  --output-dir kaggle_Kaggriculture/model/v11_iterative_league/runs/round_001/strategy \
  --round 1
```

优化器会生成：

- `diagnosis.json` / `diagnosis.md`：排名、对手/日期/席位分层、金币差尾部、领先与垫底模型差距来源。
- `representative_replays.json.gz`：惨败、窄负和反复失败谱系的闭环重跑；仅保存活跃动作、市场/农场数值差分和每日快照，不保存原始 observation。
- `candidate_smoke.json`：6 个开发 seed、双席位的候选/父版本对照，共 24 局功能测试；必须全部 720 回合、`DONE/DONE`、零 stderr 且存在真实动作差异。
- `proposal.json` / `registry_next.json`：下一轮唯一 pending 候选及自动注册表。

候选空间位于 `mutation_catalog.py`。当前包含 11 种市场残差和多组参数模板；判重键是 `(direct_parent, mutation, canonical_params)`，因此同一机制只有在父策略或证据参数不同的情况下才可形成新假设。所有 mutation 都冻结父版本的 farmer/hands 生产动作，不能伪装成新生产路线。

单独复核准入门槛可运行：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v11_iterative_league/admission_smoke.py \
  --registry path/to/current_registry.json \
  --source-manifest kaggle_Kaggriculture/model/v10_replay_lolo_router/evaluation_seed_manifest.jsonl \
  --parent parent_model_id --candidate-id candidate_id \
  --mutation value_slot_priority --params-json '{"min_sell_orders":2}' \
  --round 1 --workers 12 --output /tmp/v11_candidate_smoke.json
```

## 测试

```bash
.venv/bin/python -m unittest discover \
  -s kaggle_Kaggriculture/model/v11_iterative_league/tests -v
```

单元测试覆盖日期分层、跨轮零交集、积分与矩阵、共享 panel 完整性、冲突成功结果拒绝、一级标题报告、pending 防泄漏、Fast Router RNG 对照公平性、证据防伪和终局 test 逐行语义重算。`verify_fast_router.py` 的正式任务另在真实环境中核对 100 个 validation seed、双席位的逐动作、选择、终局奖励、状态和错误完全等价。
