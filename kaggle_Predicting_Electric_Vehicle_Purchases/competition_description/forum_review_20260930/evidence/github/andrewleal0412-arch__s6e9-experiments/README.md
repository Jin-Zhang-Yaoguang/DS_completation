# s6e9-experiments

Kaggle Playground Series S6E9 (Predicting EV Purchases, binary, ROC-AUC, 668,665 rows).

**Final: LB 0.94644, rank 31 of 1,484** (as of 2026-09-10; the competition closes Sep 30 and 37 teams are tied at this score, so the rank moves). First place is 0.94672, so the whole field is packed into 0.0003.

The interesting part of this competition was not the score. It was that **four separate changes improved my cross-validation and none of them improved the leaderboard**, and working out why taught me more than the ranking did.

## The transfer scoreboard

| Change | OOF gain | What the LB did | Cause |
|---|---:|---|---|
| Neighbour slope/curvature features | +0.00019 | flat | target leak |
| Income x column cross-TEs | +0.00016 | flat | target leak |
| 4-way public blend | +0.000137 | -0.00004 | overfit blend weights |
| 8-seed bagging | +0.00023 | -0.00003 | measurement point shifted |

The first three were caught after submitting. The fourth was **predicted in advance**, with a stated mechanism and a numeric range, before the submission was made. It landed inside the range. That is the result I would actually put my name on.

## The leak that a seed check cannot catch

Both leaks came from the same thing: target encoding fit with a **global out-of-fold scheme**. Each individual row's encoding is leak-free, so the code looks correct. But the training rows in any given fold carry encodings built from sets that include that fold's validation rows, so a little target signal crosses the boundary.

The trap is that **this reproduces under every seed**. A 3-seed stability check, which is the standard defence, confirms a leak instead of catching it, because the leak is structural rather than random. Both features passed 3 seeds and both were fake.

The only test that works is a **properly nested encoding**: fit the encoding on an inner split of the fold's own training rows, never on the whole fold. Under nesting the gains inverted:

| Feature | Global OOF scheme | Nested scheme |
|---|---:|---:|
| Neighbour slope/curvature | +0.00019 | -0.00007 |
| Income x Age cross-TE | +0.00016 | -0.00008 / -0.00013 |

`src/15_leak_check.py` is that test.

The second tell is free and I ignored it for too long: **the OOF-to-LB gap should stay roughly constant.** When a change adds OOF but the gap silently absorbs it, the OOF gain is not real.

## Why almost nothing helped: the cardinality rule

Eight ensembling and feature levers came back flat or negative. One rule explains most of them.

Target encoding only helps when a boosted ensemble **cannot already split the column directly**. Compare distinct values:

| Column | Distinct values | Encoding helped? |
|---|---:|---|
| Annual_Income_USD | 13,214 | yes |
| Daily_Commute_km | 805 | no |
| Age | 45 | no |
| Number_of_Cars_Owned | 4 | no |

With 45 distinct ages and 669k rows, LightGBM can carve age into whatever shape it wants on its own. Handing it a target encoding of age adds no information and costs a leak surface. Income is the only column dense enough for the encoding to say something the splits cannot.

The same logic kills the model-diversity levers. Every gradient boosted model here correlates above 0.99 with every other:

```
              mega  realmlp  tunedlgb    xgb  xgb_tuned
mega        1.0000   0.9626    0.9988  0.9911    0.9966
realmlp     0.9626   1.0000    0.9622  0.9635    0.9578
tunedlgb    0.9988   0.9622    1.0000  0.9902    0.9971
xgb         0.9911   0.9635    0.9902  1.0000    0.9915
xgb_tuned   0.9966   0.9578    0.9971  0.9915    1.0000
```

They are not different models, they are the same model wearing different hats, and averaging a thing with itself returns the thing. The neural net was the only genuinely decorrelated member at 0.96, and it was too weak to earn nonzero blend weight. Diversity and strength were in direct conflict the whole time.

## Levers tested and falsified

Baseline: multi-seed LightGBM + CatBoost rank average, **OOF 0.94537, LB 0.94561**.

| Experiment | Script | Result | Verdict |
|---|---|---|---|
| Add a tuned XGBoost | `04_tune_xgb.py` | 0.94170 to 0.94431, 0.9966 correlated | redundant |
| Optuna tuning | `04_tune_xgb.py` | +0.00002 | noise |
| Feature engineering (pair TE, bins, group aggregates) | `05_feature_engineering_ab.py` | flat, worse combined | null |
| The original real dataset | `06_original_dataset_ab.py` | -0.00023 | hurts |
| Neural net for diversity (0.96 correlation) | `08_stack_and_blend.py` | optimal blend weight 0.0 | no help |
| Stacking (logistic regression meta) | `08_stack_and_blend.py` | 0.94494 | worse than one model |
| Pseudo-labeling | `07_pseudo_label_ab.py` | -0.00102 | hurts |
| Slow LR + heavy smoothing | `09_slow_lr_ab.py` | +0.00005 | noise |
| Narrow income-band TE | `10`-`12` | +0.00041 at 250k, +0.00015 full | shrinks with data |
| Adversarial validation | `24_adversarial.py` | train/test indistinguishable | no shift to exploit |

The pattern in the last row is worth its own note: a win measured on a 250k subsample lost **63%** of its size on the full 669k rows. More rows let the model learn the structure unaided, so a subsample result is a hypothesis, not a finding.

## Was the ceiling reachable?

I fit a probit MLE to the published data-generating recipe to estimate a Bayes ceiling and got **0.93777**, well *below* the 0.94672 the leaderboard was already achieving. That falsifies the recipe as a description of the actual dataset rather than establishing a ceiling. Fitting a generator formula and finding it cannot reach observed scores means the formula is wrong, not that the scores are impossible.

A more useful measurement was the learning curve, which was still rising at full data (0.94346 to 0.94614), with **74% of the slope coming from encoding labels**. The binding constraint was label supply, not model capacity.

## Layout

```
src/01-09    the eight falsified levers
src/10-14    income banding, full-data confirmation, seed stability
src/15       the nested leak test
src/16-28    production models, blending, n-fold sweeps, adversarial validation
production/  the two final pipelines (margin-only, and the 8-seed bagged variant)
```

Data is not in the repo. Drop the competition CSVs in `data/s6e9/` and the scripts will find them.

## Writeups

- [S6E9: I falsified 8 leaderboard levers](https://www.kaggle.com/code/andrewleal70/s6e9-i-falsified-8-leaderboard-levers)
- [S6E9: why income encoding works and nothing else does](https://www.kaggle.com/code/andrewleal70/s6e9-why-income-encoding-works-and-nothing-else)
