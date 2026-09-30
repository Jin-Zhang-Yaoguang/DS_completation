"""Clone one timed sequence expert slot into independent destination slots."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile

from flax import serialization
import numpy as np

from model_sequence_action import HIDDEN, NUM_EXPERTS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-expert", type=int, required=True, choices=range(NUM_EXPERTS))
    parser.add_argument("--destination-expert", type=int, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    destinations = sorted(set(args.destination_expert))
    if any(value not in range(NUM_EXPERTS) for value in destinations):
        parser.error("destination expert outside model capacity")
    if args.source_expert in destinations:
        parser.error("source expert cannot also be a destination")

    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    params = payload["params"]
    for module in ("unit_expert_projection", "market_expert_projection"):
        for field in ("kernel", "bias"):
            value = np.asarray(params[module][field]).copy()
            source = slice(args.source_expert * HIDDEN, (args.source_expert + 1) * HIDDEN)
            for destination in destinations:
                target = slice(destination * HIDDEN, (destination + 1) * HIDDEN)
                if field == "kernel":
                    value[:, target] = value[:, source]
                else:
                    value[target] = value[source]
            params[module][field] = value
    result = {
        **payload,
        "params": params,
        "expert_clone": {
            "source": args.source_expert,
            "destinations": destinations,
            "source_checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(args.output)
    args.output.with_suffix(".json").write_text(
        json.dumps(result["expert_clone"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
