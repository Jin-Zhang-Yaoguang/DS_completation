# 当前接续：ddbk–ddbn 研究结束，下一版 ddbo

目标仍为3个经全部33个y68对手门控、独立新种子确认的实质不同模型。当前 **0/3**。本轮所有编译、训练、评估与诊断进程均收到exit_code=0，没有活跃进程。只改dd_family，未提交或推送，goal保持active。

## 本轮结果

| 版本 | 口径 | 胜场 | 平均胜差 | 自身现金 |
|---|---|---:|---:|---:|
| ddbj旧对照 | 原4开发seed×双席×y68v | 0/8 | -45424.375 | 68613.25 |
| ddbk | 同上，生产选项+按任务采购 | 0/8 | -124936.375 | 24796.75 |
| ddbl | 同上，允许额外备货 | 0/8 | -87916.75 | 36427.125 |
| ddbm | 同上，保住即将失养的资产 | 0/8 | -96747.375 | 44646.125 |
| ddbn | 仅复用696步前缀后的终局分支 | 0/8 | -102540.875 | 38935.875 |

本轮新增24条完整动态开发比赛。12条席0精确重放、ddbn的8条终局分支及16条终局现金流重放不追加为新独立竞技样本。ddbk/ddbl/ddbm/ddbn共享四个模型权重，不能计为多个独立成功模型。三个完整候选都hash不变、719步齐全、预算非负，未晋级。

## 标签、模型与执行

1. `compile_production_options.py ddbk --workers 4`：同Boey21train/7validation，6test未打开，28×719=20132官方逐步状态精确一致。将真实安装PLACE改为带位置INSTALL，合并相邻取动物→可选建造→安置、建造→安置、取料→FEED/FERT、DIG→PLANT。跨工人建造不伪装成可溯源完整链。
2. 训练76303成功服务折叠为73565选项，233取动物链、212建造安置链、1561取料维护链、530清理种植链。前置WAIT90，旧表述1101；粒度不同，不是同标签改善。初次编译遇到无成功服务工人的空键错误，失败部分另存 `task_policy_data/ddbk_incomplete_missing_empty_worker_events`，修复后全量重编，不混用。
3. goal345维/market221维/47goal tokens，含同格已承诺生产目标；原子动作仍44类。未来事件仅做标签，输入为当前可见状态和此前已选择承诺。`check_production_options.py`核对建造/取动物/安置、取3饲料喂1剩2、库存不重复承诺、已种同种不重种、跨工人依赖候选。
4. `train_production_options.py ddbk`：759401训练候选行；883验证完整query平均587.30候选，Top1=68.0634%、Top5=92.0725%。市场原请求验证准确率50.6782%、数量R2=.63180。四模型sklearn→numpy误差<1e-6。
5. `audit_option_ranking.py`：教师状态INSTALL真实4、预测5、全对4，样本少且不支持明显过度安装；FEED82/预测61/全对41，CARE91/62/55，PICKUP WHEAT10/29，DROP39/57。静态混淆不等于动态唯一根因。
6. `ddbk/production.py`展开任务前置动作，缺物料形成市场承诺，指定工人已持有的物料不重复采购；卖货保留已承诺库存。每天清空计划；只按直达距离剪候选，未对所有生产选项估计完整建设时间。ddbl只放开采购超过即时任务的限制，种子库存以工人数封顶，仍保留销售承诺保护和缺口补救。

## 关键归因

- ddbk四席0动物逃逸5/59/30/49，未喂动物日26/159/99/130。919260011买79只动物花35400，59只逃逸。完成大量任务没有消除维护—补建损失循环。
- ddbl逃逸18/17/27/15；未浇植物日411/385/330/456。开放备货只恢复部分收益。
- ddbm新增 `maintenance.py`，只用当前连续失养>=1的FEED/WATER义务，考虑返仓/距离/执行步数，贪心配工且保留可完成的既有维修任务；有义务时不新选PLANT/INSTALL。`check_maintenance_options.py`通过。四席0逃逸全部0，仍全负：保命有效，但产出、取货、交易和投资选择仍弱。
- ddbn发现并修正第29天没有日末刷新这条规则：终止步骤718，因此没有第29天末失养判定。只取消 `obligations` 却也解除 `filter_growth`，放开末期增长。8终局分支均现金比父版平均少5710.25。
- `audit_terminal_option_cash.py`官方真实成交审计：ddbn末日购地合计42000、动物4200、种子780，ddbm这些均0。16条父子轨迹逐步现金一致且守恒。故规则判断正确，但终局执行必须分别处理维护、未来回本投资与当前兑现，不能只清空维护义务。

