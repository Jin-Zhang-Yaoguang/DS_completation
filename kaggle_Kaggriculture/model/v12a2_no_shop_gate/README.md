# V12A2 no-shop-gate

这是 V12A 的机制级单组件删除：只移除“按已解锁商店过滤 EGG/MILK/WOOL”的规则，保留 Router 分支、小额出售、同回合入库、shed headroom、step718 fill 和全部 worker 路径。

在 frozen_v4 的关键失败 seed `1356333904` 上，它把 V12A 对 baseline_v8/learned_router 的 `-6` 恢复为与 r002 完全一致的 `+1610`（双席位）。完整开发 screen 结果：

- frozen_v3：对 r002 直接得分率 77.78%，7 个共同对手汇总 +3.97pp，最差单对手 0pp。
- frozen_v4：对 r002 直接得分率 75.00%，7 个共同对手汇总 +6.35pp，最差单对手 0pp；对 baseline_v8 从 V12A 的 -2.78pp 修复为 +2.78pp。

这是因果优先的 A2。另一个 `no_wool_throttle` 开发候选汇总分更高，但它是在看到商品级结果后选择，过拟合风险更高，不作为本次首选修复。

## Kaggle serving 入口修复

正式评测归档中的 `main.py` 把 `model_status` 放在 `agent` 之后；Kaggle 的
`get_last_callable` 因而会错误返回 `model_status`。线上包只交换了这两个函数
定义的顺序，使 `agent` 成为最后一个 callable，策略函数体和其余 16 个包内
文件均未变化。

- 旧包 SHA256：`53fda5ec6773a339fb181e2102c5e6e266620ecd0616a7034ea117587e20bd0b`
- 新包 SHA256：`e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8`
- 新 `main.py` SHA256：`f1b49085c5bc7964b744312fdf42fb24fd3f32d0d84c0daac5b2fb09d93b6e8b`

`package_qa_report.json` / `serving_entry_repair_report.json` 使用真实
`kaggle_environments.agent.get_last_callable` 加载 clean archive，并在 3 个已
暴露 QA seed、双席位上验证：每局 720 states / 719 calls、`DONE/DONE`、非
no-op、零 stderr，且每一步动作与 frozen_v5 原 `make_agent` formal policy
完全一致。未重新访问或运行 formal/test panel。

修复包已提交为 Kaggle Submission `55713355`，描述
`v12 A2 fixed: raw-loader verified causal no-shop-gate guard`，状态
`COMPLETE`。Validation Episode `97575885` 为 720 states、`DONE/DONE`、双方
奖励 27827/27966，证明线上加载的是有效策略；截至 2026-08-23 19:40:21
（Asia/Taipei）公开局 4 场、4/0/0、Rating 1022.2，仍远低于 80 场门槛。
