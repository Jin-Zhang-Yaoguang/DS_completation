# A2 strict oracle 与 stateful queue 的 5 胜差距

日期：2026-08-24  
证据边界：只使用已经暴露的 V13 screen36、既有 oracle/stateful 工件及其确定性重放；未读取 V14 fresh screen、confirm 或 test；未修改现有候选。

## 结论

**唯一充分方向是移除“我方与对手完整 public farm 必须逐字相等”这一条件，同时保留 `clone_distance <= 4`、stateful shadow、逐步公开状态校验、V8/V8、strict all-SELL、同回合 transfer 禁止、排列上限和我方收入不下降等全部约束。**

这不是猜测。旧 screen36 上只做这一项因果消融后：

| 模型 | W/T/L | 纯胜率 | 改序回合 | shadow fault |
|---|---:|---:|---:|---:|
| A2 parent | 16/40/16 | 22.22% | 0 | — |
| deployable stateful | 47/10/15 | 65.28% | 614 | 0 |
| strict perfect-info oracle | 52/10/10 | 72.22% | 942 | — |
| **仅去 exact public equality** | **52/10/10** | **72.22%** | **915** | **0** |

消融版与 oracle 的 **72/72 task outcome 完全一致**，且 72 局末尾全部 `shadow_trusted=true`、`shadow_update_errors=0`。它不是移除所有 public 安全约束：粗粒度 `clone_distance<=4` 仍在，下一步 own/opponent money、market inventory、opponent public farm 的 forward-conformance 仍在。

这只是已暴露面板上的因果诊断，不是新验证。36-source oracle 的 cluster-bootstrap 95% 区间为 59.72%–83.33%，仍包含 65%；正式结论必须由冻结候选的新面板给出。

## 为什么恰好少 5 胜

72 个 task 的结果对齐没有任何杂乱互换：

| baseline → oracle / stateful | task 数 |
|---|---:|
| L → L / L | 10 |
| **L → W / L** | **5** |
| L → W / W | 1 |
| T → T / T | 10 |
| T → W / W | 30 |
| W → W / W | 16 |

所以 52 与 47 的差距不是平均收益漂移，也不是一批 W/L 相互抵消；它精确等于 6 个 oracle `L→W` 中 stateful 少救回的 5 局。完整 72-task 对齐见 `task_alignment.json`。

对 6 个 `baseline L→oracle W` task 做透明重放：候选 parent 和 opponent shadow 只套观察 wrapper，不改变动作；6 局最终 reward 均与既有 47/10/15 artifact 逐元一致。逐步用真实 A2 action/private 计算同一 strict best response，得到 85 个“oracle 可改、stateful 未改”的机会：

- 85/85 的预测 A2 action 完全正确；
- 85/85 的预测完整 private state 完全正确；
- 85/85 为 V8/V8，且 shadow 一直 trusted；
- 最早 step 253、最低 conformance 253，远高于 96/72 门槛；
- 每方 market queue 只有 2–4 单，低于 cap 7；
- 85/85 已通过 strict all-SELL、无 same-turn transfer、至少两种商品、我方即时 SELL 收入不下降；
- **85/85 仅因 exact public equality 为 false 被拒绝；它们的 clone distance 为 0–2，全部满足保留的 cap 4。**

## 5 个缺口 task 的第一个被挡机会

| seed / seat | baseline margin | oracle margin | stateful margin | 第一个漏掉的机会 | clone distance | 漏掉 / 已执行 |
|---|---:|---:|---:|---:|---:|---:|
| 609572410 / 1 | -1080 | +456 | -987 | step 253，day10 hour13 | 2 | 16 / 6 |
| 1080458124 / 0 | -834 | +286 | -831 | step 443，day18 hour11 | 0 | 16 / 1 |
| 1815492436 / 0 | -226 | +286 | -146 | step 255，day10 hour15 | 0 | 13 / 4 |
| 2008231806 / 1 | -114 | +1244 | -113 | step 370，day15 hour10 | 2 | 21 / 1 |
| 2037284396 / 0 | -866 | +819 | -610 | step 255，day10 hour15 | 2 | 13 / 7 |

