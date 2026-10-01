# 完整 V100 的端到端复核与 CTBoost 推断合同对照

状态：`DESIGN_READY_NOT_STARTED`。本文件只给出可实施方案，不代表训练已执行。现有训练标签已被用于大量研究，重新划分只能增加端到端边界保护，不能称为新盲测。

## 两个冻结方案

| 方案 | V80/V85 | CTBoost 对外预测 | 元模型 | 作用 |
| --- | --- | --- | --- | --- |
| A：V100-E2E-REFIT | 完整两家族，各 40 折，外层训练块内重建 | 在整个外层训练块重新拟合一次，1426 树 | 保持 V90→V100 两层 fit-only ECDF、非负网格及最终推断规则 | 包含 CTBoost 的实际 V100 算法基准 |
| B：V100-E2E-CTBAG | 与 A 完全共享 | 外层训练块内生成 CT OOF 的五个模型，对外预测后固定平均 | 与 A 完全共享训练变换和权重；只替换最后 CT 查询向量 | 检验 CT 全量 fit 与五模型平均的合同差异 |

唯一主要变量为 CTBoost 对外推断的 full-refit / fold-average。两臂使用完全相同的 CT OOF，因此不会把“新原子模型、不同模型参数、新元权重算法”混入比较。A/B 都含 V80、V85 和 CTBoost；禁止改成 V85+V96 后与历史 V100 宣称胜出。

V90 仍按其固定五个元折的 ECDF/权重平均生成对外预测；V100 在完整外层训练 OOF 上拟合最终 ECDF/权重。相同流程用于外层验证与最终 test。每一层只在所处训练块拟合状态，不能直接加载历史 V90 OOF 充当新外层的中间预测。

## 数据边界与执行顺序

1. 冻结全部配方代码、参数、输入 SHA、五个外层 seed42 的行索引哈希、早停分割种子、原子折索引、TE 种子和元折索引。seed42 已用，只作固定可重复切分，不称独立确认 seed。
2. 对每个外层训练块 `T` / 验证块 `U`，进程中的训练函数只收到 `y[T]`；`y[U]` 单独留给最终评分函数。真正 test 不参与复核训练或选方案。
3. 在 `T` 内分别按冻结原始家族 seed 产生 V80 40 折、V85 40 折、CTBoost 5 折原子 OOF。所有变换的有监督状态只用当前原子 fit 行；`U` 只做 transform/predict。旧 OOF 不得拼入 `T`。
4. LightGBM 每个原子 fit 块 `F` 内，再固定 90% `S` / 10% `E` 早停划分。以 `S` 构造严格 TE 后在 `E` 选轮数；然后丢弃这次模型，在完整 `F` 重建严格 TE，以已选轮数无 eval_set 重训。原子 OOF hold 和外层 `U` 都不能用于早停。CTBoost 固定 1426 树，无早停。
5. 每个 V80/V85 原子模型同时预测自身 OOF hold 和 `U`，40 个 `U` 预测固定平均。CTBoost 五模型同时保存各自 `U` 预测供 B 平均；另在全 `T` fit CTBoost 预测 `U` 供 A。额外 CT full fit 只能使用 `T`。
6. 仅用 `T` 内重新生成的原子 OOF，调用 V90 的固定 5-fold mid-ECDF/0.05 网格，形成 `q_T`，并按 V90 原规则生成 `q_U`。这些内部元验证结果只属于外层训练过程，不把它们另称端到端无偏分数。
7. 在 `T` 的 `q_T`、`ct_oof_T` 上按 V100 原规则形成元训练状态：CT 权重网格 `0,0.025,...,0.5`，tie-break 最小 CT 权重；最终完整 `T` ECDF 和权重同时应用于 A/B 的 `q_U` 与各自 CT 查询向量。两臂权重数值必须相同。
8. 每个外层块先写两臂预测及来源 SHA，五折全部完成后才开放统一评估。只能按预注册的资源/实现错误条件停止，不能看到不利折后变更模型、轮数或去掉该折。
9. 所有完成后由父任务公共 `model/research_runtime/paired_auc.py` 评分（若该模块已经实现并验证），报告两臂 OOF、配对增量、每折方向及影响函数近似 CI。该 CI 条件于已经生成的预测，不包含训练/方法选择方差。

## 特征状态合约

- V80/V85 的纯逐行特征与原始数据标签先验可复用冻结定义；original 10k 必须固定 SHA，不能拼入 synthetic 训练。
- 若保留既有 train+test 无标签频次，应在预注册中明确 transductive feature-only 范围；A/B 共享相同静态矩阵。不能由 `U` 的标签、CT OOF、test 预测选择字段。
- V85 的 `TargetEncoder.fit_transform` 只接当前原子 fit 的行与标签；其内部 5-fold prior 测试必须通过。
- 早停子模型和最终 refit 必须分别重建自己的 TE 训练状态，不能把 F 上已经编码好的矩阵直接切给 S/E，否则 E 标签可能进入 S 特征。
- 阶段状态至少记录 `fit_ids_sha256`、`query_ids_sha256`、`target_scope_ids_sha256`、`feature_names`、参数/代码 SHA；对外预测只接受与其 fit-state 配对的矩阵。

## 可复用函数与必须适配之处

