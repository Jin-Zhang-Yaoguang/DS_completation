"""逐步复算 V14 Q2b 线上回放，定位 shadow、回退和重排是否生效。

输入只能是已经下载的公开/线上 replay。脚本拒绝任何显式标记为 test 的数据，
不运行新对局，也不修改候选策略。V14 与 A2 均从已提交 archive 中加载；每个
候选 seat 都独立从 step=0 重建状态，并把 observation[t] 产生的动作与
replay.steps[t+1].action 对齐。
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from dataclasses import dataclass
import hashlib
import importlib
import json
import math
from pathlib import Path
import statistics
import sys
import tarfile
import tempfile
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[1]
DEFAULT_RAW = HERE.parent / "raw" / "v14"
DEFAULT_ARCHIVE = MODEL_ROOT / "v14_queue_best_response" / "submission.tar.gz"
DEFAULT_MANIFEST = MODEL_ROOT / "v14_queue_best_response" / "submission_manifest.json"
DEFAULT_VALIDATION = (
    MODEL_ROOT
    / "v14_first_principles_search"
    / "validation"
    / "runs"
    / "confirmatory"
    / "v14_queue_stateful_no_mirror"
    / "games.jsonl"
)
EXPECTED_ARCHIVE_SHA256 = "d7d2e8210041d695a10ddc7797efbfd5c4ca3a0f8c33c70e0fd5d597fd4d4f9f"
SHARED_FIELDS = ("day", "farms", "hour", "market", "step", "town")
MODEL_ID = "v14_queue_stateful_no_mirror"
A2_ID = "v12a2_no_shop_gate"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    return value


def action(value: Any) -> dict[str, list[Any]]:
    source = canonical(value) if isinstance(value, Mapping) else {}
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(row or ["PASS"]) for row in source.get("hands", [])],
        "market": [list(row) for row in source.get("market", [])],
    }


def exact(left: Any, right: Any) -> bool:
    return canonical(left) == canonical(right)


def first_json_object(text: str) -> Any:
    """兼容 Kaggle CLI 在 JSON 前后打印 warning/help 的原始输出。"""

    decoder = json.JSONDecoder()
    starts = [index for index, char in enumerate(text) if char in "[{" ]
    for start in starts:
        try:
            value, _ = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, (dict, list)):
            return value
    raise ValueError("no JSON object found")


def unwrap_replay(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        try:
            return unwrap_replay(first_json_object(value))
        except ValueError:
            return None
    if isinstance(value, Mapping):
        if isinstance(value.get("steps"), list) and value.get("name") == "kaggriculture":
            return dict(value)
        for key in ("replay", "result", "data", "episode"):
            if key in value:
                found = unwrap_replay(value[key])
                if found is not None:
                    return found
    return None


def load_replay(path: Path) -> dict[str, Any] | None:
    try:
        value = first_json_object(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None
    replay = unwrap_replay(value)
    if replay is None:
        return None
    explicit_split = str(
        replay.get("split")
        or (replay.get("info") or {}).get("split")
        or ""
    ).lower()
    if explicit_split == "test" or "/test/" in path.as_posix().lower():
        raise PermissionError(f"refusing explicit test replay: {path}")
    return replay


def discover_replay_paths(inputs: Sequence[Path]) -> list[Path]:
    """只收集路径；29MB 级 replay 必须逐个加载，不能把全量同时驻留内存。"""

    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(sorted(item.rglob("*replay*.json")))
        elif item.is_file():
            paths.append(item)
    return sorted(set(path.resolve() for path in paths))


def episode_seat_map(inputs: Sequence[Path], submission_id: int) -> dict[str, int]:
    """从官方 episodes_full 元数据读取 submission 对应 seat。"""

    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(item.rglob("episodes_full.json"))
        elif item.name == "episodes_full.json":
            paths.append(item)
    result: dict[str, int] = {}
    for path in sorted(set(paths)):
        try:
            rows = first_json_object(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            matches = [
                agent for agent in (row.get("agents") or [])
                if int(agent.get("submissionId", -1) or -1) == submission_id
            ]
            if len(matches) != 1:
                continue
            result[str(row.get("id"))] = int(matches[0]["index"])
    return result


def validate_and_extract(archive: Path, manifest_path: Path, target: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_hash = sha256(archive)
    if archive_hash != EXPECTED_ARCHIVE_SHA256:
        raise ValueError(f"unexpected V14 archive sha256: {archive_hash}")
    if manifest.get("archive_sha256") != archive_hash:
        raise ValueError("submission manifest/archive mismatch")
    expected = {row["path"]: row["sha256"] for row in manifest.get("files", [])}
    with tarfile.open(archive, "r:gz") as handle:
        members = handle.getmembers()
        names = [member.name for member in members]
        for member in members:
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"unsafe archive member: {member.name}")
            if not member.isfile():
                raise ValueError(f"non-regular archive member: {member.name}")
        if set(names) != set(expected):
            raise ValueError("archive member set differs from manifest")
        handle.extractall(target, filter="data")
    for relative, wanted in expected.items():
        observed = sha256(target / relative)
        if observed != wanted:
            raise ValueError(f"extracted hash mismatch: {relative}")
    return {
        "archive": str(archive.resolve()),
        "archive_sha256": archive_hash,
        "manifest": str(manifest_path.resolve()),
        "manifest_sha256": sha256(manifest_path),
        "members": len(expected),
    }


class CaptureProxy:
    def __init__(self, delegate: Any) -> None:
        self.delegate = delegate
        self.last_action: dict[str, list[Any]] | None = None

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        self.last_action = action(self.delegate(obs, configuration))
        return copy.deepcopy(self.last_action)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)


@dataclass
class LoadedRuntime:
    main: Any
    core: Any
    a2: Any


def load_runtime(extracted: Path) -> LoadedRuntime:
    # Archive modules use top-level imports (queue_core, a2_agent, base_agent).
    # The probe is one isolated process, so a single verified archive load is safe.
    sys.path.insert(0, str(extracted))
    for name in ("main", "queue_core", "a2_agent", "base_agent"):
        sys.modules.pop(name, None)
    main = importlib.import_module("main")
    core = importlib.import_module("queue_core")
    a2 = importlib.import_module("a2_agent")
    return LoadedRuntime(main=main, core=core, a2=a2)


def full_observation(steps: list[Any], state_index: int, seat: int) -> dict[str, Any]:
    states = steps[state_index]
    if len(states) != 2:
        raise ValueError("expected two seats")
    own = copy.deepcopy(dict(states[seat].get("observation") or {}))
    shared = dict(states[0].get("observation") or {})
    for key in SHARED_FIELDS:
        if key not in own and key in shared:
            own[key] = copy.deepcopy(shared[key])
    own["player"] = seat
    own["step"] = int(shared.get("step", state_index) or state_index)
    return own


def prediction_fields(core: Any, agent_obj: Any, obs_next: Mapping[str, Any], seat: int) -> list[str]:
    fields = []
    farms = list(obs_next.get("farms") or [])
    if len(farms) != 2:
        return ["farms"]
    opponent = 1 - seat
    actual_opponent_money = float((farms[opponent] or {}).get("money", 0.0) or 0.0)
    actual_own_money = float((farms[seat] or {}).get("money", 0.0) or 0.0)
    if agent_obj.predicted_opponent_money is None or not math.isclose(
        actual_opponent_money, float(agent_obj.predicted_opponent_money), abs_tol=1e-9
    ):
        fields.append("opponent_money")
    if agent_obj.predicted_own_money is None or not math.isclose(
        actual_own_money, float(agent_obj.predicted_own_money), abs_tol=1e-9
    ):
        fields.append("own_money")
    actual_inventory = {
        str(key): int(value or 0)
        for key, value in dict((obs_next.get("market") or {}).get("inventory") or {}).items()
    }
    if agent_obj.predicted_market_inventory != actual_inventory:
        fields.append("market_inventory")
    expected_public = agent_obj.predicted_opponent_public
    if expected_public is not None and core._public_farm_state(farms[opponent]) != expected_public:
        fields.append("opponent_public_farm")
    return fields


def reason_delta(before: Mapping[str, Any], after: Mapping[str, Any], reordered: bool) -> str:
    if reordered:
        return "reordered"
    changes = []
    for key in sorted(set(before) | set(after)):
        delta = int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0)
        if delta > 0:
            changes.extend([str(key)] * delta)
    return changes[0] if changes else "unclassified"


def market_shape(value: Mapping[str, Any]) -> dict[str, Any]:
    rows = action(value)["market"]
    ops = Counter(str(row[0]) for row in rows if row)
    products = [str(row[1]) for row in rows if len(row) >= 3 and row[0] == "SELL"]
    return {
        "orders": len(rows),
        "ops": dict(sorted(ops.items())),
        "sell_products": products,
        "sell_only": bool(rows) and sum(ops.values()) == ops.get("SELL", 0),
    }


def probe_seat(
    replay: Mapping[str, Any],
    seat: int,
    runtime: LoadedRuntime,
    *,
    full_search: bool,
) -> dict[str, Any]:
    steps = list(replay.get("steps") or [])
    configuration = copy.deepcopy(dict(replay.get("configuration") or {}))
    candidate = runtime.main.make_agent()
    candidate.parent = CaptureProxy(candidate.parent)
    candidate.opponent_shadow = CaptureProxy(candidate.opponent_shadow)
    actual_a2 = runtime.a2.make_agent()
    baseline_a2 = runtime.a2.make_agent()
    original_best_sell_permutation = runtime.core._best_sell_permutation
    expected_holder: dict[str, Any] = {"action": None, "step": None}
    searched_interventions: list[dict[str, Any]] = []

    def replay_accelerated_best(
        obs: Any,
        parent_action: Mapping[str, Any],
        opponent_action: Mapping[str, Any],
        opponent_obs: Any,
        max_sell_orders: int = 7,
    ) -> Any:
        expected = action(expected_holder["action"])
        if exact(expected, parent_action):
            # 输出已经等于 exact parent A2，不需要重新枚举所有无改动排列。
            return action(parent_action), 0.0, ()
        candidate_row = original_best_sell_permutation(
            obs,
            parent_action,
            opponent_action,
            opponent_obs,
            max_sell_orders=max_sell_orders,
        )
        searched_interventions.append(
            {
                "step": expected_holder["step"],
                "expected_exact": exact(candidate_row[0], expected),
                "advantage": float(candidate_row[1]),
                "products": list(candidate_row[2]),
            }
        )
        return candidate_row

    if not full_search:
        runtime.core._best_sell_permutation = replay_accelerated_best
    opponent = 1 - seat
    rows = []
    candidate_matches = 0
    baseline_matches = 0
    opponent_a2_matches = 0
    shadow_action_matches = 0
    shadow_private_matches = 0
    opening_calls = 0
    opening_opponent_a2_matches = 0
    branch_pairs: Counter[str] = Counter()
    all_reason_counts: Counter[str] = Counter()
    sell_only_queue_calls = 0
    v8_v8_calls = 0
    reorder_steps: list[int] = []
    reorder_wrong_current_shadow_steps: list[int] = []
    previous_faults = 0
    previous_reorders = 0
    first_fault = None
    first_untrusted = None
    first_prediction_mismatch = None
    first_opponent_a2_mismatch = None
    first_candidate_mismatch = None
    first_shadow_action_mismatch = None
    previous_opponent_a2_ok: bool | None = None
    previous_shadow_action_ok: bool | None = None
    previous_mismatch_fields: tuple[str, ...] | None = None
    try:
        for state_index in range(max(0, len(steps) - 1)):
            if len(steps[state_index + 1]) != 2:
                break
            obs = full_observation(steps, state_index, seat)
            opponent_obs = full_observation(steps, state_index, opponent)
            expected_candidate = action(steps[state_index + 1][seat].get("action"))
            expected_opponent = action(steps[state_index + 1][opponent].get("action"))
            expected_holder["action"] = expected_candidate
            expected_holder["step"] = int(obs["step"])
            before_diag = candidate.diagnostics()
            before_skips = dict(before_diag.get("skip_reasons") or {})
            produced = action(candidate(obs, configuration))
            baseline = action(baseline_a2(obs, configuration))
            opponent_a2 = action(actual_a2(opponent_obs, configuration))
            diag = candidate.diagnostics()
            parent_action = action(candidate.parent.last_action)
            shadow_action = action(candidate.opponent_shadow.last_action)
            candidate_ok = exact(produced, expected_candidate)
            baseline_ok = exact(baseline, expected_candidate)
            opponent_a2_ok = exact(opponent_a2, expected_opponent)
            shadow_action_ok = exact(shadow_action, expected_opponent)
            candidate_matches += int(candidate_ok)
            baseline_matches += int(baseline_ok)
            opponent_a2_matches += int(opponent_a2_ok)
            shadow_action_matches += int(shadow_action_ok)
            if int(obs["step"]) < 72:
                opening_calls += 1
                opening_opponent_a2_matches += int(opponent_a2_ok)
            reordered = int(diag.get("reordered_steps", 0)) > previous_reorders
            faulted = int(diag.get("shadow_faults", 0)) > previous_faults
            first_fault_event = faulted and first_fault is None
            if first_fault_event:
                first_fault = int(obs["step"])
            if not bool(diag.get("shadow_trusted")) and first_untrusted is None:
                first_untrusted = int(obs["step"])
            if not candidate_ok and first_candidate_mismatch is None:
                first_candidate_mismatch = int(obs["step"])
            if not opponent_a2_ok and first_opponent_a2_mismatch is None:
                first_opponent_a2_mismatch = int(obs["step"])
            if not shadow_action_ok and first_shadow_action_mismatch is None:
                first_shadow_action_mismatch = int(obs["step"])
            next_obs = full_observation(steps, state_index + 1, seat)
            next_opponent_obs = full_observation(steps, state_index + 1, opponent)
            mismatch_fields = prediction_fields(runtime.core, candidate, next_obs, seat)
            if mismatch_fields and first_prediction_mismatch is None:
                first_prediction_mismatch = {
                    "action_step": int(obs["step"]),
                    "detected_on_step": int(next_obs["step"]),
                    "fields": mismatch_fields,
                }
            private_exact = exact(candidate.opponent_private, next_opponent_obs.get("private") or {})
            shadow_private_matches += int(private_exact)
            event_reason = reason_delta(
            before_skips,
            dict(diag.get("skip_reasons") or {}),
            reordered,
        )
            all_reason_counts[event_reason] += 1
            branch_pair = f"{diag.get('own_branch')} / {diag.get('opponent_branch')}"
            branch_pairs[branch_pair] += 1
            if diag.get("own_branch") == "baseline_v8" and diag.get("opponent_branch") == "baseline_v8":
                v8_v8_calls += 1
            parent_shape = market_shape(parent_action)
            shadow_shape = market_shape(shadow_action)
            if parent_shape["sell_only"] and shadow_shape["sell_only"]:
                sell_only_queue_calls += 1
            if reordered:
                reorder_steps.append(int(obs["step"]))
                if not shadow_action_ok:
                    reorder_wrong_current_shadow_steps.append(int(obs["step"]))
            mismatch_tuple = tuple(mismatch_fields)
            identity_transition = previous_opponent_a2_ok is None or opponent_a2_ok != previous_opponent_a2_ok
            shadow_transition = previous_shadow_action_ok is None or shadow_action_ok != previous_shadow_action_ok
            prediction_transition = previous_mismatch_fields is None or mismatch_tuple != previous_mismatch_fields
            compact_transition_event = (
                (not opponent_a2_ok and identity_transition)
                or (not shadow_action_ok and shadow_transition)
                or (mismatch_fields and prediction_transition)
            )
            if (
                reordered
                or first_fault_event
                or not candidate_ok
                or (compact_transition_event and len(rows) < 40)
            ):
                rows.append(
                {
                    "step": int(obs["step"]),
                    "day": int(obs.get("day", 0) or 0),
                    "hour": int(obs.get("hour", 0) or 0),
                    "reason": event_reason,
                    "candidate_action_exact": candidate_ok,
                    "candidate_differs_from_parent_a2": not exact(produced, parent_action),
                    "recorded_candidate_differs_from_exact_a2": not exact(expected_candidate, baseline),
                    "opponent_action_exact_a2": opponent_a2_ok,
                    "shadow_predicted_action_exact": shadow_action_ok,
                    "shadow_private_exact_next": private_exact,
                    "prediction_mismatch_fields": mismatch_fields,
                    "shadow_trusted_after_call": bool(diag.get("shadow_trusted")),
                    "shadow_faults": int(diag.get("shadow_faults", 0) or 0),
                    "conformance_steps": int(diag.get("conformance_steps", 0) or 0),
                    "clone_distance": int(runtime.core._clone_distance(obs)),
                    "own_branch": diag.get("own_branch"),
                    "shadow_branch": diag.get("opponent_branch"),
                    "candidate_market": market_shape(produced),
                    "parent_a2_market": parent_shape,
                    "recorded_opponent_market": market_shape(expected_opponent),
                    "shadow_market": shadow_shape,
                }
                )
            previous_faults = int(diag.get("shadow_faults", 0) or 0)
            previous_reorders = int(diag.get("reordered_steps", 0) or 0)
            previous_opponent_a2_ok = opponent_a2_ok
            previous_shadow_action_ok = shadow_action_ok
            previous_mismatch_fields = mismatch_tuple
    finally:
        runtime.core._best_sell_permutation = original_best_sell_permutation
    calls = max(0, len(steps) - 1)
    final_diag = candidate.diagnostics()
    return {
        "seat": seat,
        "calls": calls,
        "candidate_action_exact": {
            "matches": candidate_matches,
            "rate": candidate_matches / calls if calls else None,
            "first_mismatch_step": first_candidate_mismatch,
        },
        "recorded_candidate_exact_parent_a2": {
            "matches": baseline_matches,
            "rate": baseline_matches / calls if calls else None,
            "different_steps": calls - baseline_matches,
        },
        "recorded_opponent_exact_a2": {
            "matches": opponent_a2_matches,
            "rate": opponent_a2_matches / calls if calls else None,
            "first_mismatch_step": first_opponent_a2_mismatch,
            "opening_72_matches": opening_opponent_a2_matches,
            "opening_72_calls": opening_calls,
            "opening_72_rate": (
                opening_opponent_a2_matches / opening_calls if opening_calls else None
            ),
        },
        "shadow_predicted_opponent_action": {
            "matches": shadow_action_matches,
            "rate": shadow_action_matches / calls if calls else None,
            "first_mismatch_step": first_shadow_action_mismatch,
        },
        "shadow_private_next": {
            "matches": shadow_private_matches,
            "rate": shadow_private_matches / calls if calls else None,
        },
        "first_prediction_mismatch": first_prediction_mismatch,
        "first_shadow_fault_step": first_fault,
        "first_untrusted_step": first_untrusted,
        "all_call_reason_counts": dict(sorted(all_reason_counts.items())),
        "branch_pair_calls": dict(sorted(branch_pairs.items())),
        "v8_v8_calls": v8_v8_calls,
        "both_predicted_queues_sell_only_calls": sell_only_queue_calls,
        "reorder_steps": reorder_steps,
        "reorder_with_wrong_current_shadow_steps": reorder_wrong_current_shadow_steps,
        "queue_search_verification": {
            "mode": "full" if full_search else "observed_interventions_only",
            "observed_parent_difference_steps_searched": searched_interventions,
            "all_observed_interventions_exact": all(
                row["expected_exact"] for row in searched_interventions
            ),
            "negative_no_change_optimality_recomputed": bool(full_search),
        },
        "events": rows,
        "final_diagnostics": canonical(final_diag),
    }


def identify_candidate_seat(probes: Sequence[Mapping[str, Any]], forced: int | None) -> tuple[int | None, str]:
    if forced is not None:
        return forced, "forced_by_cli"
    exact_seats = [
        int(row["seat"])
        for row in probes
        if row["calls"] > 0
        and row["candidate_action_exact"]["matches"] == row["calls"]
    ]
    if len(exact_seats) == 1:
        return exact_seats[0], "unique_100pct_exact_archive_reproduction"
    if len(exact_seats) == 2:
        return None, "ambiguous_both_seats_exact_v14"
    return None, "no_unique_100pct_archive_reproduction"


def probe_replay(
    path: Path,
    replay: Mapping[str, Any],
    runtime: LoadedRuntime,
    forced_seat: int | None,
    full_search: bool,
) -> dict[str, Any]:
    seats = (forced_seat,) if forced_seat is not None else (0, 1)
    seat_probes = [
        probe_seat(
            replay,
            seat,
            runtime,
            full_search=full_search or forced_seat is None,
        )
        for seat in seats
    ]
    candidate_seat, seat_basis = identify_candidate_seat(seat_probes, forced_seat)
    rewards = [state.get("reward") for state in (replay.get("steps") or [[]])[-1]]
    statuses = [state.get("status") for state in (replay.get("steps") or [[]])[-1]]
    if not rewards or all(value is None for value in rewards):
        rewards = list(replay.get("rewards") or [])
    if not statuses:
        statuses = list(replay.get("statuses") or [])
    margin = None
    outcome = None
    selected = None
    if candidate_seat is not None:
        selected = next(row for row in seat_probes if int(row["seat"]) == candidate_seat)
        if len(rewards) == 2 and all(value is not None for value in rewards):
            margin = float(rewards[candidate_seat]) - float(rewards[1 - candidate_seat])
            outcome = "W" if margin > 0 else "L" if margin < 0 else "T"
    info = dict(replay.get("info") or {})
    return {
        "episode_id": str(info.get("EpisodeId") or replay.get("id") or path.stem),
        "source_path": str(path),
        "source_sha256": sha256(path),
        "module_version": replay.get("module_version"),
        "states": len(replay.get("steps") or []),
        "agents": canonical(info.get("Agents") or []),
        "team_names": canonical(info.get("TeamNames") or []),
        "statuses": statuses,
        "rewards": rewards,
        "candidate_seat": candidate_seat,
        "candidate_seat_basis": seat_basis,
        "margin": margin,
        "outcome": outcome,
        "selected_probe": selected,
        "seat_probe_summaries": [
            {
                "seat": row["seat"],
                "calls": row["calls"],
                "candidate_action_exact": row["candidate_action_exact"],
                "recorded_candidate_exact_parent_a2": row[
                    "recorded_candidate_exact_parent_a2"
                ],
                "recorded_opponent_exact_a2": row["recorded_opponent_exact_a2"],
                "first_prediction_mismatch": row["first_prediction_mismatch"],
                "first_shadow_fault_step": row["first_shadow_fault_step"],
                "reorder_steps": row["reorder_steps"],
                "shadow_trusted_at_end": row["final_diagnostics"].get("shadow_trusted"),
            }
            for row in seat_probes
        ],
    }


def validation_benchmark(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    by_anchor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if str((row.get("source") or {}).get("split", "")).lower() == "test":
                raise PermissionError("validation benchmark unexpectedly contains test")
            if row.get("model_a") != MODEL_ID:
                continue
            status = (
                row.get("agent_diagnostics", {})
                .get(MODEL_ID, {})
                .get("underlying", {})
                .get("model_status", {})
            )
            by_anchor[str(row.get("model_b"))].append({"row": row, "status": status})
    result = {}
    for anchor, records in sorted(by_anchor.items()):
        margins = [float(item["row"].get("margin_a", 0.0) or 0.0) for item in records]
        wins = sum(value > 0 for value in margins)
        ties = sum(value == 0 for value in margins)
        losses = sum(value < 0 for value in margins)
        statuses = [item["status"] for item in records]
        reorder_steps = [int(item.get("reordered_steps", 0) or 0) for item in statuses]
        result[anchor] = {
            "games": len(records),
            "wins_ties_losses": [wins, ties, losses],
            "pure_win_rate": wins / len(records) if records else None,
            "mean_margin": statistics.mean(margins) if margins else None,
            "shadow_trusted_games": sum(bool(item.get("shadow_trusted")) for item in statuses),
            "zero_fault_games": sum(int(item.get("shadow_faults", 0) or 0) == 0 for item in statuses),
            "games_with_reorder": sum(value > 0 for value in reorder_steps),
            "total_reordered_steps": sum(reorder_steps),
            "mean_reordered_steps": statistics.mean(reorder_steps) if reorder_steps else None,
            "branch_pairs": dict(
                sorted(
                    Counter(
                        f"{item.get('own_branch')} / {item.get('opponent_branch')}"
                        for item in statuses
                    ).items()
                )
            ),
        }
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "test_access": False,
        "by_anchor": result,
    }


def aggregate(episodes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    selected = [row for row in episodes if row.get("selected_probe") is not None]
    exact_reproduced = [
        row for row in selected
        if row["selected_probe"]["candidate_action_exact"]["matches"]
        == row["selected_probe"]["calls"]
    ]
    decided = [row for row in selected if row.get("outcome") in {"W", "T", "L"}]
    wins = sum(row["outcome"] == "W" for row in decided)
    ties = sum(row["outcome"] == "T" for row in decided)
    losses = sum(row["outcome"] == "L" for row in decided)
    exact_a2 = [
        row for row in selected
        if row["selected_probe"]["recorded_opponent_exact_a2"]["matches"]
        == row["selected_probe"]["calls"]
    ]
    non_a2 = [row for row in selected if row not in exact_a2]
    with_reorder = [
        row for row in selected
        if int(row["selected_probe"]["final_diagnostics"].get("reordered_steps", 0) or 0) > 0
    ]
    end_trusted = [
        row for row in selected
        if bool(row["selected_probe"]["final_diagnostics"].get("shadow_trusted"))
    ]
    all_calls = sum(int(row["selected_probe"]["calls"]) for row in selected)
    opponent_a2_matches = sum(
        int(row["selected_probe"]["recorded_opponent_exact_a2"]["matches"])
        for row in selected
    )
    return {
        "replays": len(episodes),
        "candidate_seat_identified": len(selected),
        "archive_action_exact_reproduced": len(exact_reproduced),
        "outcomes_w_t_l": [wins, ties, losses],
        "pure_win_rate": wins / len(decided) if decided else None,
        "mean_margin": statistics.mean(float(row["margin"]) for row in decided) if decided else None,
        "exact_a2_opponent_games": len(exact_a2),
        "non_exact_a2_opponent_games": len(non_a2),
        "opponent_action_exact_a2_rate": opponent_a2_matches / all_calls if all_calls else None,
        "games_with_v14_reorder": len(with_reorder),
        "games_shadow_trusted_at_end": len(end_trusted),
        "games_shadow_untrusted_at_end": len(selected) - len(end_trusted),
        "interpretation_flags": {
            "all_selected_archive_exact": len(selected) > 0 and len(exact_reproduced) == len(selected),
            "online_population_contains_non_a2": len(non_a2) > 0,
            "v14_specialized_intervention_exercised": len(with_reorder) > 0,
            "fallback_common": len(selected) > 0 and len(end_trusted) < len(selected) / 2,
        },
    }


def write_markdown(payload: Mapping[str, Any], output: Path) -> None:
    aggregate_row = payload["aggregate"]
    lines = [
        "# V14 Q2b 线上回放 runtime probe",
        "",
        "## 结论边界",
        "",
        "本报告只复算已下载线上回放，不读取 test、不运行新对局、不修改策略。",
        "提交包动作若不能 100% 复现，则该局不应用于机制归因。",
        "",
        "## 汇总",
        "",
        f"- 回放数：{aggregate_row['replays']}",
        f"- 已识别 V14 seat：{aggregate_row['candidate_seat_identified']}",
        f"- 提交包逐步 100% 复现：{aggregate_row['archive_action_exact_reproduced']}",
        f"- 胜/平/负：{aggregate_row['outcomes_w_t_l']}",
        f"- exact-A2 对手局：{aggregate_row['exact_a2_opponent_games']}",
        f"- 非 exact-A2 对手局：{aggregate_row['non_exact_a2_opponent_games']}",
        f"- 对手动作与 A2 的逐步一致率：{aggregate_row['opponent_action_exact_a2_rate']}",
        f"- V14 实际发生重排的局：{aggregate_row['games_with_v14_reorder']}",
        f"- 终局 shadow 仍 trusted / 已 fail-closed：{aggregate_row['games_shadow_trusted_at_end']} / {aggregate_row['games_shadow_untrusted_at_end']}",
        "",
        "## 单局证据",
        "",
        "| episode | seat | outcome | margin | V14动作复现 | 对手=A2 | 首次A2差异 | 首次预测差异 | 首次fault | reorder | 终局trusted |",
        "|---|---:|:---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for episode in payload["episodes"]:
        selected = episode.get("selected_probe")
        if selected is None:
            lines.append(
                f"| {episode['episode_id']} | ? | ? | ? | ? | ? | ? | ? | ? | ? | ? |"
            )
            continue
        calls = selected["calls"]
        candidate_matches = selected["candidate_action_exact"]["matches"]
        a2_matches = selected["recorded_opponent_exact_a2"]["matches"]
        diag = selected["final_diagnostics"]
        prediction = selected.get("first_prediction_mismatch") or {}
        lines.append(
            "| {episode} | {seat} | {outcome} | {margin} | {cm}/{calls} | {am}/{calls} | "
            "{a2first} | {pred} | {fault} | {reorder} | {trusted} |".format(
                episode=episode["episode_id"],
                seat=episode["candidate_seat"],
                outcome=episode.get("outcome"),
                margin=episode.get("margin"),
                cm=candidate_matches,
                am=a2_matches,
                calls=calls,
                a2first=selected["recorded_opponent_exact_a2"].get("first_mismatch_step"),
                pred=prediction.get("detected_on_step"),
                fault=selected.get("first_shadow_fault_step"),
                reorder=diag.get("reordered_steps"),
                trusted=diag.get("shadow_trusted"),
            )
        )
    lines.extend(
        [
            "",
            "## 机制解释",
            "",
            "1. 本地对 A2 的 74.5% 是针对 exact A2 的条件胜率，不是对线上混合对手池的无条件胜率。",
            "2. V14 的新增能力只有 SELL 队列重排；不能通过门时，动作就是父策略 A2。",
            "3. 对手不是 exact A2 时，shadow 通常在公开资金、市场库存或公开农场出现差异后永久 fail-closed；此后 V14 没有新增优势。",
            "4. 检查是滞后一回合的；隐藏状态或无立即公开后果的动作差异可能暂时不被发现。若在此期间重排，优化目标针对的是错误的对手队列。",
            "5. 因此必须同时查看“对手 exact-A2 率、首次 mismatch、重排发生在 mismatch 前还是后、终局 trusted”才能解释线上分数。",
            "",
            "## 本地确认集参照",
            "",
            "```json",
            json.dumps(payload.get("validation_benchmark"), ensure_ascii=False, indent=2),
            "```",
        ]
    )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--validation-games", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--output", type=Path, default=HERE / "runtime_probe.json")
    parser.add_argument("--markdown", type=Path, default=HERE / "runtime_probe.md")
    parser.add_argument("--candidate-seat", type=int, choices=(0, 1), default=None)
    parser.add_argument("--submission-id", type=int, default=55722630)
    parser.add_argument(
        "--full-search",
        action="store_true",
        help="重新枚举所有 SELL 排列；默认只在回放动作确实不同于 parent A2 时枚举",
    )
    args = parser.parse_args()
    inputs = [path.resolve() for path in (args.input or [DEFAULT_RAW])]
    with tempfile.TemporaryDirectory(prefix="v14-runtime-probe-") as temp_dir:
        extracted = Path(temp_dir)
        artifact = validate_and_extract(
            args.archive.resolve(), args.manifest.resolve(), extracted
        )
        runtime = load_runtime(extracted)
        replay_paths = discover_replay_paths(inputs)
        seat_map = episode_seat_map(inputs, int(args.submission_id))
        episodes = []
        for index, path in enumerate(replay_paths, 1):
            replay = load_replay(path)
            if replay is None:
                continue
            episode_id = str(
                (replay.get("info") or {}).get("EpisodeId") or replay.get("id")
            )
            episodes.append(
                probe_replay(
                    path,
                    replay,
                    runtime,
                    args.candidate_seat
                    if args.candidate_seat is not None
                    else seat_map.get(episode_id),
                    bool(args.full_search),
                )
            )
            del replay
            if index % 10 == 0 or index == len(replay_paths):
                print(f"probed {index}/{len(replay_paths)} replays", flush=True)
    payload = {
        "schema": "kaggriculture-v14-online-runtime-probe-1",
        "scope": {
            "online_downloaded_replays_only": True,
            "new_games_run": False,
            "strategy_modified": False,
            "submission_performed": False,
            "test_access": False,
            "action_alignment": "observation[t] -> replay.steps[t+1].action",
        },
        "artifact": artifact,
        "inputs": [str(path) for path in inputs],
        "submission_id": int(args.submission_id),
        "episode_seat_metadata_count": len(seat_map),
        "aggregate": aggregate(episodes),
        "validation_benchmark": validation_benchmark(args.validation_games.resolve()),
        "episodes": episodes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    write_markdown(payload, args.markdown)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "markdown": str(args.markdown.resolve()),
                "aggregate": payload["aggregate"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
