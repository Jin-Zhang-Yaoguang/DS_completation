# P3 独立静态审查

审查对象为 `b5bcdd51829e9df20686de08935e96f65ec3ca7f1bd13bf7f9c756cfaa0465e6`。在本次授权范围内未发现阻塞，可据此冻结源码并准备有界工程控制；这不是运行验证通过，也不证明耗时或策略强度。

本次仅读取源码、用标准库解析 AST 和计算 SHA，没有导入候选或构建器，没有加载候选定义，没有调用报价、selector、route、scheduler、checker 或引擎。首稿 e507 已由作者快照，本报告对应抽出 selector 后的 b5bc 稿。

| 静态核验 | 结果 |
|---|---|
| 相对冻结 R9 的原顶层函数 AST | 仅 `economic_plan_prefix` 改变，其余原函数相同 |
| legacy 副本 | 改回函数名后与原 R9 `economic_plan_prefix` AST 完全相同 |
| cheap `budget_quote` | 与原 R9 AST 完全相同 |
| cheap 初始报价扫描 | 与原 R9 AST 完全相同 |
| cheap 批量提交循环 | 仅去掉新增 source 登记语句后，与原 R9 AST 完全相同 |
| compiler/scheduler/checker/route_admission/inline_modules | 五份文件与 P2 逐字节相同 |
| helper 内联 | 新源码中每个 helper 的 AST 与 helper 源文件一致 |
| 老 helper 差异 | 相对 P2 仅 `_r10_integration_finish` 的诊断语义调整；新增轮转 helper 另列 |
| route 调用位置 | 新 prefix 中只有一处，位于单个已选择 q 的条件块内，不在报价循环中 |
| 最后顶层函数或类定义 | `agent` |

原预算路径及 rescue 重报价分别见 [2309 行](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_03/integration_prototype.py:2309) 与 [2341 行](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_03/integration_prototype.py:2341)。rescue 使用农业批量提交后的闭包变量重新计算价格、边际雇工、自有粮机会成本、资金前缀和订单槽；只接受正原净值、当前日劳动可行且至少一个未来日原劳动失败的报价。净值没有改为毛收入代理。

[2443 行](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_03/integration_prototype.py:2443) 后才进入 rescue；原土地判断从 2515 行开始。rescue 候选排除 `reserved`、`plant_permits`，保留在途动物与本帧已准入动物禁新限制。adaptive 使用原四专家集合；fixed 使用原 chosen 的集合。失败不重新选择第二项。

[2474–2475 行](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_03/integration_prototype.py:2474) 对同一个 q 的完整 trial 先核 route，再核原 `prefix_admission`。2482 行以后的经营写入只在双门通过后执行，复制原提交块：共享资金、义务、工时、材料槽、饲料、种子、订单、许可、accepted、市场预测和 source 一并更新。route 失败或后置现金拒绝只更新失败轮转及诊断，不进入业务提交。土地随后读取更新后的资金；挤出土地是此新机制的明确行为代价。

完整义务沿用 P2：原合同、在途和 cheap accepted 三处工时累加均同步 source 登记，rescue 成功才追加第四处。实际资产与模型位置集合必须一致，合同无可表达报价、未分配在途、原日历 goods/work/feed 不同或已知不可能历史均继续拒绝。见 [source 合并与资金绑定](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_03/integration_helpers.py:142)。没有把未知启动条件升级为实际执行证明。

轮转由 [生产 selector](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_03/integration_helpers.py:22) 控制。key 只含 seat/item/position/目标 kind，普通时钟、价格和工人移动不重置。未试项优先；如果上一帧耗尽后新出现未试项，不会先清旧失败集使旧高分项插队。只有仍无未试项且已跨过耗尽帧才开新轮。选中前即登记 `last_attempt_step`，同帧重复调用拒绝第二次尝试；seat 各自保存轮转。失败 helper 只保存 key，不保存 PASS、证书、预算或许可。

未准入 rescue 不写入原 expert_scores/crop_scores。只有成功的作物 q 在 2511 行并入其原 task score；rescue_expert 单独记录，原 chosen/专家诊断仍属于 cheap 扫描。获准同品种 score 更新可能同时影响既有同品种任务权重；因此不声称整个新策略 Router 或执行顺序等价。

需要保留的边界：一次 route 仍会检查多个未来失败日，最多 `max(0, 29-day)` 次 scheduler/checker；报价扫描仍有原经济成本，静态调用数不能证明小于 1 秒。证书与原执行器路线没有直接消费关系，不能把条件日历通过当作未来实际服务。重复调用同一帧可以不再产生上次的 rescue 许可，这是不复用 PASS 的保守代价，不是完整 plan 幂等保证。成功 route 的缓存是本次规划内纯结果，不代表现金或实际采购获准，且不会跨帧复用。

后续控制应使用这份生产 selector 验证失败 A 后选 B、耗尽跨帧重试、新未试项优先、seat 隔离、同帧第二次不调用 route；集成控制应核 cheap 农业基线、单次 route、失败业务基线不变、成功全字段提交与获批才更新 score。这些是待执行的控制建议，本报告没有运行它们。

| 源文件 | SHA-256 |
|---|---|
| ROOT_SCOPE.json | `e3c744a1b4848adb99f1123d5a34314048c61c2a44234ef37500646edfc609fa` |
| integration_prototype.py | `b5bcdd51829e9df20686de08935e96f65ec3ca7f1bd13bf7f9c756cfaa0465e6` |
| integration_helpers.py | `ba55458b58ad072f330cb260dab4b271d3fc2e24466e2b199dc39b194c454a84` |
| rescue_transform.py | `4fc2f9d70e9c016309c943a39e3472566da38c68abbb2edb5f3ce2c4caab19a9` |
| build_candidate.py | `8d00596d84b1436685a1c195a3b91b93f3fe409b4cca4e13342f9786d507947b` |
