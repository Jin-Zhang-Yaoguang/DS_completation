"""Closed-loop representative-loss reruns with compact event traces."""

from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V10_FACTORY = HERE.parent / "v10_replay_lolo_router" / "agent_factory.py"
PREMIUM_PRODUCTS = frozenset({"STRAWBERRY", "MELON", "MILK", "WOOL"})
ANIMAL_PRODUCTS = frozenset({"EGG", "MILK", "WOOL"})
BASE_PRICES = {
    "STRAWBERRY": 120.0,
    "MELON": 250.0,
    "MILK": 160.0,
    "WOOL": 200.0,
}


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _load_factory():
    name = f"_v11_trace_factory_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, V10_FACTORY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load V10 factory: {V10_FACTORY}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def _plain_map(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    items = getattr(value, "items", None)
    if callable(items):
        return {str(key): item for key, item in items()}
    return {}


def compact_action(action: Mapping[str, Any] | None) -> dict[str, Any]:
    action = dict(action or {})
    farmer = list(action.get("farmer") or ["PASS"])
    hands = [list(item or ["PASS"]) for item in (action.get("hands") or [])]
    active_hands = [
        {"hand": index, "action": item}
        for index, item in enumerate(hands)
        if item and item[0] != "PASS"
    ]
    market = [list(item) for item in (action.get("market") or [])]
    result: dict[str, Any] = {}
    if farmer and farmer[0] != "PASS":
        result["farmer"] = farmer
    if active_hands:
        result["hands"] = active_hands
    if market:
        result["market"] = market
    return result


def action_digest(action: Mapping[str, Any] | None) -> str:
    encoded = json.dumps(
        dict(action or {}), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _tile_counts(tiles: Any) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in tiles if isinstance(tiles, (list, tuple)) else []:
        for tile in row if isinstance(row, (list, tuple)) else []:
            if tile is None:
                counts["EMPTY"] += 1
            elif tile == "LOCKED":
                counts["LOCKED"] += 1
            else:
                kind = str(_get(tile, "kind", "UNKNOWN") or "UNKNOWN")
                counts[f"KIND:{kind}"] += 1
                crop = _get(tile, "crop")
                animal = _get(tile, "animal")
                if crop:
                    counts[f"CROP:{crop}"] += 1
                if animal:
                    counts[f"ANIMAL:{animal}"] += 1
    return dict(sorted(counts.items()))


def farm_summary(obs: Any) -> list[dict[str, Any]]:
    result = []
    for farm in _get(obs, "farms", []) or []:
        result.append(
            {
                "money": float(_get(farm, "money", 0.0) or 0.0),
                "hands": len(_get(farm, "hands", []) or []),
                "hires_today": int(_get(farm, "hires_today", 0) or 0),
                "tiles": _tile_counts(_get(farm, "tiles", [])),
            }
        )
    return result


def private_summary(obs: Any) -> dict[str, Any]:
    private = _get(obs, "private", {}) or {}
    shed = {
        key: int(value or 0)
        for key, value in _plain_map(_get(private, "shed", {}) or {}).items()
        if int(value or 0)
    }
    seeds = {
        key: int(value or 0)
        for key, value in _plain_map(_get(private, "seeds", {}) or {}).items()
        if int(value or 0)
    }
    carried: Counter[str] = Counter()
    for inventory in _get(private, "inventories", []) or []:
        for key, value in _plain_map(inventory).items():
            carried[key] += int(value or 0)
    return {
        "shed": dict(sorted(shed.items())),
        "seeds": dict(sorted(seeds.items())),
        "carried": dict(sorted(carried.items())),
        "shed_total": sum(shed.values()),
    }


def market_summary(obs: Any) -> dict[str, Any]:
    market = _get(obs, "market", {}) or {}
    return {
        "prices": {
            key: float(value or 0.0)
            for key, value in sorted(_plain_map(_get(market, "prices", {}) or {}).items())
        },
        "inventory": {
            key: int(value or 0)
            for key, value in sorted(_plain_map(_get(market, "inventory", {}) or {}).items())
        },
    }


def _numeric_delta(current: Mapping[str, Any], previous: Mapping[str, Any]) -> dict[str, Any]:
    result = {}
    for key in sorted(set(current) | set(previous)):
        now = current.get(key, 0)
        before = previous.get(key, 0)
        if isinstance(now, Mapping) or isinstance(before, Mapping):
            nested = _numeric_delta(
                now if isinstance(now, Mapping) else {},
                before if isinstance(before, Mapping) else {},
            )
            if nested:
                result[key] = nested
        elif isinstance(now, (int, float)) and isinstance(before, (int, float)):
            change = now - before
            if change:
                result[key] = change
        elif now != before:
            result[key] = {"from": before, "to": now}
    return result


class TraceAgent:
    def __init__(self, agent: Any, seat: int, model_id: str) -> None:
        self.agent = agent
        self.seat = int(seat)
        self.model_id = str(model_id)
        self.records: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None):
        action = self.agent(obs, configuration)
        prices = market_summary(obs)["prices"]
        self.records.append(
            {
                "step": int(_get(obs, "step", len(self.records)) or 0),
                "day": int(_get(obs, "day", 0) or 0),
                "hour": int(_get(obs, "hour", 0) or 0),
                "action": compact_action(action),
                "action_sha16": action_digest(action),
                "farms": farm_summary(obs),
                "private": private_summary(obs),
                "market": {"prices": prices, "inventory": market_summary(obs)["inventory"]},
                "unlocked_shops": [
                    str(item)
                    for item in (_get(_get(obs, "town", {}) or {}, "unlocked_shops", []) or [])
                ],
            }
        )
        return action