## 下一步建议：ddbo，尚未创建

这套Boey参数化模型已做三条完整执行对照，均显著弱于ddbj，更弱于旧M&M强控制ddam（原4seed为6/8；全部20开发seed仅24/40，仍不稳定）。不要继续靠零散保命/终局补丁宣称接近成功，也不要重新大规模扫描已经失败的固定整局计划。

可优先做数据覆盖对照：保持明确的执行语义，转用已有M&M源训练参数化任务模型。当前只做了清单元数据核查，没有打开新的回放内容：ddm/training_manifest.json含146训练、40验证、29测试，内部seed完全隔离；146训练seed与Boey全部34个seed无交集，见 `diagnostics/mm_option_source_inventory.json`。这是数据覆盖假设，不保证竞技改善；同一套权重改规则不算独立成功模型。

实施要点：

- 先明确终局：第29天取消强制保命，但独立禁止无法在终局前兑现的新种植、动物安装和扩地；不要再让“无维护义务”自动解除增长限制。可以用已验证的终局分支诊断先确认此规则，但不能据此当完整新模型验收。
- 新编译器以新版本源manifest显式指定训练/验证源，保留SHA与官方逐步状态一致性；不要改旧编译器或复用不匹配编号。原Boey脚本和训练器硬编码28/21/7，需要新副本泛化。别打开29个M&M测试或6个Boey测试。
- 可先取已固定训练集中的小批验证M&M实际服务能否用当前INSTALL/前置任务表述覆盖，再全量训练；不要按开发对局胜负临时挑选教师计划，也不要输出未来源状态为特征。
- 若源外泛化仍弱，下一条实质路线应在学生自己到达的状态上，用官方动态续局的终局收益为可执行候选排序提供训练反馈。只能使用黑盒收益；不得使用y68动作/源码作学生标签或推理。它属于自生成改进数据，不是可调用教师的DAgger。优先检查旧ddaa/ddbb已做的反事实边界，避免重复单次作物替换的失败实验。
- 起步仍用原4开发seed×双席×y68v完整8局；改善后才扩展开发面板。正式seed不能用于调参，三稳定胜者目标与门控不变。

## 文件、运行与门控

- 本轮说明PRODUCTION_OPTIONS.md，对照diagnostics/production_option_comparison.json，逐版审计diagnostics/{ddbk,ddbl,ddbm}_development_audit.json，执行重放diagnostics/task_execution_VERSION_manifest.json。ddbn终局脚本diagnose_terminal_maintenance.py及诊断summary，不在candidate/runs冒充完整评估。
- `audit_option_development.py VERSION`核对完整比赛、hash、预算；`diagnose_task_execution_v2.py VERSION`对4席0做官方精确重放和现金守恒。
- 根 `.venv/bin/python`运行官方环境，dd_family/.venv训练sklearn。没有torch/xgboost/lightgbm/catboost。新文件只在dd_family，注意数据可能hardlink，不原地改数组。
- 运行中不得改候选py/json/npz；ProcessPool每24/36任务重建，不用max_tasks_per_child。
- 原开发seed919260010..13已反复看过；919261001..008、919262001..008也开发用过。919270001..128都看过前72步，仍仅开发。ddaw/seed_panels.json里的validation16未跑完整未来，但不能当从未接触的新种子。
- 正式门控：每候选独占16新seed×双席×全33对手，每对手>=30/32、每席>=14/16、paired-seed平均胜差bootstrap95%下界>0，完整、无异常/超时；另16独占新seed确认。三候选需实质差异。正式门控与确认尚未使用，goal保持active。
- 旧上下文：NEXT_STEPS_pre_ddbk.md、NEXT_STEPS_pre_ddbi.md、NEXT_STEPS_pre_ddbe.md。当前本地数据最新日期的最近核验仍为9月18日，本轮没刷新远端；扩数据优先CLI/API，不输出凭据。
