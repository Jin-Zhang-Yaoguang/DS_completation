#!/usr/bin/env python3
"""Package the hash-locked candidate only after the untouched gate passes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
TARGET = MODEL / "v123_top20_role_phase_hmoe"
FREEZE = HERE / "v123_candidate_freeze_manifest.json"
SEEDS = HERE / "v123_frozen_untouched_seeds.json"
GATE = HERE / "v123_frozen_gate_vs_v120.json"
DEV = HERE / "whyme_phase_release_dev32.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    require(not TARGET.exists(), f"target already exists: {TARGET}")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    seeds = json.loads(SEEDS.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    dev = json.loads(DEV.read_text(encoding="utf-8"))

    sources = {
        "whyme_phase_release_candidate.py": HERE / "whyme_phase_release_candidate.py",
        "whyme_phase_core.py": HERE / "whyme_phase_core.py",
        "whyme_role_phase_contract.json": HERE / "whyme_role_phase_contract.json",
    }
    for name, expected in freeze["candidate_files"].items():
        require(sha256(sources[name]) == expected, f"candidate changed after freeze: {name}")
    opponent = MODEL / "v120_hierarchical_top5_distillation" / "main.py"
    require(sha256(opponent) == freeze["opponent_files"]["v120_hierarchical_top5_distillation/main.py"], "V120 changed after freeze")
    require(sha256(SEEDS) == freeze["seed_file_sha256"], "frozen seed panel changed")

    expected_rows = {(int(seed), seat) for seed in seeds["seeds"] for seat in (0, 1)}
    actual_rows = {(int(row["seed"]), int(row["seat"])) for row in gate["rows"]}
    require(actual_rows == expected_rows and len(gate["rows"]) == len(expected_rows), "gate rows do not match frozen panel")
    require(gate["dual_seat"] is True and gate["all_719_turns"] is True, "gate was not a complete dual-seat run")
    require(gate["win_rate"] > 0.70, "candidate failed the strict >70% V120 gate")

    TARGET.mkdir(parents=False)
    copies = {
        HERE / "whyme_phase_release_candidate.py": TARGET / "main.py",
        HERE / "whyme_phase_core.py": TARGET / "whyme_phase_core.py",
        HERE / "whyme_role_phase_contract.json": TARGET / "whyme_role_phase_contract.json",
        HERE / "dataset_manifest.json": TARGET / "dataset_manifest.json",
        HERE / "top20_snapshot.json": TARGET / "top20_snapshot.json",
        HERE / "training_report.json": TARGET / "top20_training_report.json",
        HERE / "goal_target_training_report.json": TARGET / "goal_target_training_report.json",
        HERE / "whyme_structured_market_training_report.json": TARGET / "whyme_teacher_training_report.json",
        DEV: TARGET / "development_vs_v120.json",
        SEEDS: TARGET / "frozen_untouched_seeds.json",
        FREEZE: TARGET / "candidate_freeze_manifest.json",
    }
    for source, destination in copies.items():
        shutil.copyfile(source, destination)

    raw_gate_sha = sha256(GATE)
    frozen_report = dict(gate)
    frozen_report["schema"] = "kaggriculture-v123-frozen-untouched-gate-v1"
    frozen_report["seed_role"] = "frozen_untouched"
    frozen_report["one_shot"] = True
    frozen_report["raw_research_report_sha256"] = raw_gate_sha
    (TARGET / "frozen_gate_vs_v120.json").write_text(
        json.dumps(frozen_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    contract = json.loads((TARGET / "whyme_role_phase_contract.json").read_text(encoding="utf-8"))
    manifest = {
        "schema": "kaggriculture-v123-release-manifest-v1",
        "version": "V123",
        "kind": "independent_top20_role_phase_hmoe",
        "strategy_parent": None,
        "entrypoint": "main.py:agent",
        "teacher_lineage": {
            "selection_panel": "Kaggriculture gold Top20",
            "teachers_covered_train": 20,
            "teachers_covered_dev": 20,
            "unique_episodes_combined": 339,
            "teacher_trajectories_combined": 407,
            "top20_auxiliary_teacher_trajectories": 320,
            "selected_teacher": "Whyme Labs",
            "selected_teacher_trajectories": 16,
            "semantic_contract_source": contract["source"],
        },
        "runtime_contract": contract["runtime_contract"],
        "experts": ["role_path", "resource_budget", "market_queue", "room_guard", "terminal_liquidation"],
        "development_vs_v120": {
            "games": dev["games"], "wins_ties_losses": dev["wins_ties_losses"],
            "win_rate": dev["win_rate"], "mean_margin": dev["mean_margin"],
        },
        "frozen_untouched_vs_v120": {
            "games": gate["games"], "wins_ties_losses": gate["wins_ties_losses"],
            "win_rate": gate["win_rate"], "mean_margin": gate["mean_margin"],
            "required": ">0.70", "passed": True,
        },
        "kaggle_submission_created": False,
    }
    manifest["file_sha256"] = {
        path.name: sha256(path)
        for path in sorted(TARGET.iterdir())
        if path.is_file() and path.name not in {"release_manifest.json", "README.md"}
    }
    (TARGET / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    readme = """# V123 Top20 Role-Phase HMoE

V123 是独立策略，不继承 V120，也不是逐回合动作 tape。

- 数据：Top20 全覆盖；综合 339 局、407 条教师轨迹，Top20 CLI 辅助面板贡献 320 条轨迹。
- 选择：跨 Top20 筛选后选择 Whyme Labs 稳定路线，并用其 16 条轨迹验证教师内一致性。
- 单位层：按日、按角色保存语义任务队列，由当前棋盘状态恢复最短路径；不保存逐步移动动作。
- 市场层：每 6 小时一个资源预算专家，由实时现金、库存、容量和价格执行；无逐回合动作查询、无未来特征。
- 闭环专家：市场队列、仓容保护、出售排序和终局清仓。
- 开发集对 V120：60/0/4，胜率 93.75%。
- 未触碰冻结集对 V120：62/0/2，胜率 96.875%，64 局均完成 719 回合。

入口：`main.py:agent`。本目录未产生 Kaggle 提交。
"""
    (TARGET / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"target": str(TARGET), "win_rate": gate["win_rate"], "files": len(list(TARGET.iterdir()))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
