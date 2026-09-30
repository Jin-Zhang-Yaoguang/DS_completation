#!/usr/bin/env python3
"""Clone different unit and market source experts into one coordinated slot."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from flax import serialization
import numpy as np

from model_sequence_action import HIDDEN, NUM_EXPERTS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--source-unit-expert", type=int, required=True)
    parser.add_argument("--source-market-expert", type=int, required=True)
    parser.add_argument("--destination-expert", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for value in (args.source_unit_expert, args.source_market_expert, args.destination_expert):
        if value not in range(NUM_EXPERTS):
            parser.error(f"expert index must be in [0,{NUM_EXPERTS})")
    payload = serialization.msgpack_restore(args.checkpoint.read_bytes())
    params = payload["params"]
    for module, source in (
        ("unit_expert_projection", args.source_unit_expert),
        ("market_expert_projection", args.source_market_expert),
    ):
        for field in ("kernel", "bias"):
            value = np.asarray(params[module][field]).copy()
            source_slice = slice(source * HIDDEN, (source + 1) * HIDDEN)
            destination_slice = slice(
                args.destination_expert * HIDDEN,
                (args.destination_expert + 1) * HIDDEN,
            )
            value[..., destination_slice] = value[..., source_slice]
            params[module][field] = value
    result = {**payload, "params": params}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as sink:
        sink.write(serialization.msgpack_serialize(result))
        temporary = Path(sink.name)
    temporary.replace(args.output)


if __name__ == "__main__":
    main()
