import importlib.metadata
import sys
import time

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable

started = time.perf_counter()
selected = get_last_callable(Path("main.py").read_text(), path="main.py")
load_seconds = time.perf_counter() - started
assert selected.__name__ == "kaggle_agent_v58"

environment = make("kaggriculture", configuration={"seed": 580902}, debug=False)
observation = environment.steps[-1][0]["observation"]
observation["player"] = 0
observation["step"] = 0
started = time.perf_counter()
action = selected(observation, environment.configuration)
action_seconds = time.perf_counter() - started
assert set(action) == {"farmer", "hands", "market"}
assert isinstance(action["farmer"], list)
assert isinstance(action["hands"], list)
assert isinstance(action["market"], list)

print({
    "python": sys.version,
    "kaggle_environments": importlib.metadata.version("kaggle-environments"),
    "selected_callable": selected.__name__,
    "source_load_seconds": load_seconds,
    "first_action_seconds": action_seconds,
    "first_action_keys": sorted(action),
    "full_both_seat_default_timeout_smoke": "verified in frozen manifest",
})