# v94：v80 + v85 + v87 严格三成员小融合

## 预注册结论

- 实验 ID：`v94_strict_v80_v85_v87_cv_blend`
- 研究周期：`C01`，预留普通版本位置 `12`
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-04
- 实验类型：`SMALL_BLEND`
- 正式关闭后计入周期：`true`
- 提交预算：`0`
- preflight revision：`R6_SEALED_ARCHIVE_PROVENANCE`
- runner SHA-256：`8cc913d874a1866f51d24879cae728135f8e1170bdb3da9b82dbee32d0fd9943`
- frozen config SHA-256：`8361b731d09466cdd97a9b1cf5699650de712c8b5185b7b82b0f3e2736781a34`
- tests SHA-256：`502afc31792e50660091db7cee5c2281aa12e0abeee896218b741f1918c71139`

本目录只完成预注册和工程实现。当前禁止正式运行；没有读取或使用正在运行的 v92 中间预测、分数、checkpoint 或日志，也没有创建任何效果证据。

## 为什么是 GO_DISTINCT_MECHANISM

历史审计没有找到可信、未重复的普通单模机制：收入交叉、平滑、邻域表达已经有明确否定边界；CatBoost/MLP 再调参也只是盲搜。v87 则是一个已关闭、机制明确的独立表示实验：只给 strict v80 增加通勤负担和充电可达性特征，40 折验证中对 v80 固定 seed42 桶胜出 `23/40`，OOF `0.9462357606221546`，虽不足以单模晋级，但满足另立融合预注册的多样性条件。

无标签的已关闭预测诊断进一步确认它不是复制品：v85-v87 Spearman 为 OOF `0.9968860455`、test `0.9983808764`；比 v80-v87 的 OOF `0.9983390242` 更低。该诊断只用于证明非同一性和机制合理性，没有读取标签挑候选、规则或权重。

唯一问题是：冻结的 v87 通勤/充电表示，能否在不改变任何基模型的前提下，为当前最佳 strict v90 增加可复现残差信号？

## 冻结成员与谱系边界

正式成员恰好三个，且都是已关闭的原子单模：

1. `v80_strict_v61_outer104395303_40f`：strict 核心。
2. `v85_naji_v74_40f`：Naji/sklearn TargetEncoder 多样性。
3. `v87_strict_v80_commute_charging_burden_40f`：通勤/充电基础设施表示。

v80 与 v87 共享基础配方，但 v87 是独立训练出的预测，不是包装或重用 v80 预测。本实验只允许这一次针对明确新增表示块的增量消融。

`v90_v89_member_verify_budget_retry` 是唯一 strict 对照，不能作为成员。它虽然由 v80/v85 派生，但本实验只比较其已冻结结果并独立重建其五折分支，避免把 v90 与自己的子成员同时混入。若 v94 晋级，后续只能把 v94 当作一个融合节点，不得再与 v90 或 v80/v85/v87 重复叠加。

禁止成员包括 v61、v64、v72、v74、v83 和 v90；不纳入未关闭的 v92/v93。

## 冻结元验证协议

- 五折：`StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`。
- 每折只在 meta-train 内，分别对三个成员拟合 mid-ECDF；再应用到该折 meta-train、holdout 和 test。
- 权重是步长 `0.05` 的三成员非负 simplex，总计 `231` 个组合。
- 只按 meta-train AUC 选权重，holdout 只用于评估。
- 同分在 `1e-15` 内时：先取离该折独立重建的 v90 权重 `(w80_base,w85_base,0)` 的 L1 距离最小者；再取更低 v87 权重；再取 v85 权重更接近 `0.5` 者；最后取更低 v85 权重。
- 五个 holdout 拼成主 OOF；test 为五个 meta-fold test 预测的平均。
- 三成员各 `1/3` 只作诊断，绝不能替换主方法。

每折还会用 v90 原权重网格和原并列规则独立重建 v80/v85 对照分支。正式完成前，重建的 v90 OOF/test 必须与已冻结 v90 数组逐元素一致，绝对误差最多 `1e-12`；否则失败关闭。

## 晋级门槛

唯一项目基准为 v90：

- `base=v90_v89_member_verify_budget_retry`
- `base_oof_auc=0.9463720745765888`

只有同时满足以下两项才 `PROMOTE`：

1. 主 OOF 相对 v90 至少 `+0.0001`；
2. 五个 meta holdout 对 v90 全部严格提升，即 `5/5`。

否则完整结果仍落盘，但结论是 `REJECT`。不能用等权控制、单折结果、相关性或 test 分布替代门槛。

