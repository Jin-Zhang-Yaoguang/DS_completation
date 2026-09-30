"""从第一名公开 Replay 提取可复现的规则路线资产。"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory

from kaggle.api.kaggle_api_extended import KaggleApi
from requests import HTTPError


ROOT = Path(__file__).resolve().parent
SUBMISSION_ID = 55540317
ROUTE_EPISODES = {
    "default": (94079899, 0),
    "early_yarn": (93783010, 0),
    "mid_yarn": (93816256, 1),
    "late_yarn": (93974374, 1),
    "novelty_fallback": (93481053, 1),
}


def _canonical(actions):
    return json.dumps(actions, ensure_ascii=False, separators=(",", ":"))


def _download_replay(api, episode_id, directory):
    path = Path(directory) / f"episode-{episode_id}-replay.json"
    if path.exists():
        return path
    for attempt in range(8):
        try:
            api.competition_episode_replay(episode_id, directory, quiet=True)
            return path
        except HTTPError as error:
            status = getattr(error.response, "status_code", None)
            if status != 429 or attempt == 7:
                raise
            wait_seconds = min(60, 10 * (attempt + 1))
            print(json.dumps({"episode": episode_id, "rate_limited": True, "wait_seconds": wait_seconds}), flush=True)
            time.sleep(wait_seconds)
    raise RuntimeError(episode_id)


def main():
    api = KaggleApi()
    api.authenticate()
    routes = {}
    manifest = {
        "schema": "kaggriculture-v4-public-route-1",
        "source_submission_id": SUBMISSION_ID,
        "routes": {},
    }
    with TemporaryDirectory(prefix="kaggriculture_v4_routes_") as directory:
        for name, (episode_id, seat) in ROUTE_EPISODES.items():
            path = _download_replay(api, episode_id, directory)
            replay = json.loads(path.read_text())
            actions = [row[seat]["action"] for row in replay["steps"][1:]]
            if len(actions) != 719:
                raise RuntimeError((name, episode_id, len(actions)))
            payload = _canonical(actions).encode("utf-8")
            routes[name] = base64.b85encode(zlib.compress(payload, 9)).decode("ascii")
            manifest["routes"][name] = {
                "episode_id": episode_id,
                "seat": seat,
                "decisions": len(actions),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }

    source = [
        '"""由 extract_routes.py 生成；仅包含公开 Replay 的动作序列。"""',
        "import base64",
        "import json",
        "import zlib",
        "",
        f"_ENCODED = {routes!r}",
        "ROUTES = {",
        "    name: json.loads(zlib.decompress(base64.b85decode(payload)).decode('utf-8'))",
        "    for name, payload in _ENCODED.items()",
        "}",
        "",
    ]
    (ROOT / "routes.py").write_text("\n".join(source))
    (ROOT / "route_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
