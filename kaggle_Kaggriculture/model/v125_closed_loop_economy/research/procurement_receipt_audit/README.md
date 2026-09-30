# V125 逐笔采购收据审计原型

本目录把**发出前目标 → 实际订单 → 官方逐单位成交 → 下一帧原确认函数**连成可追溯记录。结论与限制见 `REPORT.md`。它不修改候选，也不会授予 G1 或线上金牌资格。

推荐入口为 `audit_receipts_v2.py`。已使用的 `audit_receipts.py` 保留原 SHA；v2 只修正候选诊断在保存为 JSON 时的 tuple/list 口径差异，仍比较全部字段，不删事件或放宽动作比较。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_receipt_audit/audit_receipts_v2.py \
  --run-dir kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/已有运行目录 \
  --game-index 0 \
  --output kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_receipt_audit/新审计目录
```

只接收已完成 719 步的 official 动作带。开始前核验并冻结源候选、runner、引擎、trace 和观察器 SHA；输出目录已有 manifest 时拒绝覆盖。环境参数必须与源 manifest 一致。只用源 trace 的原双方动作推进官方引擎，原候选每步重新调用一次并与原动作严格比较。**每次完整审计会调用原候选 719 次；这些是同一已有对局的复现，不增加独立比赛。** 不重新调用对手。观察器开销不用于延迟资格。

观察方法：

- 用 Python trace 观察冻结候选原 `confirm_orders` 的每次进入、每笔原生 `got` 计算和核查前后计数；没有用外部公式冒充原函数执行。
- 观察原 `economic_plan` 返回值与 `market_orders.fixed_order` 调用点的局部变量，记录预算接受和原订单位置。观察期间不改候选文件、函数或决策值。
- 透明包裹官方 `_commit_unit`、`_do_buy_land`、`_apply_unit_action`、动物日结及仓库回收函数；每次都执行原函数。成交按官方 `_process_market` 的真实订单索引关联，而非凭商品名猜序号。
- seed 外部收据为 `终帧种子 − 初帧种子 + 官方实际耗种`。animal 外部收据为 `终帧总动物 − 初帧总动物 + 逃逸 + 已观察到的日末动物溢出`。土地由真实解锁变化核对。
- 末步没有下一次代理调用的订单只标 `external_terminal_only_no_next_agent_call`，不得伪造候选核查。两条真实验证轨迹末步均没有这三类采购；该分支另有纯收据测试。

每笔 `receipts.json` 主要字段：

| 字段 | 定义 |
|---|---|
| `issued_step`, `order_index`, `order` | 原 trace 的动作步、市场订单索引和内容 |
| `target_capture` | 原调用点源码行号、预算变量、真实目标与目标含义 |
| `net_target_gap` | 原策略该作用域目标减该作用域实际量，最低为 0 |
| `actual_committed_quantity`, `actual_money_delta` | 官方该订单各单位 commit 的合计与真实现金变化 |
| `original_confirmation` | 原函数下一可见帧核查的 `requested`、`got`、前后摘要和源码行号 |
| `actual_seed_consumption` | 官方接受 PLANT 后真实耗种；原始请求数另列 |
| `animal_escapes_same_step`, `animal_overflow_same_step` | 与采购同帧的可见动物损失补偿项 |
| `over_target_requested_quantity`, `over_target_committed_quantity` | 请求量/成交量分别超过原净缺口的单位数 |
| `issues`, `status` | 缺字段、确认冲突、不闭合、超目标均为 PENDING；完整仅称 DIAGNOSTIC_COMPLETE |

目标口径必须保留：动物取原 `plan['animals'][item]`，实际量包括地块、仓库和随身；种子取原市场函数的库存缓冲目标与 `available_seeds`，**不是整个作物生命周期的产能目标**；土地取真实触发分支的 `lands < 3` 静态容量上限，并记录日数、占用格和预算条件，**没有独立的事前土地计划变量**。它能检验重复越过实际 guard，不能证明扩地经济上值得。若未来 G1 要求独立目标决策日志，土地项仍须 PENDING，不能把上限伪装成预定建设量。

文件：

- `audit_manifest.json`：源运行、游戏键、源文件/观察器 SHA、单进程约束。
- `summary.json`, `receipts.json`, `validation.json`：逐笔收据、结论与文件校验。
- `candidate_*.jsonl.gz`：原确认调用、逐笔检查、经济计划返回和预算订单调用。
- `official_*.jsonl.gz`, `external_state_frames.jsonl.gz`：真实成交、实际播种、损失和前后资产。
- v2 的 `diagnostics_comparison.json`, `reproduced_strategy_diagnostics.json.gz`：原始 Python 及 JSON 口径的完整诊断比较。
- `saved_audits_validation.json`：从保存证据重建全部收据、检查前序动作链、缺字段/重复/超目标/末步故障注入。
- `confirmation_microcases_r0/result.json`：官方纯函数与原确认函数的两个构造反例和一个控制例。

当前原型按 V125 R0/R4 的函数结构观察；函数结构不受支持时拒绝推断。还不支持同一步同商品多笔采购的外部净变化分配（会保留不闭合/PENDING），也未归因手动 DROP 导致的动物销毁；不得给这些情况自动放行。由于还未实现 G1 接口合并，冻结的 `summarize_g1.py` 采购项仍保持原 PENDING 行为。正式接入需新版本、核验完整新 8 seed × 双席块及目标语义，不覆盖旧诊断资格。