去掉 exact equality、保留 clone cap 后，这 5 局 margin 分别恢复为 `+456/+286/+286/+1244/+819`，与 oracle 完全相同。

`clone distance=0` 但 exact equality 仍可为 false，并不矛盾：前者只比较 hand/unlock/生产物数量，后者还要求 farmer/hands 位置、`hires_today` 与完整 tiles 排布逐字相同。独立 stateful shadow 本来就是为了正确建模这种公开生产路径不相同的情况；再强迫两座 farm 逐字相同，等于把旧 mirror 假设叠回独立 tracker。

## gate 逐项判定

| gate | 是否解释 5 胜缺口 | 证据 |
|---|---|---|
| `start_step=96` | 否 | oracle 在 step 96 前触发为 0；缺口最早 step 253。 |
| `minimum_conformance=72` | 否 | 85 个漏点最低 conformance 253。 |
| V8/V8 | 否，且应保留 | 85/85 都是 V8/V8；V5/V5 oracle 本来就 0 触发。 |
| exact public production equality | **是，解释 85/85 漏点** | 所有漏点均 equality=false。 |
| `clone_distance<=4` | 否，应保留 | 漏点范围 0–2；不必放宽 cap。 |
| same-turn transfer | 否，应保留 | 漏点均通过 strict 无 transfer 条件。 |
| 双方 all-SELL | 否，应保留 | 漏点均由同一个 strict SELL solver 生成。 |
| permutation cap 7 | 否，应保留 | 漏点只有 2–4 单。 |
| own-revenue nondecrease | 否，应保留 | 漏点均通过 `ours >= base_ours` 才进入 best response。 |
| 预测 vs 实际 | 否 | 85/85 action/private exact；0 shadow fault。 |

## 最小补丁建议

当前源码已经把 exact equality 与 clone cap 拆开，因此最小实现是让 Q2b 用 `require_public_mirror=False`，不需要再改 solver：

```python
QueueBestResponseAgent(require_public_mirror=False)
```

当前条件仍独立执行 `_clone_distance(obs) > self.max_clone_distance`，所以 flag 只关闭 exact cross-farm equality，不会关闭 clone cap。若将来重构，应保持这个逻辑分离，不能让 flag 包住整个 clone 条件。

除此之外不改任何 gate 或目标函数。预期的**旧面板机制上限**是 52W/10T/10L、纯胜 72.22%；本次消融已经达到该 outcome ceiling。它执行 915 次而非 oracle 942 次，是因为仍保留 V8/V8 和 clone 安全条件；64/72 reward vector 与 oracle 逐元相等，另外 8 局虽金额路径不同但 outcome 不变。

## 安全边界

对“对手确为绑定的 A2”这一威胁模型，放宽是机械且安全的：独立 private forward model 已在漏点逐步命中真值；当前候选还会在下一 observation 核验双方 money、market inventory 和对手 public farm，任一不符即永久 fail-closed。exact cross-farm equality 既不验证 shadow，也不验证对手身份，只验证“两座 farm 是否相同”，因此是冗余且错误的代理变量。

对任意未知 Kaggle 对手，不能据此宣称同样安全。公开 conformance 最早只能在下一回合发现错误身份，放宽后会增加在公开生产不对称状态中的覆盖。正式候选仍须：

1. 保留全部 forward-conformance 与永久 fail-closed；
2. 保留 clone cap、V8/V8、strict SELL 和 liquidity guard；
3. 用冻结字节在新的 A2+r002 双锚 screen 检查纯胜与故障率；
4. 只有新 confirm 的 A2 纯胜率达到预注册门槛，才可提交。

## 可复查产物

- `task_alignment.json`：72 个 task 的 baseline/oracle/stateful/消融逐项对齐；
- `gap_task_trace.json`：6 个 `L→W` task 的逐回合 perfect opportunity 与首个 gate；
- `public_equality_ablation.json`：72 局单变量消融结果；
- `trace_gap_tasks.py`、`run_public_equality_ablation.py`、`build_task_alignment.py`：可复跑脚本。
