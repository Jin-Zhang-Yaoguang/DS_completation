#!/usr/bin/env python3
"""从 Top20 Replay 构造三日、日级、全局合同数据。"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any

from contract_features import PRODUCTS, state_features, window_targets


HERE = Path(__file__).resolve().parent
DATA = HERE / "dataset"
RECEIPTS = (
    HERE / "replay_data" / "receipt.json",
    HERE / "replay_data" / "top20_cli_receipt.json",
)
CUTOFF = date(2026, 8, 20)
ENGINE = "1.32.7"
FORMAL_PANELS = {"own_online_primary", "official_daily_confirmation"}
FORBIDDEN = {"episode_id", "replay_sha256", "teacher", "submission_id", "seat", "seed", "future_shop", "future_action"}


def teacher_identity(source: dict, teacher: dict) -> tuple[int, str, str, int]:
    return int(source["episode_id"]), str(source["sha256"]), str(teacher["team"]), int(teacher["seat"])


def load_sources() -> tuple[list[dict], dict[str, int]]:
    """同一教师轨迹只保留一次；任何 dev 标记优先于 train。"""
    selected: dict[tuple[int, str, str, int], dict] = {}
    receipt_counts: Counter = Counter()
    for receipt_path in RECEIPTS:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        for source in receipt["rows"]:
            if date.fromisoformat(source["actual_date"]) < CUTOFF:
                raise ValueError(f"过期 Replay: {source['episode_id']}")
            if str(source.get("module_version")) != ENGINE:
                raise ValueError(f"规则版本不一致: {source['episode_id']}")
            for teacher in source.get("teachers", []):
                key = teacher_identity(source, teacher)
                candidate = {**source, "teachers": [teacher], "receipt": receipt_path.name}
                path = Path(candidate["path"])
                if not path.exists():
                    alternatives = (
                        HERE / "replay_data" / "top20_cli_raw" / path.name,
                        HERE / "replay_data" / "own_online_raw" / path.name,
                    )
                    replacement = next((value for value in alternatives if value.exists()), None)
                    if replacement is None:
                        raise FileNotFoundError(path)
                    candidate["path"] = str(replacement)
                old = selected.get(key)
                if old is None or (old["split"] == "train" and candidate["split"] == "dev"):
                    selected[key] = candidate
                receipt_counts[receipt_path.name] += 1
    # 防止一局在训练与开发间泄漏：episode 只要在任一 dev 轨迹中出现，整局归 dev。
    dev_episodes = {int(v["episode_id"]) for v in selected.values() if v["split"] == "dev"}
    for value in selected.values():
        if int(value["episode_id"]) in dev_episodes:
            value["split"] = "dev"
    return list(selected.values()), dict(receipt_counts)


def state_at(replay: dict, seat: int, turn: int) -> dict:
    return replay["steps"][min(turn, len(replay["steps"]) - 1)][seat]["observation"]


def base_row(source: dict, teacher: dict) -> dict[str, Any]:
    panel = str(source["source_panel"])
    return {
        "episode_id": int(source["episode_id"]), "replay_sha256": str(source["sha256"]),
        "actual_date": str(source["actual_date"]), "split": str(source["split"]),
        "source_panel": panel, "evidence_role": "FORMAL_PANEL" if panel in FORMAL_PANELS else "TRAINING_AUXILIARY_NOT_PROMOTION_EVIDENCE",
        "teacher": str(teacher["team"]), "submission_id": int(teacher.get("submission_id", 0) or 0),
        "leaderboard_rank": int(teacher.get("leaderboard_rank", 0) or 0), "seat": int(teacher["seat"]),
    }


def build_rows(replay: dict, source: dict) -> tuple[list[dict], list[dict], list[dict]]:
    teacher = source["teachers"][0]
    seat, base = int(teacher["seat"]), base_row(source, teacher)
    macro, daily, global_rows = [], [], []
    for day in range(0, 30, 3):
        turn, stop = day * 24, min((day + 3) * 24, 719)
        obs = state_at(replay, seat, turn)
        previous = state_at(replay, seat, max(0, turn - 72)) if turn else None
        target = window_targets(replay, seat, turn, stop)
        macro.append({**base, "decision_day": day, "features": state_features(obs, previous), "target": target})
    for day in range(30):
        turn, stop = day * 24, min((day + 1) * 24, 719)
        obs = state_at(replay, seat, turn)
        previous = state_at(replay, seat, max(0, turn - 24)) if turn else None
        own = window_targets(replay, seat, turn, stop)
        rival = window_targets(replay, 1-seat, turn, stop)
        daily.append({**base, "decision_day": day, "cycle_day": day - day % 3, "features": state_features(obs, previous), "target": own})
        global_target = {
            "own_money_delta": own["money_delta"], "rival_money_delta": own["rival_money_delta"],
            "money_gap_delta": own["money_gap_delta"],
            **{f"own_sell_{item}": own.get(f"sell_{item}", 0.0) for item in PRODUCTS},
            **{f"rival_sell_{item}": rival.get(f"sell_{item}", 0.0) for item in PRODUCTS},
            **{f"own_early_sell_{item}": own.get(f"early_sell_{item}", 0.0) for item in PRODUCTS},
        }
        global_rows.append({**base, "decision_day": day, "features": state_features(obs, previous), "target": global_target})
    return macro, daily, global_rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> int:
    sources, receipt_counts = load_sources()
    by_replay: dict[tuple[int, str], list[dict]] = defaultdict(list)
    for source in sources:
        by_replay[(int(source["episode_id"]), str(source["sha256"]))].append(source)
    macro, daily, global_rows = [], [], []
    for index, ((episode, sha), group) in enumerate(sorted(by_replay.items()), 1):
        path = Path(group[0]["path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError(f"Replay SHA 不匹配: {episode}")
        replay = json.loads(raw)
        if len(replay.get("steps", [])) != 720:
            raise ValueError(f"Replay 不完整: {episode}")
        for source in group:
            a, b, c = build_rows(replay, source)
            macro.extend(a); daily.extend(b); global_rows.extend(c)
        if index % 20 == 0 or index == len(by_replay):
            print(f"processed {index}/{len(by_replay)} replays", flush=True)
    DATA.mkdir(parents=True, exist_ok=True)
    write_jsonl(DATA / "macro_3day.jsonl", macro)
    write_jsonl(DATA / "daily_contract.jsonl", daily)
    write_jsonl(DATA / "global_market.jsonl", global_rows)
    feature_names = sorted({key for row in macro for key in row["features"]})
    if FORBIDDEN.intersection(feature_names):
        raise ValueError(f"非法运行时特征: {sorted(FORBIDDEN.intersection(feature_names))}")
    teacher_split = Counter((row["teacher"], row["split"]) for row in daily[::30])
    manifest = {
        "schema": "kaggriculture-v122-top20-contract-dataset-v1",
        "admission": {"minimum_actual_date": str(CUTOFF), "engine": ENGINE, "dedupe": "episode_id+replay_sha256+teacher+seat"},
        "alignment": "steps[t].observation -> unordered aggregate contract over steps[t+1:t+h].actions",
        "runtime_uses_future_actions": False, "split_unit": "episode_id", "dev_wins_on_split_conflict": True,
        "episodes": len(by_replay), "teacher_trajectories": len(daily) // 30,
        "rows": {"macro_3day": len(macro), "daily_contract": len(daily), "global_market": len(global_rows)},
        "split": dict(Counter(row["split"] for row in macro)),
        "teacher_coverage": {
            "train": len({row["teacher"] for row in daily if row["split"] == "train"}),
            "dev": len({row["teacher"] for row in daily if row["split"] == "dev"}),
            "counts": {f"{teacher}|{split}": count for (teacher, split), count in sorted(teacher_split.items())},
        },
        "source_panels": dict(Counter(row["source_panel"] for row in macro)),
        "receipt_teacher_rows_before_dedupe": receipt_counts,
        "feature_count": len(feature_names), "forbidden_runtime_fields": sorted(FORBIDDEN),
        "status": "TRAINING_DATA_READY_NOT_PROMOTION_EVIDENCE",
    }
    (HERE / "dataset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
