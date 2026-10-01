# Fixed-Shop Synthetic Replay Arena

This directory contains an isolated scenario build of the Kaggriculture
1.32.7 C++ simulator.  It does not modify the existing cppsim source, headers,
or shared objects.

Despite the directory name, this arena does not read or embed real Replay
actions.  A scenario is only a synthetic sequence of shop names and the public
step from which each shop becomes visible.

## Build

Use the repository's CPython 3.12 environment because the existing simulator
extension is built for CPython 3.12:

```bash
.venv/bin/python3.12 \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/replay_arena/build_scenario.py
```

The build script reads the existing `python/kagsim.cpp`, verifies exact
mechanical anchors, emits `kagsim_scenario.cpp`, injects
`Game.force_shops(list)`, renames the module to `kagsim_scenario`, and compiles
only into `replay_arena/build/`.  `build_manifest.json` records upstream source
and `.so` hashes before and after the build.

## Run a scenario

```python
from scenario_runner import ScenarioRunner

schedule = [
    {"shop": "BAKERY", "visible_from_step": 72},
    {"shop": "PET_CAFE", "visible_from_step": 144},
]
arena = ScenarioRunner(seed, candidate_a, candidate_b, schedule)
result = arena.run()
```

Both agents are called live at every step and receive only their current seat
observation.  After the shared engine step completes, the runner replaces the
current shop list with the schedule prefix whose `visible_from_step` has been
reached.  Future schedule entries are never passed to agents.

An empty schedule performs no shop override at all and therefore retains exact
standard-engine behavior.

## Synthetic QA

```bash
.venv/bin/python3.12 \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/replay_arena/test_scenario.py
```

The test compares every observation and reward across the engine's complete
configured-720 horizon (719 executed transitions under existing 1.32.7 done
semantics), verifies fixed visibility and town demand at steps 72 and 144,
checks both seats, verifies engine version 1.32.7, and re-hashes every original
shared object.  It runs no gold battle and reads no real Replay.
