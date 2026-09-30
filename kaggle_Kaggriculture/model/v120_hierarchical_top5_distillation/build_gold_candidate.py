#!/usr/bin/env python3
"""Build the selected Top5-distilled V120 into a standalone main.py."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import zlib


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
BASE = MODEL / "v119_center_livestock_spatial_moe/main.py"
ROUTE_ID = "OceanMix__104547425__s0"


def selected_route() -> tuple[list[dict], dict]:
    receipt = json.loads((HERE / "replay_data/download_receipt.json").read_text(encoding="utf-8"))
    for source in receipt["rows"]:
        replay = json.loads(Path(source["path"]).read_text(encoding="utf-8"))
        for teacher in source["teachers"]:
            route_id = f"{teacher['team']}__{source['episode_id']}__s{teacher['seat']}"
            if route_id != ROUTE_ID:
                continue
            seat = int(teacher["seat"])
            actions = [replay["steps"][turn + 1][seat].get("action") for turn in range(719)]
            metadata = {
                "distillation_pool": "19 teacher trajectories from current Top5 public episodes",
                "selected_route_id": route_id,
                "teacher": teacher["team"],
                "submission_id": int(teacher["submission_id"]),
                "episode_id": int(source["episode_id"]),
                "source_seed": int(source["seed"]),
                "source_seat": seat,
                "replay_sha256": source["sha256"],
                "actions": len(actions),
                "selection_objective": "maximize minimum dual-seat win rate versus V76 and V20 on development seeds",
            }
            return actions, metadata
    raise KeyError(ROUTE_ID)


def main() -> int:
    actions, metadata = selected_route()
    payload = json.dumps(actions, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    encoded = base64.b85encode(zlib.compress(payload, 9)).decode("ascii")
    text = BASE.read_text(encoding="utf-8")
    start = text.index("# --- V119: champion-derived spatial production expert over V118 execution layers ---")
    prefix = text[:start]
    suffix = f'''# --- V120: Top5 episode distillation selected route expert ---
_V120_PARENT_STATUS = model_status
_V120_DISTILLED_ROUTE = json.loads(zlib.decompress(base64.b85decode("{encoded}")).decode("utf-8"))
_V120_SOURCE = {json.dumps(metadata, ensure_ascii=False, sort_keys=True)}
__version__ = "v120-top5-distilled-gold-candidate-rc1"


def _v120_distilled_expert(obs, step):
    global _ACTIONS
    _ACTIONS = _V120_DISTILLED_ROUTE
    action = _V19_CORE(obs)
    action = _v76_adjacent_safe_buy_lead(obs, action)
    return _v118_reveal_liquidity(obs, action, step)


def model_status():
    status = _V120_PARENT_STATUS()
    status.update({{
        "kind": "v120_top5_distilled_gold_candidate",
        "model_id": "v120_hierarchical_top5_distillation",
        "distillation": copy.deepcopy(_V120_SOURCE),
        "serving_route_lookup": False,
        "future_information": False,
    }})
    return status


del agent
def agent(obs, configuration=None):
    del configuration
    step = int(_get(obs, "step", int(_get(obs, "day", 0) or 0) * 24 + int(_get(obs, "hour", 0) or 0)) or 0)
    return _v120_distilled_expert(obs, step)
'''
    output = prefix + suffix
    if re.search(r"episode-104547425", output):
        raise AssertionError("unexpected path dependency")
    (HERE / "main.py").write_text(output, encoding="utf-8")
    (HERE / "candidate_manifest.json").write_text(json.dumps({"schema": "kaggriculture-v120-gold-candidate-manifest-v1", **metadata, "standalone_main": True, "status": "READY_FOR_CONFIRMATION"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"main_bytes": len(output.encode("utf-8")), "route_id": ROUTE_ID}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
