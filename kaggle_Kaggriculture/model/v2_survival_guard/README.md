# v2_survival_guard

`v1_adaptive_market` 的保守增量版本。它保留两条完整生产路线与市场策略，只修复线上
回放中确认过的牲畜死亡，并把种子裁剪扩展到非小麦作物。

## 变更

- 每天 18 点后扫描已连续一天未进食的动物；携带小麦的最近工人只在最后安全时刻
  偏离原路线，前往对应牧场并执行 `FEED`。
- 第 672 步后关闭保护器，保留原路线在终局主动停止养殖的行为。
- 对 `CARROT`、`TOMATO`、`STRAWBERRY`、`MELON` 按未来种植前缀裁剪多余购买。
- `WHEAT` 只使用 v1 已验证过的“最后一次播种后停止购买”规则。更激进的小麦裁剪
  在公开回放中造成约 9.5k 回撤，已通过消融排除。

## 回归边界

`fixtures/` 保存 11 场 v1 公开对局的对手动作轨迹，覆盖两个席位、两条路线、三场
线上败局以及多场胜局。`regression_test.py` 在同一随机种子与席位下配对运行 v1/v2。
当前结果为 10 场完全持平、1 场增加 6,585 金币；关键场次在第 672 步前的牛损失
从 5 头降到 2 头。

轨迹来自 Kaggle 公开 episode，只作为固定对手回归夹具；离线回放金币不等同于原始
线上金币，也不等同于 Kaggle Simulation 评级。

## 本地运行

从仓库根目录执行：

```bash
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v2_survival_guard/smoke_test.py

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v2_survival_guard/regression_test.py

env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
  kaggle_Kaggriculture/model/v2_survival_guard/build_submission.py
```

提交归档根目录必须只有 `main.py`，入口必须是文件中最后一个 callable `agent`。
