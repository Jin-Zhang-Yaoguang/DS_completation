"""Re-register a from-scratch shared-network BC run as a V114 expert checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from flax import serialization


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--training-seed", type=int, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--model-id", default="v114_day_smdp_hmoe_ppo_bc_init_v1")
    parser.add_argument("--architecture", default="v114-timed-autoregressive-product-experts-bc-init-v1")
    parser.add_argument("--evidence-parent", default="v113_stage35_closed_loop_teacher_data_only")
    parser.add_argument("--lineage-id")
    parser.add_argument("--teacher-family-evidence")
    args = parser.parse_args()
    payload = serialization.msgpack_restore(args.source.read_bytes())
    if payload.get("strategy_parent") is not None:
        raise ValueError("V114 BC source must have strategy_parent=null")
    dataset_sha = hashlib.sha256(args.dataset.read_bytes()).hexdigest()
    registered = dict(payload)
    registered.update({
        "model_id": args.model_id,
        "strategy_parent": None,
        "evidence_parent": args.evidence_parent,
        "architecture": args.architecture,
        "training_seed": int(args.training_seed),
        "dataset_sha256": dataset_sha,
        "inherits_v113_checkpoint": False,
        "online_historical_agent_fallback": False,
        "qualification_status": "BC_INIT_NOT_EXPERT_QUALIFIED_NOT_GOLD",
    })
    if args.lineage_id is not None:
        registered["lineage_id"] = args.lineage_id
    if args.teacher_family_evidence is not None:
        registered["teacher_family_evidence"] = args.teacher_family_evidence
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(registered))
        temporary = Path(sink.name)
    temporary.replace(args.output)
    checkpoint_sha = hashlib.sha256(args.output.read_bytes()).hexdigest()
    report = {
        "schema": "kaggriculture-v114-bc-registration-v1",
        "model_id": registered["model_id"],
        "strategy_parent": None,
        "source_checkpoint": str(args.source),
        "checkpoint": str(args.output),
        "checkpoint_sha256": checkpoint_sha,
        "dataset": str(args.dataset),
        "dataset_sha256": dataset_sha,
        "training_seed": args.training_seed,
        "lineage_id": registered.get("lineage_id"),
        "teacher_family_evidence": registered.get("teacher_family_evidence"),
        "inherits_v113_checkpoint": False,
        "qualification_status": registered["qualification_status"],
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
