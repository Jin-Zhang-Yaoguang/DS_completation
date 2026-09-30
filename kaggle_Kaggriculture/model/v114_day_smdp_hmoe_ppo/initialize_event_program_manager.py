"""Initialize and serialize an independent random event-program Manager."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from flax import serialization
from flax.core import unfreeze
import jax
import jax.numpy as jnp

try:
    from .event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM
    from .model_event_program_ppo import EventProgramPPOManager, make_checkpoint_payload
except ImportError:  # Direct-file imports used by local runners.
    from event_program_features import FEATURE_SCHEMA, MANAGER_FEATURE_DIM  # type: ignore
    from model_event_program_ppo import (  # type: ignore
        EventProgramPPOManager,
        make_checkpoint_payload,
    )


HERE = Path(__file__).resolve().parent
SOURCE_FILES = (
    "event_program.py",
    "event_program_features.py",
    "model_event_program_ppo.py",
    "initialize_event_program_manager.py",
    "policy_random_event_program.py",
)


def source_hashes(root: Path = HERE) -> tuple[dict[str, str], str]:
    per_file: dict[str, str] = {}
    combined = hashlib.sha256()
    for name in SOURCE_FILES:
        path = root / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        per_file[name] = digest
        combined.update(name.encode("utf-8"))
        combined.update(b"\0")
        combined.update(bytes.fromhex(digest))
    return per_file, combined.hexdigest()


def initialize_payload(seed: int, *, policy_seed: int | None = None) -> dict[str, Any]:
    initialization_seed = int(seed)
    action_seed = initialization_seed if policy_seed is None else int(policy_seed)
    model = EventProgramPPOManager()
    variables = model.init(
        jax.random.PRNGKey(initialization_seed),
        jnp.zeros((1, MANAGER_FEATURE_DIM), dtype=jnp.float32),
    )
    file_hashes, combined_hash = source_hashes()
    payload = make_checkpoint_payload(unfreeze(variables["params"]))
    payload.update(
        {
            "input_dim": MANAGER_FEATURE_DIM,
            "feature_schema": FEATURE_SCHEMA,
            "initialization_seed": initialization_seed,
            "policy_seed": action_seed,
            "source_files_sha256": file_hashes,
            "source_sha256": combined_hash,
        }
    )
    return payload


def write_checkpoint(
    output: Path,
    *,
    seed: int,
    policy_seed: int | None = None,
) -> dict[str, Any]:
    payload = initialize_payload(seed, policy_seed=policy_seed)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = serialization.msgpack_serialize(payload)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as sink:
        sink.write(encoded)
        temporary = Path(sink.name)
    temporary.replace(output)
    return {
        "checkpoint": str(output),
        "checkpoint_sha256": hashlib.sha256(encoded).hexdigest(),
        "input_dim": payload["input_dim"],
        "initialization_seed": payload["initialization_seed"],
        "policy_seed": payload["policy_seed"],
        "strategy_parent": payload["strategy_parent"],
        "source_sha256": payload["source_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--policy-seed", type=int)
    args = parser.parse_args()
    report = write_checkpoint(args.output, seed=args.seed, policy_seed=args.policy_seed)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


__all__ = ["SOURCE_FILES", "initialize_payload", "source_hashes", "write_checkpoint"]
