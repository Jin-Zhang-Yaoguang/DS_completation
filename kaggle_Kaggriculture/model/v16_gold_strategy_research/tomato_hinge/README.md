# TOMATO hinge production-gap verdict

## Decision

**REJECT as the current gold-gap direction.** The 1.32.7 TOMATO hinge is real,
but current top routes are not leaving a robustly harvestable TOMATO premium.
No complete TOMATO expert/router was promoted.

This is not an A2 comparison. The screen starts from 18 current top-team
replay routes and asks whether replacing part of their complete STRAWBERRY
production lifecycle improves absolute reward and head-to-head margin under the
official interpreter.

## Evidence

- All 18 replay identities reproduce their recorded terminal rewards exactly.
- The 18 routes produce zero TOMATO. Their final public town layouts contain
  0--3 `PIZZA_SHOP/FARMERS_MARKET` instances.
- TOMATO really crosses its hinge knee in four routes: public inventory falls
  below `I0-T = 9800`; the most extreme route reaches inventory 9592 and price
  317.
- Nevertheless, full STRAWBERRY-to-TOMATO substitution reduces own reward and
  margin in 18/18 routes, with 8 W-to-L and 0 L-to-W.
- A better isolated treatment replaces exactly 1/2/4/8 evenly distributed
  STRAWBERRY plant slots and matching seed units, retains every original
  STRAWBERRY sale, and adds TOMATO liquidation only in free market slots.
- In the actionable `tomato_shops >= 2` regime, mean margin deltas for 1/2/4/8
  tiles are respectively -2820.0, -2340.6, -6195.6, and -10890.0. No capacity
  has an L-to-W conversion.
- In the four routes already below the hinge knee, the smallest one-tile block
  has margin deltas negative in 4/4, mean -3894.0, own-reward mean -15858.25,
  and one W-to-L.

The economic failure is strategic rather than merely a lack of TOMATO demand:
TOMATO is an ongoing daily producer, so even a tiny block quickly supplies the
scarcity that created the premium, while sacrificing a proven STRAWBERRY slot
and changing the shared market faced by both players. The premium is not a
stable private alpha source.

## Why live evaluation was not run

The task's promotion rule was conditional: build a complete live expert only
if an obvious positive public-shop regime exists. None exists. Selecting the
few individually positive replay/capacity cells would be precisely the
replay-overfitting failure mode the gold strategy must avoid.

This rejects the tested production substitution, not every possible TOMATO
use. A jointly optimized route found independently by route search could still
be tested as a new hypothesis.

## Reproduce

From the repository root, using the competition virtual environment:

```bash
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/tomato_hinge/open_loop_screen.py
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/tomato_hinge/isolated_capacity_screen.py
```

Artifacts:

- `open_loop_screen.json`: 25%/50%/100% broad lifecycle screen.
- `isolated_capacity_screen.json`: 1/2/4/8-tile isolated-capacity screen.
- `decision.json`: frozen promotion decision and headline metrics.

Both scripts use `production_gap/replay_audit.py`, which wraps the installed
official interpreter only for instrumentation; game rules and outcomes remain
official-engine 1.32.7.