def compress_records(traces: Sequence[TraceAgent]) -> dict[str, Any]:
    by_seat = {trace.seat: trace.records for trace in traces}
    action_events = []
    action_differences = []
    farm_events = []
    market_events = []
    town_events = []
    daily_snapshots = []
    findings = Counter()
    operation_counts = {0: Counter(), 1: Counter()}
    product_flows = {0: Counter(), 1: Counter()}
    opening_digests = {0: hashlib.sha256(), 1: hashlib.sha256()}
    max_steps = max((len(records) for records in by_seat.values()), default=0)
    previous_farms: list[dict[str, Any]] = []
    previous_market: dict[str, Any] = {}
    previous_shops: list[str] = []
    previous_money_leader: int | None = None
    for index in range(max_steps):
        records = [by_seat.get(seat, []) for seat in (0, 1)]
        rows = [items[index] if index < len(items) else None for items in records]
        step = int(next((row["step"] for row in rows if row is not None), index))
        for seat, row in enumerate(rows):
            if row is None:
                continue
            if row["action"]:
                action_events.append({"step": step, "seat": seat, **row["action"]})
            if step < 72:
                opening_digests[seat].update(row["action_sha16"].encode("ascii"))
            farmer = row["action"].get("farmer") or []
            if farmer:
                operation_counts[seat][f"farmer:{farmer[0]}"] += 1
            for hand in row["action"].get("hands", []):
                order = hand.get("action") or []
                if order:
                    operation_counts[seat][f"hand:{order[0]}"] += 1
            for order in row["action"].get("market", []):
                if order:
                    operation_counts[seat][f"market:{order[0]}"] += 1
                if len(order) >= 3 and order[0] == "SELL":
                    product = str(order[1])
                    quantity = int(order[2] or 0)
                    product_flows[seat][f"SELL:{product}"] += quantity
                    price = float(row["market"]["prices"].get(product, 0.0))
                    if product in PREMIUM_PRODUCTS and price < 0.55 * BASE_PRICES[product]:
                        findings["low_price_premium_sells"] += 1
                    if product in ANIMAL_PRODUCTS and quantity > 12:
                        findings["large_animal_sell_batches"] += 1
                    if quantity > 20:
                        findings["large_general_sell_batches"] += 1
                elif len(order) >= 3 and str(order[0]).startswith("BUY"):
                    product_flows[seat][f"{order[0]}:{order[1]}"] += int(order[2] or 0)
            sell_products = [
                str(order[1])
                for order in row["action"].get("market", [])
                if len(order) >= 3 and order[0] == "SELL"
            ]
            findings["duplicate_sell_order_events"] += sum(
                count - 1 for count in Counter(sell_products).values() if count > 1
            )
            if row["private"]["shed_total"] >= 95:
                findings["near_shed_overflow_events"] += 1
        if rows[0] is not None and rows[1] is not None:
            if rows[0]["action_sha16"] != rows[1]["action_sha16"]:
                action_differences.append(
                    {
                        "step": step,
                        "seat0_sha16": rows[0]["action_sha16"],
                        "seat1_sha16": rows[1]["action_sha16"],
                    }
                )
            current_farms = rows[0]["farms"]
            if len(current_farms) == 2:
                money_delta = float(current_farms[0]["money"]) - float(current_farms[1]["money"])
                leader = 0 if money_delta > 0 else 1 if money_delta < 0 else None
                if (
                    leader is not None
                    and previous_money_leader is not None
                    and leader != previous_money_leader
                ):
                    findings["public_money_lead_reversals"] += 1
                if leader is not None:
                    previous_money_leader = leader
            for seat, farm in enumerate(current_farms):
                before = previous_farms[seat] if seat < len(previous_farms) else {}
                delta = _numeric_delta(farm, before)
                if delta and previous_farms:
                    farm_events.append({"step": step, "seat": seat, "delta": delta})
                    animal_delta = (delta.get("tiles") or {}) if isinstance(delta.get("tiles"), Mapping) else {}
                    if any(
                        str(key).startswith("ANIMAL:") and float(value) < 0
                        for key, value in animal_delta.items()
                        if isinstance(value, (int, float))
                    ):
                        findings["animal_count_drop_events"] += 1
            previous_farms = current_farms
            current_market = rows[0]["market"]
            market_delta = _numeric_delta(current_market, previous_market)
            if market_delta and previous_market:
                market_events.append({"step": step, "delta": market_delta})
            previous_market = current_market
            current_shops = list(rows[0].get("unlocked_shops") or [])
            before_counts, current_counts = Counter(previous_shops), Counter(current_shops)
            unlocked = list((current_counts - before_counts).elements())
            if unlocked:
                town_events.append({"step": step, "unlocked_shops": unlocked})
            previous_shops = current_shops
            if rows[0]["hour"] == 0 or index == max_steps - 1:
                daily_snapshots.append(
                    {
                        "step": step,
                        "day": rows[0]["day"],
                        "farms": current_farms,
                        "private": [rows[0]["private"], rows[1]["private"]],
                    }
                )
    for seat in (0, 1):
        if by_seat.get(seat):
            final_private = by_seat[seat][-1]["private"]
            unsold = sum(
                int(value)
                for key, value in final_private["shed"].items()
                if key not in {"COW", "GOOSE", "SHEEP"}
            )
            if unsold:
                findings["terminal_unsold_events"] += 1
    first_production_difference = None
    for index in range(min(len(by_seat.get(0, [])), len(by_seat.get(1, [])))):
        left = by_seat[0][index]["action"]
        right = by_seat[1][index]["action"]
        if left.get("farmer") != right.get("farmer") or left.get("hands") != right.get("hands"):
            first_production_difference = int(by_seat[0][index]["step"])
            break
    return {
        "schema": "kaggriculture-v11-compact-replay-trace-1",
        "compression": "only active actions, numeric market/farm deltas, and daily snapshots; no raw observations",
        "calls_by_seat": {str(seat): len(by_seat.get(seat, [])) for seat in (0, 1)},
        "first_production_difference_step": first_production_difference,
        "opening_action_sha256_by_seat": {
            str(seat): opening_digests[seat].hexdigest() for seat in (0, 1)
        },
        "operation_counts_by_seat": {
            str(seat): dict(sorted(operation_counts[seat].items())) for seat in (0, 1)
        },
        "product_flows_by_seat": {
            str(seat): dict(sorted(product_flows[seat].items())) for seat in (0, 1)
        },
        "action_events": action_events,
        "action_differences": action_differences,
        "market_events": market_events,
        "farm_events": farm_events,
        "town_events": town_events,
        "daily_snapshots": daily_snapshots,
        "findings": dict(sorted(findings.items())),
    }