## 工程与失败治理

- audit 只做真实文件的流式 SHA 和 JSON/schema 校验，不加载真实 OOF/test 数组，并明确输出 `NO_PREDICTION_ARRAYS_READ`。
- formal 才调用 v80/v85/v87/v90 自身完整 verifier，再核对所有 runner/config/results/sources/OOF/test 哈希和 canonical newline ID 身份。
- 12 GiB process peak RSS、900 秒 wall、1 CPU；输入核验、元折计算、staged verify 都计入预算。
- 使用 `flock`，持锁后再次检查 COMPLETE；只允许同一正式实例写终态。
- COMPLETE 采用 staged 产物、独立 verify、最后原子提交 `cv_results.json`。
- 资源失败和异常失败都在锁内写统一最小 schema，列出 expected/present/missing artifacts；任何失败后已有预测都标为无效。

### R2 预运行修订

独立审计指出的三个工程阻断已在未运行状态原地修复，研究假设、成员、权重协议和门槛均未变化：

1. `validate_resource_check` 现在从原始 elapsed seconds、peak RSS bytes 和冻结预算独立复算 breaches，同时核验 bytes/GiB 换算；漏报、伪报、单位漂移均 fail closed。
2. FAILED 关闭不再调用可能因来源/data 漂移而重复抛错的严格 `code_and_input_hashes`。它逐文件保存预期 SHA、能取得的现场 SHA/size 和采集错误；即使所有 hash 读取都失败，仍可校验 schema 并原子写入 `FAILED_EXCEPTION`。
3. formal 会先序列化 provisional pending 文件并对该实际文件完整重建；采样包含该 verifier 的资源后，再生成最终 pending 文件并再次对实际文件运行完整 verifier。文件在 verifier 期间的 SHA 若变化即拒绝；第二次完整核验通过且 pre-commit 资源 guard 通过后，才允许最后一次 `os.replace`。

新增合成攻击回归覆盖 breaches 漏报/伪报、GiB 伪造、hash 采集全失败、来源缺失以及 staged 文件在 verifier 期间被篡改。R2 自测没有加载真实预测。

### R3 预运行修订

第二轮独立复审要求进一步封闭证据和资源状态机，仍未改变模型协议：

1. FAILED 的每条现场记录必须逐项匹配冻结 key 与规范化 path。`exists=true` 时只能是完整成功态（hash、size 齐全且无 error）或完整失败态（hash、size 都为空且有 error）；`exists=false` 时只能使用由冻结 path 唯一生成的 FileNotFoundError。验证会重新采集所有当前文件并逐字段比较，因此伪 hash、伪 size、伪不存在或替换错误文本均不能通过；error 和 mismatch 索引也必须重新计算一致。
2. 资源 phase 固定白名单及 fold 域：输入前后只能为 `None`，meta 折只能依次为 `1..5`，输出、两阶段 verify 和 pre-commit 都只能为 fold 5，异常关闭的 fold 必须等于已完成 meta 折数。COMPLETE 必须完整覆盖规范序列；资源失败必须是规范前缀且只有末项超限；异常失败必须是规范前缀加唯一 `FAILED_EXCEPTION` 末项。
3. pre-commit 资源采样现在写入最终 payload 和完整资源序列；该最终实际 pending 文件会进行第三次完整 verifier，通过后才执行唯一终态 `os.replace`。

R3 新增攻击回归覆盖 `FORGED_PHASE`、fold 999、phase 缺口/乱序/错误折号，以及可读与缺失输入的 path、exists、hash、size、error 和失败索引伪造。R3 自测同样没有加载真实预测。

### R4 预运行修订

第三轮独立复审要求补齐资源单调性和真正终态封印，模型协议继续保持不变：

1. 完整资源序列除 phase/fold 外，还要求 `wall_elapsed_seconds`、`peak_rss_bytes`、`peak_rss_gib` 分别非递减；相等合法，任何一项回退均拒绝。
2. 第三次文件级 verifier 验证 pre-commit payload 后，记录该文件 SHA；只有文件未变化才采样 `FINAL_GUARD_AFTER_THIRD_FILE_VERIFY`。该 guard 被追加到完整资源序列，900 秒或 12 GiB 任一超限都会在构造 sealed COMPLETE 前抛出资源失败，绝不提交。
3. guard 通过后构造并序列化唯一 sealed payload，再对该实际 pending 文件执行第四次完整 verifier；之后不再采样、不再改写 payload，直接执行唯一终态 replace。第四次 verifier 定义为对最终资源封印的只读验证，不再派生新资源字段，因此不会形成“采样后又验证、验证后又采样”的无限循环。

