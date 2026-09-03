"""Local human-vs-bot web playground for Kaggriculture."""

from __future__ import annotations

import importlib.util
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request
from kaggle_environments import make


ROOT = Path(__file__).resolve().parents[1]
BOT_PATH = ROOT / "model" / "v1_adaptive_market" / "main.py"

UNIT_SIMPLE = {
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    "PASS",
    "DROP",
    "WATER",
    "HARVEST",
    "FERTILIZE",
    "BUILD_COOP",
    "BUILD_PASTURE",
    "DIG",
    "FEED",
    "COLLECT_FERTILIZER",
    "CARE",
}
UNIT_ITEM = {"PLANT", "PICKUP", "PLACE"}
MARKET_SIMPLE = {"HIRE", "BUY_LAND"}
MARKET_ITEM = {"BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def _plain(value: Any) -> Any:
    """Convert Struct/dicts from kaggle-environments into JSON-safe values."""

    return json.loads(json.dumps(value))


def _get(value: Any, key: str, default: Any = None) -> Any:
    """Read both dicts and Kaggle Structs, including falsey values such as step 0."""

    getter = getattr(value, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(value, key, default)


def _positive_int(value: Any, default: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(0, min(parsed, 100_000))


def _normalize_unit(raw: Any) -> list[Any]:
    if not isinstance(raw, list) or not raw:
        return ["PASS"]
    op = str(raw[0]).upper()
    if op in UNIT_SIMPLE:
        return [op]
    if op not in UNIT_ITEM or len(raw) < 2 or not str(raw[1]):
        raise ValueError(f"Invalid unit action: {raw!r}")
    item = str(raw[1]).upper()
    if op == "PLANT":
        return [op, item]
    quantity = _positive_int(raw[2] if len(raw) >= 3 else 1)
    return [op, item, quantity]


def _normalize_market(raw: Any) -> list[Any]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"Invalid market order: {raw!r}")
    op = str(raw[0]).upper()
    if op in MARKET_SIMPLE:
        return [op]
    if op not in MARKET_ITEM or len(raw) < 3 or not str(raw[1]):
        raise ValueError(f"Invalid market order: {raw!r}")
    return [op, str(raw[1]).upper(), _positive_int(raw[2])]


def _pass_action(obs: Any) -> dict[str, Any]:
    player = int(_get(obs, "player", 0) or 0)
    farms = list(_get(obs, "farms", []) or [])
    hands = list(_get(farms[player], "hands", []) or [])
    return {
        "farmer": ["PASS"],
        "hands": [["PASS"] for _ in hands],
        "market": [],
    }


def _normalize_human_action(payload: Any, obs: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Action payload must be an object")
    action = {
        "farmer": _normalize_unit(payload.get("farmer", ["PASS"])),
        "hands": [],
        "market": [],
    }
    player = int(_get(obs, "player", 0) or 0)
    farms = list(_get(obs, "farms", []) or [])
    expected_hands = len(_get(farms[player], "hands", []) or [])
    raw_hands = payload.get("hands", [])
    if not isinstance(raw_hands, list):
        raise ValueError("hands must be a list")
    for index in range(expected_hands):
        raw = raw_hands[index] if index < len(raw_hands) else ["PASS"]
        action["hands"].append(_normalize_unit(raw))
    raw_market = payload.get("market", [])
    if not isinstance(raw_market, list):
        raise ValueError("market must be a list")
    action["market"] = [_normalize_market(order) for order in raw_market[:10]]
    return action


class GameSession:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.env = None
        self.bot = None
        self.human_player = 0
        self.bot_player = 1
        self.seed = 0
        self.days = 30
        self.history: list[dict[str, Any]] = []
        self.last_actions: dict[str, Any] = {"human": None, "bot": None}
        self.new_game(seed=0, days=30, human_player=0)

    def _load_bot(self) -> Any:
        module_name = f"kaggriculture_v1_play_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, BOT_PATH)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load bot: {BOT_PATH}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def new_game(self, seed: int, days: int, human_player: int) -> dict[str, Any]:
        with self.lock:
            self.seed = int(seed)
            self.days = max(1, min(int(days), 30))
            self.human_player = 1 if int(human_player) == 1 else 0
            self.bot_player = 1 - self.human_player
            self.bot = self._load_bot()
            self.env = make(
                "kaggriculture",
                configuration={"episodeSteps": self.days * 24, "seed": self.seed},
                debug=False,
            )
            self.history = []
            self.last_actions = {"human": None, "bot": None}
            return self.snapshot()

    def _obs(self, player: int) -> Any:
        # Environment.state stores shared fields (notably ``step``) only on
        # player 0.  AgentRunner normally rehydrates them immediately before
        # calling each agent.  Manual env.step callers must do the same so a
        # player-1 human or bot sees exactly the normal runtime observation.
        return self.env._Environment__get_shared_state(player).observation

    def _record_turn(
        self,
        before: list[float],
        human_action: dict[str, Any],
        bot_action: dict[str, Any],
    ) -> None:
        after_obs = self._obs(self.human_player)
        after = [float(_get(farm, "money", 0) or 0) for farm in (_get(after_obs, "farms", []) or [])]
        self.history.append(
            {
                "step": int(_get(after_obs, "step", 0) or 0),
                "day": int(_get(after_obs, "day", 0) or 0),
                "hour": int(_get(after_obs, "hour", 0) or 0),
                "humanMoneyDelta": round(after[self.human_player] - before[self.human_player], 2),
                "botMoneyDelta": round(after[self.bot_player] - before[self.bot_player], 2),
                "human": _plain(human_action),
                "bot": _plain(bot_action),
            }
        )
        self.history = self.history[-80:]

    def step(self, payload: Any) -> dict[str, Any]:
        with self.lock:
            if self.env.done:
                raise ValueError("Game is already over; start a new game")
            human_obs = self._obs(self.human_player)
            bot_obs = self._obs(self.bot_player)
            human_action = _normalize_human_action(payload, human_obs)
            bot_action = self.bot.agent(bot_obs)
            before = [float(_get(farm, "money", 0) or 0) for farm in (_get(human_obs, "farms", []) or [])]
            actions = [None, None]
            actions[self.human_player] = human_action
            actions[self.bot_player] = bot_action
            self.env.step(actions)
            self.last_actions = {
                "human": _plain(human_action),
                "bot": _plain(bot_action),
            }
            self._record_turn(before, human_action, bot_action)
            return self.snapshot()

    def fast_forward(self, turns: int) -> dict[str, Any]:
        turns = max(1, min(int(turns), 24))
        for _ in range(turns):
            if self.env.done:
                break
            self.step(_pass_action(self._obs(self.human_player)))
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            obs = self._obs(self.human_player)
            farms = _plain(_get(obs, "farms", []))
            statuses = [str(state.status) for state in self.env.state]
            rewards = [state.reward for state in self.env.state]
            result = None
            if self.env.done:
                human_money = float(farms[self.human_player].get("money", 0) or 0)
                bot_money = float(farms[self.bot_player].get("money", 0) or 0)
                result = "win" if human_money > bot_money else "loss" if human_money < bot_money else "tie"
            return {
                "game": {
                    "done": bool(self.env.done),
                    "step": int(_get(obs, "step", 0) or 0),
                    "day": int(_get(obs, "day", 0) or 0),
                    "hour": int(_get(obs, "hour", 0) or 0),
                    "days": self.days,
                    "episodeSteps": self.days * 24,
                    "seed": self.seed,
                    "humanPlayer": self.human_player,
                    "botPlayer": self.bot_player,
                    "statuses": statuses,
                    "rewards": rewards,
                    "result": result,
                },
                "farms": farms,
                "private": _plain(_get(obs, "private", {})),
                "market": _plain(_get(obs, "market", {})),
                "town": _plain(_get(obs, "town", {})),
                "lastActions": self.last_actions,
                "history": self.history[-12:],
                "bot": {
                    "name": "v1 adaptive market",
                    "version": str(getattr(self.bot, "__version__", "unknown")),
                    "path": str(BOT_PATH.relative_to(ROOT)),
                },
            }


app = Flask(__name__)
session = GameSession()


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/state")
def state():
    return jsonify(session.snapshot())


@app.post("/api/new")
def new_game():
    payload = request.get_json(silent=True) or {}
    try:
        seed = int(payload.get("seed", 0))
        days = int(payload.get("days", 30))
        human_player = int(payload.get("humanPlayer", 0))
        return jsonify(session.new_game(seed, days, human_player))
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/step")
def step():
    try:
        return jsonify(session.step(request.get_json(silent=True) or {}))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/fast-forward")
def fast_forward():
    payload = request.get_json(silent=True) or {}
    try:
        return jsonify(session.fast_forward(int(payload.get("turns", 1))))
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("KAGGRICULTURE_PLAY_PORT", "8765"))
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