def _official_source(
    source: Mapping[str, Any], data_root: Path | None
) -> dict[str, Any]:
    if str(source.get("split", "")).lower() == "test":
        raise ValueError("sealed test source is forbidden in strategy optimisation")
    result = {
        "date": str(source.get("date") or source.get("source_date") or "")[:10],
        "seed": int(source["seed"]),
        "episode_id": str(source.get("episode_id") or ""),
        "split": str(source.get("split") or "unknown"),
        "source_path": str(source.get("source_path") or source.get("source_relpath") or ""),
        "verified_raw_replay": False,
    }
    if data_root is None:
        return result
    candidates = []
    if result["source_path"]:
        candidates.append(data_root / result["source_path"])
    if result["date"] and result["episode_id"]:
        candidates.append(data_root / result["date"] / f"{result['episode_id']}.json")
    path = next((item.resolve() for item in candidates if item.is_file()), None)
    if path is None:
        result["raw_replay_error"] = "source replay file not found"
        return result
    raw = path.read_bytes()
    result.update(
        {
            "raw_replay_path": str(path),
            "raw_replay_size_bytes": len(raw),
            "raw_replay_sha256": hashlib.sha256(raw).hexdigest(),
        }
    )
    try:
        import orjson

        payload = orjson.loads(raw)
    except ImportError:
        payload = json.loads(raw)
    info = payload.get("info") if isinstance(payload, Mapping) else {}
    raw_seed = int((info or {}).get("seed"))
    raw_episode = str((info or {}).get("EpisodeId"))
    if raw_seed != result["seed"] or raw_episode != result["episode_id"]:
        raise ValueError(
            f"official replay identity mismatch: expected {result['episode_id']}/{result['seed']}, "
            f"got {raw_episode}/{raw_seed}"
        )
    result["verified_raw_replay"] = True
    return result


