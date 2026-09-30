# V12B-v2：胜率约束的可观测市场反馈

最终模型 ID 是 `v12b_v2_winrisk_feedback_gate`，完整父策略是字节级封存的
`baseline_v8`。神经网络、Replay Trace、固定日期动作和终局清仓都不是本方案的
主机制。

## 单一新增机制

V8 仍负责生产路线、工人动作、订单种类、市场排序和季末安全。残差模块先用连续
可观测状态判断是否发生同质化供给冲击：价格弱、公开库存高、扣除自己计划卖量并
加回确定性商店消耗后对手供给下界为正、对手公开动物产能足够，并且库存可在季末
前由实际解锁商店消化。只有 V8 已经提交的 `EGG/MILK/WOOL` 卖单可以被减少。

V2 在这个 proposal 上增加唯一的胜率门：

```text
自己公开银行 > 对手公开银行  -> 原样执行 V8，保护当前领先
自己公开银行 <= 对手公开银行 -> 允许市场反馈暂缓，承担方差争取翻盘
```

零是胜负目标的自然符号边界，不是从 Replay 拟合出的金额阈值。仓库压力、价格地板
不可辨识和最后两天继续 fail-safe 回到 V8。每次真实触发累计记录
`step/item/pre_money_gap/held_quantity`，而 `lead_protection_bypasses` 只计数本来会
通过全部反馈资格、但因公开领先而被阻止的 proposal。

## 为什么替换 V1

已淘汰的 B-v1 已完整保存在 `archived/v1_market_feedback/`。在已暴露的 screen18 上，
它相对 V8 的平均金币差增加 16.63，但得分率下降 1.1905 个百分点；出现 4 个
`W→L`、2 个 `T→W`、0 个 `L→W`。四个坏翻转触发时公开银行领先 51，两个好翻转
触发时公开银行恰好持平。这是“赚更多钱却更容易输”的目标错配，而不是阈值偏一点。

## 当前证据边界

B-v2 只在同一批已暴露 screen18 上做因果回归：7 类对手、18 个 source、双席位，
共 252 个严格配对。相对 V8 得分率增加 0.3968 个百分点，平均金币差增加 14.89；
2 个 `T→W`、0 个 `W→L`，每类对手得分率均未下降。57 次真实触发全部发生在公开
银行落后或持平状态。

这不是泛化证据：唯一正得分仍来自设计前已经见过的同一个 source、同一个对手的
双席位，没有 `L→W`；57 次触发中 55 次是 MILK，EGG 尚未覆盖。公开银行暂时落后
也不等于终局会输，因此未见正式面板仍可能出现放行暂缓后把潜在胜局变成失败。
`screen_v2_report.json` 的用途仅是确认失败修复方向，没有访问 formal100。

## 验证与构建

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation
PYTHONPYCACHEPREFIX=/tmp/v12b-v2-pycache \
  .venv/bin/python -m unittest discover \
  -s kaggle_Kaggriculture/model/v12b_market_feedback_router -p 'test_main.py' -v
PYTHONPYCACHEPREFIX=/tmp/v12b-v2-pycache \
  .venv/bin/python kaggle_Kaggriculture/model/v12b_market_feedback_router/build_submission.py
PYTHONPATH=$PWD PYTHONPYCACHEPREFIX=/tmp/v12b-v2-pycache \
  .venv/bin/python kaggle_Kaggriculture/model/v12b_market_feedback_router/package_qa_v2.py
```

`submission.tar.gz` 只包含 `main.py` 和封存为 `parent_agent.py` 的 V8。独立 package
QA 使用 B-v1 已暴露的 3 个 QA seed、双席位，验证干净解包、720 步、719 次调用、
`DONE/DONE`、零 stderr，并逐步比较归档与 registry 的动作哈希及终局奖励。

旧 `smoke_report.json`、`multi_lineage_smoke_report.json`、
`paired_control_smoke_report.json` 和 `package_qa_report.json` 都属于 B-v1 历史证据；
B-v2 的有效文件是 `screen_v2_report.json`、`package_qa_v2_report.json`、
`submission_manifest.json` 和 `registry_entry.json`。
