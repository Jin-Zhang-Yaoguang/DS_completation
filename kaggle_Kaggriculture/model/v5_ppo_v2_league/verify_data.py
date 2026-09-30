"""Verify compact BC shards and their reproducibility manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import main


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    episodes = 0
    all_seeds = []
    seats = np.zeros(2, dtype=np.int64)
    routes = np.zeros(2, dtype=np.int64)
    for shard in manifest["shards"]:
        path = directory / shard["file"]
        assert _sha256(path) == shard["sha256"], path
        data = np.load(path, allow_pickle=False)
        count = len(data["features"])
        assert data["features"].shape == (count, 30, main.FEATURE_DIM)
        assert data["actions"].shape == (count, 30, len(main.HEAD_SIZES))
        assert data["route_mask"].shape == (count, 30)
        assert np.all(np.sum(data["route_mask"], axis=1) == 1)
        assert np.isfinite(data["features"]).all() and np.isfinite(data["potentials"]).all()
        for head, size in enumerate(main.HEAD_SIZES):
            assert np.all((data["actions"][..., head] >= 0) & (data["actions"][..., head] < size))
        episodes += count
        all_seeds.extend(data["seeds"].tolist())
        seats += np.bincount(data["seats"], minlength=2)
        routes += np.bincount(data["actions"][:, 7, 0], minlength=2)
    assert episodes == manifest["episodes"]
    assert len(set(all_seeds)) == episodes
    assert tuple(seats) == (episodes // 2, episodes // 2)
    source_hashes = manifest.get("source_sha256", {})
    return {
        "ok": True, "episodes": episodes, "shards": len(manifest["shards"]),
        "seats": seats.tolist(), "routes": routes.tolist(),
        "compressed_bytes": sum((directory / shard["file"]).stat().st_size for shard in manifest["shards"]),
        "source_sha256": source_hashes,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parent / "data" / "bc")
    print(json.dumps(verify(parser.parse_args().data), ensure_ascii=False, indent=2))
