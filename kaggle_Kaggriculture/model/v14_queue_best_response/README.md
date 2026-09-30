# V14-Q2 Kaggle package

The only candidate is `v14_queue_stateful_no_mirror`. `main.py` reproduces the
frozen Q2b wrapper directly: it removes full public-production equality but
retains `clone_distance <= 4`. The build freezes the queue core, A2,
the learned Router, all complete experts, and the official Kaggriculture
transition implementation into one deterministic archive. The serving entry
is the last callable named `agent` and has no source-tree location dependency.

Only the already-exposed QA seeds `93451031..93451033` may be used by
`package_qa.py`. Formal screen/confirm panels are owned by the separate sealed
validation protocol and are never read here.

```bash
.venv/bin/python -m kaggle_Kaggriculture.model.v14_queue_best_response.build_submission
.venv/bin/python -m kaggle_Kaggriculture.model.v14_queue_best_response.package_qa
```
