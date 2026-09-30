# R5 共享紧迫性独立审查

范围：只读 `DESIGN.md`、`parent_r4.py`、`main.py` 及实现方微场景结果。只写此审查文件，不改候选、不运行完整比赛、不读取新 Replay / Blind。

## 变更范围

初审主文件 SHA 为 `68d52f5e3b261304d0c54f31081a6f4983039c2b429d4f70a6d5b159f4e308e0`；父副本 SHA 为 `8d3b634468d58c47df7c2c87644af04aa9d493e7c6381969866d4acfa3558431`，匹配上一轮 R4 冻结。

AST 独立比较确认：仅修改 `allocate`，新增 `shared_task_urgency`，顶层常量仅 `CANDIDATE_ID` 改变。所有其他 R4 执行、经营、市场、材料与收据函数均未改动，最后 callable 仍为 `agent`。

实现有两次共享紧迫性计算：活动 owner 抢占之前，使用尚未被终局搬运占用的工人；保留 owner 分配之后，再用剩余 `actors` 和扣除预约后的材料计算，供 matching 使用。`covered` 也在按编号处理 owner 之前一次登记全部可行旧合同，覆盖 R4 高编号 owner 尚未进入 `occupied` 的边界。

## 已修复的 P1：共享目标奖励不能授予无法完成必要操作的边

初审 `main.py:751–755` 的抢占判断只要求 `propose_contract` 非空；`main.py:775` 的 matching 则把共享 `urgent_bonus` 加给目标的全部非空 offer。

动物同格可以有不同的可行前缀：有麦工人的 offer 含 FEED，没麦工人的 offer 可能只有 HARVEST。后者的 `slack=None`，没有兑现保活的能力，不能因同格 FEED 紧迫而获得保活奖励或抢占资格。

最小反例：第 23 小时，一只 `consecutive_unfed=1` 的牛存有 6 单位 MILK；两名工人同在牛格，unit 0 无麦，unit 1 有 1 麦，仓内无麦。unit 0 的可行 offer 是 HARVEST，unit 1 只能在本日最后一帧 FEED。共享目标被判紧迫后，两条边同时加相同奖励，HARVEST 产值可能压过 FEED，导致 unit 0 收奶、unit 1 闲置、牛日终逃逸。R4 原来的逐边奖励在此场景会让 FEED 优先。

最终实现仍共享目标级紧迫标志，但 active 抢占（`main.py:754–756`）和 matching 奖励（`main.py:778`）都要求 `offer.slack is not None`，确保该边包含可兑现的必要阶段。旧 HARVEST 合同也不能把同格紧迫 FEED 错误标成已覆盖（`main.py:742`），并会释放该目标供有粮工人执行（`main.py:751–753`）。上述两种实际动作均已在微场景中核对为无粮 farmer PASS、有粮 hand FEED，动物存活。

紧迫奖励上界现为 `1 + 1.15 * sum(非负阶段价值)`（`main.py:769`），包含站在目标上的 1.15 倍权重。独立核对公式：每条 offer 的阶段是其 group 阶段的子集、cost 至少 1、每个 group 最多被匹配一次，因此该值严格超过所有非紧迫边可共同获得的基础权重上界。

## 场景核对

| 场景 | 预期 |
|---|---|
| 同目标一名近端、一名恰到最后窗口的远端工人 | R4 原反例已复现；R5 近端依次 WATER / HARVEST，远端 PASS |
| 只有远端工人可完成必要操作 | 9 帧路径后第 23 小时 WATER，植物存活；共享标志为 True |
| 真正最后一帧，有粮工人与无粮高产值采收工人同格 | 只有能 FEED 的边获得保活奖励，有粮 hand FEED，动物存活 |
| 已有 owner 承担保活，另一 owner 持非紧迫合同 | 正反编号均分别 WEST / CARE，`contract_urgent_preempted=0` |
| 活动 owner 保留后，剩余匹配池的最快工人变化 | 静态核对 `main.py:763–767`：重新以剩余 actors、free_groups 和实际剩余 available 计算；未声称另有独立竞争资源场景 |
| 等价首水合同，另有远处动物但近端工人可喂 | 实际 farmer WATER、hand FEED，未抢占首水 |

首水等价微场景：第 20 小时，unit 0 站在新苗上，合同剩余 WATER；3 格外牛需 FEED，unit 1 已站牛旁且有麦，unit 0 也有麦。R5 应让 unit 0 WATER、unit 1 FEED。该场景只验证共享紧迫性；不额外引入“首水永不可抢占”规则。没有近端可用工人时，真正最后窗口仍按既定抢占规则处理。

## 最终验证状态

独立核验 `micro_results.json` 时间为 `2026-09-05T10:26:22Z`，**13 / 13 检查通过、10 个短运行、21 次官方引擎转换**。候选 SHA `7091a3ad25bdc64854987592d38148404e84cc1b6e9a5fef101662f7e53999a2`、父 SHA 及 harness SHA 均与当前文件匹配。测试由实现方执行，本审查读取代码与实际动作结果，没有重复运行。

最终 AST 范围仍为 `allocate`、新增 `shared_task_urgency`、`CANDIDATE_ID` 三处；未修改其他 R4 机制。第一阶段共享紧迫性排除已经终局搬运的工人，完整 covered 集合在 owner 编号循环前建立；第二阶段在 owner 分配后重新计算。最后 callable 仍为 `agent`。

本轮约定范围内未发现剩余阻塞缺陷，可交父代理冻结后开展独立强度验证。首水测试是“已持有剩余 WATER 合同”的等价场景，不是完整 PLANT→收据→WATER 回放；R4 的其他执行边界也未因本轮通过而获得额外证明。审查通过仅表示本轮有界机制与范围可核验，不表示完整对局强度或金牌门通过。
