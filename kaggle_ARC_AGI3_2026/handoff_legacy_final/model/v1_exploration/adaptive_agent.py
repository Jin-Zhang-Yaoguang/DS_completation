"""ARC-AGI-3 的通用反馈驱动探索基线。

只使用当前帧、合法动作和本局历史；不读取游戏源码或隐藏关卡。
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np


def _grid(observation: Any) -> np.ndarray:
    frames = getattr(observation, "frame", None)
    if frames is None or len(frames) == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    array = np.asarray(frames[-1], dtype=np.uint8)
    if array.ndim != 2:
        return np.zeros((1, 1), dtype=np.uint8)
    return array


def _fingerprint(grid: np.ndarray) -> str:
    digest = hashlib.blake2b(digest_size=12)
    digest.update(bytes(grid.shape))
    digest.update(grid.tobytes())
    return digest.hexdigest()


def _click_candidates(grid: np.ndarray, previous: np.ndarray | None) -> list[tuple[int, int]]:
    """先试变化区域，再试稀有色块和网格中心，坐标始终在画面内。"""
    height, width = grid.shape
    points: list[tuple[int, int]] = []
    if previous is not None and previous.shape == grid.shape:
        ys, xs = np.nonzero(grid != previous)
        if len(xs):
            points.append((int(np.median(xs)), int(np.median(ys))))

    colors, counts = np.unique(grid, return_counts=True)
    for color in colors[np.argsort(counts)[: min(6, len(colors))]]:
        ys, xs = np.nonzero(grid == color)
        if len(xs):
            points.append((int(np.median(xs)), int(np.median(ys))))
    points.extend([(width // 2, height // 2), (width // 4, height // 4),
                   (3 * width // 4, 3 * height // 4)])
    return list(dict.fromkeys((min(x, width - 1), min(y, height - 1)) for x, y in points))


@dataclass(frozen=True)
class Decision:
    action: Any
    data: dict[str, int]
    reason: str


class AdaptiveExplorer:
    """按状态访问数和观察反馈选动作，并对无效动作降权。"""

    def __init__(self, game_id: str, max_actions: int = 240) -> None:
        self.game_id = game_id
        self.max_actions = max_actions
        self.steps = 0
        self.state_visits: Counter[str] = Counter()
        self.action_visits: Counter[tuple[str, str, int, int]] = Counter()
        self.global_trials: Counter[str] = Counter()
        self.global_gain: defaultdict[str, float] = defaultdict(float)
        self.previous_grid: np.ndarray | None = None
        self.pending: tuple[str, str, int, int] | None = None
        self.pending_levels = 0
        self.last_action: str | None = None
        self.streak = 0
        self.resets = 0

    def observe(self, observation: Any) -> None:
        grid = _grid(observation)
        key = _fingerprint(grid)
        prior_visits = self.state_visits[key]
        if self.pending is not None:
            state_key, action_name, _, _ = self.pending
            changed = key != state_key
            levels = int(getattr(observation, "levels_completed", 0) or 0)
            progress = max(0, levels - self.pending_levels)
            gain = (2.0 if changed else -0.6) + (1.0 / (1 + prior_visits) if changed else 0) + 20.0 * progress
            self.global_trials[action_name] += 1
            self.global_gain[action_name] += gain
            self.pending = None
        self.state_visits[key] += 1

    def choose(self, observation: Any, actions: list[Any]) -> Decision:
        grid = _grid(observation)
        key = _fingerprint(grid)
        levels = int(getattr(observation, "levels_completed", 0) or 0)
        candidates: list[tuple[float, str, int, int, Any]] = []
        for action in actions:
            name = action.name
            if name == "RESET":
                continue
            positions = _click_candidates(grid, self.previous_grid) if name == "ACTION6" else [(-1, -1)]
            for x, y in positions:
                visits = self.action_visits[(key, name, x, y)]
                mean_gain = self.global_gain[name] / max(1, self.global_trials[name])
                novelty = 1.8 / math.sqrt(1 + visits)
                probe = 1.2 if self.global_trials[name] == 0 else 0.0
                momentum = 0.45 if name == self.last_action and self.streak < 3 else 0.0
                # 稳定打破并列；避免 Python hash 随进程变化。
                tie = int(hashlib.blake2b(f"{self.game_id}:{key}:{name}:{x}:{y}".encode(), digest_size=2).hexdigest(), 16) / 65535 * 0.01
                score = mean_gain + novelty + probe + momentum + tie - 0.25 * visits
                candidates.append((score, name, x, y, action))
        if not candidates:
            raise RuntimeError(f"{self.game_id}: 当前帧没有可用的非 RESET 动作")
        _, name, x, y, action = max(candidates, key=lambda item: item[0])
        self.action_visits[(key, name, x, y)] += 1
        self.pending = (key, name, x, y)
        self.pending_levels = levels
        self.previous_grid = grid.copy()
        self.streak = self.streak + 1 if name == self.last_action else 1
        self.last_action = name
        self.steps += 1
        data = {"x": x, "y": y} if name == "ACTION6" else {}
        return Decision(action=action, data=data, reason=f"反馈探索: 状态访问{self.state_visits[key]}次，动作{name}局部尝试{self.action_visits[(key, name, x, y)]}次")


def play_game(env: Any, game_id: str, max_actions: int = 240) -> dict[str, Any]:
    """运行一局并返回动作数、完成关卡；env 遵循 ARC-AGI SDK 协议。"""
    policy = AdaptiveExplorer(game_id, max_actions)
    observation = env.observation_space
    if observation is None:
        observation = env.reset()
    if observation is None:
        raise RuntimeError(f"{game_id}: RESET 未返回观测")
    policy.observe(observation)
    history: list[dict[str, Any]] = []
    while policy.steps < max_actions:
        state = getattr(observation, "state", None)
        state_name = getattr(state, "name", str(state))
        if state_name == "WIN":
            break
        if state_name in {"GAME_OVER", "NOT_PLAYED"}:
            if policy.resets >= 2:
                break
            observation = env.reset()
            policy.resets += 1
            if observation is None:
                break
            policy.observe(observation)
            continue
        decision = policy.choose(observation, list(env.action_space))
        next_observation = env.step(decision.action, data=decision.data,
                                    reasoning={"policy": "adaptive_exploration_v1", "reason": decision.reason})
        if next_observation is None:
            raise RuntimeError(f"{game_id}: 第 {policy.steps} 步动作 {decision.action.name} 未返回观测")
        policy.observe(next_observation)
        observation = next_observation
        history.append({"step": policy.steps, "action": decision.action.name,
                        "data": decision.data, "levels_completed": int(getattr(observation, "levels_completed", 0) or 0),
                        "state": getattr(getattr(observation, "state", None), "name", "UNKNOWN")})
    return {"game_id": game_id, "actions": policy.steps, "resets": policy.resets,
            "levels_completed": int(getattr(observation, "levels_completed", 0) or 0),
            "state": getattr(getattr(observation, "state", None), "name", "UNKNOWN"),
            "history": history}
