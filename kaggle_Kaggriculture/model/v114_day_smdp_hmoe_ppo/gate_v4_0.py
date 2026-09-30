"""Run V114 V4-0 engine parity and action-closure gates via audited shared adapters."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "v113_simulator_hmoe_ppo"
if str(V113) not in sys.path:
    sys.path.insert(0, str(V113))

import audit_codec as shared_codec  # noqa: E402
import engine_parity as shared_engine  # noqa: E402


_SHARED_MARKET_TOKEN = shared_codec.space.market_token


def _v114_market_token(order):
    """Official 1.32.7 emits market PASS; it is the STOP/no-order token."""
    if isinstance(order, (list, tuple)) and order and str(order[0]) == "PASS":
        return shared_codec.space.MARKET_INDEX["STOP"], 0, True
    return _SHARED_MARKET_TOKEN(order)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def run(episodes_root: Path, output_dir: Path, parity_samples: int, codec_samples: int, workers: int) -> dict:
    rows = shared_engine.discover(episodes_root, "1.32.7")
    parity = shared_engine.run(episodes_root, "1.32.7", parity_samples, workers, 114001)
    parity.update({
        "schema": "kaggriculture-v114-engine-parity-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "shared_adapter_source": "v113_simulator_hmoe_ppo/engine_parity.py",
    })
    selected = shared_engine.select_samples(rows, codec_samples, 114002)
    shared_codec.space.market_token = _v114_market_token
    codec = shared_codec.audit([Path(row["path"]) for row in selected])
    codec.update({
        "schema": "kaggriculture-v114-codec-audit-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "shared_adapter_source": "v113_simulator_hmoe_ppo/action_space.py",
        "v114_codec_extension": "market PASS is canonical STOP/no-order",
    })
    _atomic_json(output_dir / "engine_parity.json", parity)
    _atomic_json(output_dir / "action_closure.json", codec)
    report = {
        "schema": "kaggriculture-v114-v4-0-gate-v1",
        "model_id": "v114_day_smdp_hmoe_ppo",
        "parity_samples": parity_samples,
        "codec_samples": codec_samples,
        "engine_parity_passed": bool(parity["gate_passed"]),
        "action_closure_passed": bool(codec["gate_passed"]),
        "gate_passed": bool(parity["gate_passed"] and codec["gate_passed"]),
    }
    _atomic_json(output_dir / "v4_0_gate.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--parity-samples", type=int, default=100)
    parser.add_argument("--codec-samples", type=int, default=16)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    report = run(args.episodes_root, args.output_dir, args.parity_samples, args.codec_samples, args.workers)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