def rerun_match(
    registry_path: str | Path,
    model_a: str,
    model_b: str,
    model_a_seat: int,
    source: Mapping[str, Any],
    data_root: str | Path | None = None,
) -> dict[str, Any]:
    """Rerun one official seed in the live engine; never use TraceAgent playback."""

    from kaggle_environments import make

    factory = _load_factory()
    registry = factory.load_registry(registry_path)
    raw_a = factory.create_agent(registry, model_a)
    raw_b = factory.create_agent(registry, model_b)
    a_seat = int(model_a_seat)
    trace_a = TraceAgent(raw_a, a_seat, model_a)
    trace_b = TraceAgent(raw_b, 1 - a_seat, model_b)
    agents = [trace_a, trace_b] if a_seat == 0 else [trace_b, trace_a]
    official = _official_source(
        source, Path(data_root).expanduser().resolve() if data_root else None
    )
    env = make("kaggriculture", configuration={"seed": official["seed"]}, debug=False)
    env.run(agents)
    statuses = [str(state.status) for state in env.state]
    rewards = [float(state.reward or 0.0) for state in env.state]
    traces = [trace_a, trace_b] if a_seat == 0 else [trace_b, trace_a]
    return {
        "schema": "kaggriculture-v11-representative-rerun-1",
        "closed_loop": True,
        "trace_agent_playback": False,
        "official_source": official,
        "model_a": model_a,
        "model_b": model_b,
        "model_a_seat": a_seat,
        "seat_models": [model_a, model_b] if a_seat == 0 else [model_b, model_a],
        "statuses": statuses,
        "rewards": rewards,
        "done": statuses == ["DONE", "DONE"],
        "steps": len(env.steps),
        "events": compress_records(traces),
    }
