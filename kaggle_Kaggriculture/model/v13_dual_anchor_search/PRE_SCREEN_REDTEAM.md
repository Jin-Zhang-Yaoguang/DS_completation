# V13 pre-screen red-team verdict

Verdict: **GO** for the sealed screen only. No screen or confirmatory game was run during this audit.

## Frozen chain

- Final protocol seal SHA256: `010e63413f67a90203c0b153ce46fe79d3a0be7d880ec19bd9ce9300cee63613`.
- `freeze_protocol.py --verify`: every sealed asset, exposure, panel, candidate-order, and clean-registry check passed.
- Candidate slate is exactly A/C/D in this order:
  - `v13a_a2_no_wool_throttle`, archive `c86eabf219fdd1fa23327049cb027747e77407a604d067516fa7e35c73420928`.
  - `v13c_a2_v8_no_wool_throttle`, archive `ef279bbc937c73027ce17293aba19eeaa419563d2093880487ec9849400af0c1`.
  - `v13d_a2_public_winrisk_gate`, archive `4811794cef4bdd0210bc67bf01e95c9f4530c339f26056ebeb26121ee3197edd`.
- Anchors are exactly `v12_incumbent_r002` and `v12a2_no_shop_gate`.
- All five archives independently matched their submission manifests member-for-member. The clean registry fingerprint is `9d8a332350ccd9edef2d9cffd1b080ad59ed3bb97051b1feb456a0eb22bec28d`.
- All five registry entries point to safely extracted archive bytes, bind the complete serving closure, and use the raw Kaggle last callable `agent` rather than repository imports or `make_agent`.

## Adversarial checks

- 23 protocol/candidate unit and raw-loader tests passed.
- All three candidates passed dry-run construction with exactly 144 scheduled games and distinct sealed run fingerprints; no games JSONL was created.
- An out-of-slate candidate was rejected before task construction.
- A 144-row forged fixture used the correct sealed panel, exact run fingerprint, and exact task IDs, but lied about schema, engine, closed-loop/trace status, seat models, and reward-derived fields. Both resume validation and the final auditor rejected it at row 1.
- A second 144-row fixture with otherwise consistent semantics but a foreign task ID was rejected by both resume validation and the final auditor.
- A non-dry confirmatory attempt without a finalist seal failed before lock creation or game execution.
- Final filesystem/process check found no V13 execution-state lock, games JSONL, run audit, finalist seal, confirmatory lock, or active evaluator process.

## Threat boundary

The seal protects against drift, accidental reuse, foreign rows, malformed semantics, extra candidates, path changes, and repeat execution through the official runner. It does not claim protection against a privileged local operator deliberately rewriting artifacts and creating a new seal; that actor is outside the experiment-integrity threat model.
