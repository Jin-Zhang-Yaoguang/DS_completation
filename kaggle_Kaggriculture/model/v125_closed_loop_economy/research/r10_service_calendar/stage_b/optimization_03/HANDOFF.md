# P3 静态交付

源码可供根冻结并准备有限工程控制；尚未运行候选，未开放新完整比赛。

- 单文件：`integration_prototype.py`
- SHA-256：`b5bcdd51829e9df20686de08935e96f65ec3ca7f1bd13bf7f9c756cfaa0465e6`
- CID：`V125-R10-OPT03-PROTOTYPE`
- 授权范围：`ROOT_SCOPE.json`，SHA `e3c744a1b4848adb99f1123d5a34314048c61c2a44234ef37500646edfc609fa`。
- 28/28 静态检查通过，独立审查未发现阻塞。所有候选定义加载、策略函数、selector、solver、checker、engine 调用均为 0。

唯一新机制是保留 R9 原农业批量准入，再在扩地判断前，按当前最终农业组合重报剩余项目，至多让一个仅未来劳动被拒的项目尝试完整服务证书。旧净值、机会成本、资金前缀、容量、材料和执行公式保持；这是准入与调用范围变化，不主张和 P2 全字段等价。见 `integration_prototype.py:2309`、`:2341`、`:2443`、`:2474`、`:2515`。

## 构建与未改范围

`build_candidate.py` 从冻结 R9 读取 AST，并使用复制的 P2 服务模块、`integration_helpers.py` 和 `rescue_transform.py` 生成单文件。候选运行不访问父包，不依赖研究目录文件，不使用动态 exec。原 45 个顶层函数中 44 个 AST 完全不变，只有 `economic_plan_prefix` 接入新阶段；最后静态可调用定义仍是 `agent`，真实 loader 身份检查尚未执行。

五份模块 `calendar_compiler.py`、`scheduler.py`、`checker.py`、`route_admission.py`、`inline_modules.py` 与 P2 字节相同。原 `budget_quote` 整体 AST 相同；删除新 rescue 阶段与纯诊断/source 登记后，整个经济函数 AST 可还原为冻结 R9。`static_checks.json` 保留全部 28 项。

P2 原始源码、交付与超时证据未修改，快照在 `p2/`；`p2_preservation.json` 登记原文件 SHA。首个 P3 草稿 e507 及输入在 `drafts/e507aeaf/`。首版静态检查器选错 labor 节点并漏列 `__future__`，26/28 输出与脚本已留在 `drafts/static_checker_v0/`；更正的是检查器，不是候选行为。

## 工程接口

- 默认 `PARAMS.r10_route_mode = 'bounded_future_failure_rescue'`；`legacy` 原样调用单文件内的冻结 R9 经济函数副本。固定 Router 的 rescue 只搜索同一专家，adaptive 才搜索原四专家集合。
- `_r10_integration_rescue_key(obs, item, pos)`：只含 seat、品种、位置和目标种类，不含时间、价格或工人位置。
- `_r10_integration_select_rescue(st, obs, offers)`：输入已过原现金、正净值和当前劳动门的未获证报价，返回 `q / cycle / status`。q 需含 `_r10_rescue_key`、`selection_score`、`position`。排序保留原净值、近仓距离、位置及稳定枚举顺序。
- `_r10_integration_fail_rescue(cycle, obs, key, eligible_keys)`：只存失败身份。`st['_r10_rescue_cycles'][str(player)]` 分席持久化；未试候选优先，全部耗尽后下一帧才重置；同帧不能第二次尝试，不存 PASS 或跨帧许可。
- cheap 阶段的完整闭包可在源码 `:2443` 进入新阶段前，以外部只读 trace 捕获；无需为了测试额外改变候选。
- `receipt['r10_rescue']` 区分原 chosen、额外 rescue_expert、净值/选择分/task score、eligible 与拒绝数量、轮转和批准状态。`receipt['r10_future_route']['counts']` 保留 route/scheduler/checker/cache 的正确嵌套口径。

对选中的唯一 q，`:2474` 的 route 与 `:2475` 的后置资金门使用同一 `funding_trial`，通过后才在 `:2482` 起统一写入资金、粮账、工时、材料槽、种子、订单、许可、预测供给和 source。失败不改业务基线；未准入估值不入 crop_scores。获准作物才更新 task score，原 chosen/expert_scores 不替换为 rescue 分数。

## 必须保留的边界

一次 route 最多仍有 `max(0, 29-day)` 个未来日 scheduler/checker；旧报价和新增重报价也有成本，所以静态上界不能证明小于 1 秒。原执行器不消费证书，证书只是条件模型可行，不证明未来真实兑现。rescue 用款与材料槽可挤出随后 BUY_LAND，获准同品种 score 可改变旧任务优先级；这两项是明确行为代价。同帧再次调用不会复用已通过许可，因此不声称整个 plan 幂等。

后续仅按根的独立冻结与工程预算执行。`PROTOCOL_ADDENDUM.md` 已纳入交付 SHA 清单，原 R10 主机制和强度门仍有效；本交付不降低门槛，也不宣布金牌或运行门通过。
