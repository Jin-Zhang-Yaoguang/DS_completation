"""用官方 ARC-AGI SDK 在本地公开环境运行策略。"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from arc_agi import Arcade, OperationMode

from adaptive_agent import play_game


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environments-dir", required=True)
    parser.add_argument("--games", default="", help="逗号分隔的 game_id；默认全部本地游戏")
    parser.add_argument("--max-actions", type=int, default=240)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=args.environments_dir)
    available = {entry.game_id for entry in arc.get_environments()}
    requested = [part.strip() for part in args.games.split(",") if part.strip()] or sorted(available)
    missing = sorted(set(requested) - available)
    if missing:
        raise SystemExit(f"本地缺少游戏: {missing}")
    scorecard_id = arc.open_scorecard(tags=["adaptive_exploration_v1", "offline"])
    results = []
    try:
        for game_id in requested:
            env = arc.make(game_id, scorecard_id=scorecard_id)
            if env is None:
                raise RuntimeError(f"无法创建游戏 {game_id}")
            result = play_game(env, game_id, args.max_actions)
            results.append(result)
            print(f"{game_id}: 关卡 {result['levels_completed']}，动作 {result['actions']}，状态 {result['state']}")
    finally:
        card = arc.close_scorecard(scorecard_id)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment_dir": str(Path(args.environments_dir).resolve()),
        "max_actions_per_game": args.max_actions,
        "games": results,
        "scorecard": card.model_dump(mode="json") if card else None,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
