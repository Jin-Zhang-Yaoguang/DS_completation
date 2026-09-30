# V14-QS1 Kaggle package

This package combines the complete S1 parent with the stateful opponent-shadow
queue best response. The deterministic build freezes S1, the queue solver, A2,
the learned Router, all complete experts, and the exact official transition
implementation. The final archive has no source-tree or absolute-path runtime
dependency.

Only the already-exposed QA seeds `93451031..93451033` may be used here. The
formal screen and confirm panels remain sealed outside this package.

Development comparison added no wins over the queue-only candidate. This
directory is retained as a rejected, provisional engineering template; it is
not part of the finalist slate and must not receive full package QA.

```bash
.venv/bin/python -m kaggle_Kaggriculture.model.v14_queue_s1.build_submission
.venv/bin/python -m kaggle_Kaggriculture.model.v14_queue_s1.package_qa
```
