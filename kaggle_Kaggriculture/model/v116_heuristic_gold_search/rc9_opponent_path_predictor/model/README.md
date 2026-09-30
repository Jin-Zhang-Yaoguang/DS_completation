# V116 RC9 Opponent Path Predictor

RC9 freezes RC8 configuration `p0064_3f0eb3eec9` and adds a depth-2,
public-state-only Shop + Opponent Path Router.  It is a mechanism candidate,
not a gold or advancement result; no battle evaluation is included here.

## Information contract

- The first shop is latched from the actual observation.  It is explicitly not
  treated as an exogenous seed label.
- At the beginning of `act(obs_t)`, market residuals use the previous public
  step and shops: `rival = (I_t - I_{t-1}) + D_{t-1}`.
- If our previous market batch touched a product with `SELL` or `BUY_PRODUCT`,
  that product's next residual is marked contaminated and is not used for an
  irreversible target change or a strong market trigger.
- State survives day boundaries.  Only a non-contiguous step resets market
  history.
- No Replay action stream, future state, opponent private state, per-step
  coordinate route, or parent agent is used.

## Router

The tree has three leaves and maximum depth two:

1. collision evidence -> `collision`;
2. otherwise current first-shop scarcity -> `scarcity`;
3. otherwise neutral/late broad liquidation -> `liquidator`.

Production overlays commit only at day 5 and day 9 and only affect future
aggregate goals.  Market overlays never remove sales from a batch containing a
same-turn purchase, and never alter the base terminal liquidation at step 708.

## Interface

```python
executor = build_executor(DEFAULT_PARAMS, "full")
action = executor.act(obs)
state = executor.diagnostics()
```

Modes:

- `base`
- `router_log_only`
- `target_only`
- `market_only`
- `full`
- `fixed_collision`
- `fixed_scarcity`
- `fixed_liquidator`

`base` and `router_log_only` execute the unchanged p0064 policy; the latter
also records path diagnostics.

## Build and mechanism QA

```bash
python packager.py
python test_rc9.py
```

`packager.py` appends the maintainable `overlay.py` to the audited RC8 source
and emits the self-contained Kaggle artifact `main.py`.  Tests cover mechanism
semantics, compile all source/artifacts, and make one engine call per mode.
They do not run matches.