R4 合成攻击覆盖 elapsed、peak bytes 和 peak GiB 回退，并模拟第三次 verifier 后墙钟从 899 秒跳到 901 秒：最终 guard 必须抛出 `WALL_CLOCK_BUDGET`，payload builder 不得执行，终态 replace 调用次数必须为零。

### R5 预运行修订

第四轮独立复审指出 COMPLETE verifier 与第四次验证后的资源窗口仍需封闭：

1. `validate_complete_result_schema` 不再只逐条验证资源记录，而是强制调用 `validate_resource_sequence`。provisional COMPLETE 使用合法规范前缀，最终 sealed COMPLETE 必须使用完整序列；二者都执行 wall time、peak bytes、peak GiB 非递减检查。合成测试把已落盘 COMPLETE 的一个中间 elapsed 节点向后篡改，完整 schema verifier 必须拒绝。
2. 第四次 sealed-file verifier 返回后，下一条操作立即读取 monotonic time 和 process peak RSS，形成不写入 sealed payload 的 `POST_SEAL_COMMIT_GUARD`。该 guard 只承担最终提交授权：超出 900 秒或 12 GiB 时，完整 sealed pending 通过硬链接归档为 `sealed_complete.invalid.json`，随后可靠原子关闭 `FAILED_RESOURCE_BUDGET`；归档在失败 schema 中明确标记 `invalid_for_use=true`。
3. POST_SEAL guard 通过时，不再采样、不再改写，直接调用唯一 COMPLETE 终态提交。它不写回 sealed payload，避免重新触发无限 verifier 链。

R5 动态攻击固定 sealed payload 内 `FINAL_GUARD=899s`，让第四次 verifier 把时钟推进到 `901s`。测试确认 POST_SEAL guard 捕获 `WALL_CLOCK_BUDGET`、COMPLETE 提交次数为零、最终状态仅为 `FAILED_RESOURCE_BUDGET`，且无效 sealed 归档已记录。

### R6 预运行修订

第五轮独立复审指出 post-seal 超限的归档证据仍不足，本轮只封闭该证据链，不改变模型、权重、门槛或资源协议：

1. post-seal 超限会在抛出 `ResourceBudgetExceeded` 前记录本次 sealed pending 的绝对路径、SHA-256 和 size，以及归档的实时 SHA-256/size、`link_attempted`、`link_succeeded`、errno 和包含异常类型/双路径/原始 message 的规范化 `link_error`。
2. 同名 `sealed_complete.invalid.json` 已存在时不再吞掉 `EEXIST`。只有实时 SHA/size 与本次 sealed pending 完全一致才标记 `EXISTING_IDENTICAL` 和 archive success；不一致必须标记 `STALE_COLLISION`、`archive_failed=true`，失败摘要的 `present=false`，但物理 stale 文件仍列入 invalid artifacts。
3. `validate_failed_result` 会重新计算当前 archive SHA/size，并与本次 sealed provenance 和所有派生状态逐项核对。归档后篡改、伪造 success/status/error，或预置不同内容触发 stale EEXIST 均不能通过验证；所有路径仍保持零次 COMPLETE commit 并可靠关闭为 `FAILED_RESOURCE_BUDGET`。

R6 新增合成攻击覆盖：成功硬链归档后删除 pending 再篡改 archive；预置不同内容造成 stale `EEXIST` 并尝试伪造 success/link_error；以及预置完全相同内容时只经实时 hash/size 核验后接受 `EXISTING_IDENTICAL`。全部测试均不读取真实预测数组。

## 运行方式

```bash
python model/v94_strict_v80_v85_v87_cv_blend/v94_strict_v80_v85_v87_cv_blend.py --mode audit
python model/v94_strict_v80_v85_v87_cv_blend/v94_strict_v80_v85_v87_cv_blend.py --mode smoke

# 本次禁止；以后获得明确授权才允许：
python model/v94_strict_v80_v85_v87_cv_blend/v94_strict_v80_v85_v87_cv_blend.py --mode run
python model/v94_strict_v80_v85_v87_cv_blend/v94_strict_v80_v85_v87_cv_blend.py --mode verify
```

## 当前边界

这是 `GO_DISTINCT_MECHANISM` 的预运行候选，不是效果结论。未修改 experiments、phase2、NEXT 或 research_cycle，也未产生 candidate snapshot、fold、sources、OOF、test、submission、日志或 cv_results。