| 来源 | 函数/位置 | 用途与适配 |
| --- | --- | --- |
| `model/v80_strict_v61_outer104395303_40f/...py` | `strict_encode_key` 第 244 行；`strict_prior_self_check` 第 310 行 | TE 算法可复用。外层输入需改为本地 T 子数据和显式索引，不能依赖原 runner 的全局40折与固定完整数据长度 |
| 同上 | `load_recipe` 第 233 行；训练块第 1247–1297 行 | 复用冻结 static/TE key/参数；拆出 `fit_atom`，早停移入 F 内；不能调用完整历史 `train()` |
| `model/v85_naji_v74_40f/...py` | `encode_naji_fold` 第 378 行；`target_encoder_prior_self_check` 第 344 行 | 接受局部 x/y/query，保留 auto/10 编码与所有随机种子；需返回可用于 S/E 与 F 重建的状态 |
| 同上 | `load_probe` 第 330 行；训练块第 1419–1452 行 | 复用 Naji preprocessing，替换训练入口和 eval_set 范围 |
| `model/diagnostics/ctboost_remote_probe_20260905/kernel/s6e9-ctboost-oof-audit.ipynb` | cell `chapter-15`：`fit_features`；其他 feature cell 的 `transform_features`；`chapter-17`：`new_model` | notebook 已固定源码 SHA；抽取定义为 helper，禁止执行顶层 pip/install、原始 `RUN_CV` 或原始最终提交单元 |
| 同上 | `chapter-17` / `chapter-19` | 分别提供 fold 与 full-fit 两条 CT 查询路径。0.1.58 GPU、1426 树及原参数不变；新私有 kernel 保存 U 行身份、每折预测、配置、日志与模型，不生成比赛 submission |
| `model/v90_v89_member_verify_budget_retry/...py` | `fit_mid_ecdf` / `transform_mid_ecdf` / `select_v85_weight` / `run_meta_cv` | 算法可复用。改为显式局部数组，保留网格/并列规则；对外 query 可为 U，无真实 test 语义 |
| `model/v100_v90_ctboost_nested_cv_blend/...py` | `fit_mid_ecdf` 第 177 行、`choose_weight` 第 204 行、`nested_blend` 第 215 行 | 拆出元状态 fit/apply。A/B 共用同一拟合结果；不可直接调用带历史路径加载的 `load_inputs` |

推荐统一接口：`fit_atom(recipe, fit_rows, query_rows, seed_contract, early_stop_contract)` 返回 `query_predictions, model_state, evidence`；`fit_meta(train_oof, labels, meta_contract)` 返回 immutable ECDF 状态/权重；`apply_meta(state, query_predictions)` 不接受标签。CPU 与 GPU 之间仅交换带原始行 ID 和冻结索引 SHA 的文件，不能按隐含行序拼接。

## 计算量与预算估计

- 每个外层：V80 40 + V85 40 个正式原子 fit；每个正式 fit 对应一个 S/E 早停子 fit；CT 5 个 OOF fit + 1 个 full fit。五个外层共 **400 个 LGB 正式 fit + 400 个早停子 fit + 30 个 CT fit**。B 复用 CT fold 模型，只增加 U 推断和极小元运算。
- 当前历史实测（8 CPU 线程）：V80 40 折 `1553.6s`，V85 40 折 `1449.3s`。按外层80%数据和新增早停/refit粗估，完整CPU部分约 **4.5–7.5小时，8线程**；不能把这个估计套用到2线程。2线程未实测，保守工作预算可暂设16小时，先用一个无结果揭示的原子工程计时更新预算再冻结正式运行。
- 原私有GPU日志：CT连续fold约148–152秒，五折约766秒，全量refit约3.1分钟，全部完成约961秒。30个在80%数据范围内的fit预计 **0.8–1.5小时GPU**，不含排队和首次依赖下载；可冻结2小时GPU执行预算，硬上限另行在正式配置中确定。
- 内存：V80历史peak3.665GiB、V85约8.988GiB；正式建议每进程16GiB，CPU两家族串行，不并存其完整编码矩阵。GPU RAM需先在私有kernel小规模工程探针记录，不能凭CPU RSS推断。
- 进度按原子模型checkpoint，恢复前核对配置、fit/query索引和特征SHA；不重复训练已完成模型。已有正式历史产物不可作为新外层的原子checkpoint。
- 不应为了省钱把40/40/5改成5/5/5仍叫原V100确认。若预算不足，可以明确另建低成本端到端诊断，但其基准与原V100数值不等价，不能宣称超越；本设计尚未启动任何一档。

## 验收和停止

算法正确性先于分数：每条有监督统计/早停/权重拟合的标签范围排除 U；交换 U 标签不能改变任何训练态/预测文件；每行OOF恰好一次；A/B训练侧权重相同；B只能改变CT查询向量；所有输出有限且在[0,1]。

晋级门槛交由父任务冻结的续研协议确定，不能在观察A/B结果后降低。默认保留项目 `+0.0001` 与5/5方向要求；若父任务预注册了小增量证据线，只能用于发现筛查，不能自动改变正式晋级。若B没有证据，关闭CT推断合同分支；A的完整端到端结果仍有确认价值。

即便两臂都较历史 V100 `0.9463981465` 低，也必须报告。历史分数不进入新的配对增量定义。Public/test不用于挑权重、早停或决定保留哪一折；本计划提交预算为0。
