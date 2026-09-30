"""Synthetic interface fixture for ablation planner tests; never a game candidate."""

P0064_HASH = "3f0eb3eec980aa0100dab9bc3a001d022b9b354770e9944fec4568ccb8ff0766"
ALLOWED_MODES = {
    "base", "target_only", "market_only", "full",
    "fixed_collision", "fixed_scarcity", "fixed_liquidator",
}


def canonical_hash(params):
    del params
    return P0064_HASH


class SyntheticExecutor:
    def __init__(self, mode):
        self.mode = mode

    def act(self, observation):
        hands = len(observation.get("hands", [])) if isinstance(observation, dict) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in range(hands)], "market": []}

    def diagnostics(self):
        return {
            "expert": "synthetic",
            "target_path_id": self.mode,
            "market_path_id": self.mode,
        }


def build_executor(params, mode):
    del params
    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported synthetic mode: {mode}")
    return SyntheticExecutor(mode)

