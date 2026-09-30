# V12C observable YARN complete-expert router

## 单一机制

V5 与 V8 的前 72 个决策回合已经在 V10/V11 的 prefix 审计中逐动作一致。
V12C 从 step 0 同步运行这两个完整专家，并在 step 72 只看公开的
`town.unlocked_shops` 做一次选择：

- 已解锁 `YARN_STORE`：整季剩余部分交给完整 V5；
- 否则：整季剩余部分交给完整 V8。

选择后不再切换，也不拼接 worker 计划。该版本不含市场残差、固定日节流、
premium floor 或价格阈值。

## 开发证据

机制先在互不复用 seed 的 V11 Round 1–3 上审查，再冻结后进入 V12 的
18-seed screen。Round 1–3 的共同对手配对反事实显示，相对固定 V8，YARN
局切换完整 V5 的总体得分率增量分别为 `+5.04 / +4.42 / +5.18` 个百分点；
三个轮次内按 0818/0819/0820 分层均为正，且没有单一共同对手为负。

这些数字只属于开发证据，不是线上保证。screen 结果记录在
`screen_report.json`；只有 screen 仍保持增益且主要对手不退化，才允许进入
后续正式验证。

## 构建与本地检查

```bash
PYTHONPYCACHEPREFIX=/tmp/kag-v12c-pycache \
  .venv/bin/python -m unittest \
  kaggle_Kaggriculture.model.v12c_yarn_complete_router.test_main -v

PYTHONPYCACHEPREFIX=/tmp/kag-v12c-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v12c_yarn_complete_router/build_submission.py
```

最终 Kaggle 文件是 `submission.tar.gz`，线上只依赖归档内 Python 文件。

