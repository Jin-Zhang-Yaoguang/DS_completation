# 当前接续：ddbj 已完成，下一版 ddbk

目标仍为3个有实质差异、经全部33个y68对手门控与独立新种子确认的模型。当前 **0/3**。本轮所有进程均已实际收到exit_code=0，无活跃编译/训练/评估。只改dd_family；未提交或推送。

## 本轮完成

1. `audit_teacher_roundtrips.py`：21条Boey训练源，各做原请求重放、有效成交序列重放、抵消同回合WHEAT/FERTILIZER匹配往返量的反事实重放，共63次。有效成交序列与原719步farms/private/market/town精确相等，现金流守恒。
   - 匹配往返71117单位；按原均价分摊的价差合计1487.35，平均70.83。这是会计分摊，不是因果收益。
   - 抵消后自身现金平均-8411.476、中位数-3794，14/21下降、7/21上升，最差-73637。固定对手回放，不是动态竞技。故没有将净额化当等价压缩，也没有随意删掉这些订单。
   - `teacher_market_audit/summary.json`、每源 `*_fills.npz`、`*_audit.json`；prototype编号是ddbd/training_manifest.episodes训练数组索引。
2. `ddbi` 新特征重训四模型：同21训练/7验证，6测试未打开；目标特征247→325，市场157→218。加入连续饥饿/缺水、pending_care_bonus、产出日历/剩余次数、当前货值、其他工人位置/持料、此前已承诺的目标计数。保留ddbh取放循环和种子库存约束。
   - `compile_task_policy_v3.py`，`train_task_policy_v2.py ddbi`。所有监督标签与ddbf逐项一致，见 `diagnostics/ddbi_label_alignment.json`。goal token仍在末尾[-55:-11]，空间尾11维；schema在候选内。
   - 留出920完整候选查询Top1=70.652%、Top5=93.804%；市场成交标签验证准确率50.544%。不是竞技成绩。
   - 原4开发seed×双席×y68v=8局，全负，平均胜差-58785.5，自身现金均值62260.5。
3. `ddbj` 保持ddbi目标/数量模型不变，仅把市场监督从实际成交改为原请求意图。21训练源96256请求中41584零成交，43.2%。原WAIT替代可能丢失条件订单意图，这是受控假设，不宣称已证明唯一根因。
   - `compile_task_requests.py` 保存请求token/数量，teacher forcing影子状态只应用我方请求可成交部分，prefix保存已请求数量；不读未来对手结果。
   - `train_requested_market.py` 逐数组证明goal输入/标签与ddbi完全相同，并复制两套goal权重，只训练市场两模型。市场109769训练/35684验证行，原请求分类验证50.950%，请求数量R2=0.62977；与成交标签任务不同，不能直接比较准确率当胜负。
   - 推理保留当前未成交请求的槽位，禁止超过16工人，保留种子库存约束，不按可成交mask把未成交请求换成另一个动作。
   - 同面板0/8，平均胜差-45424.375，自身现金均值68613.25。仍低于ddam旧控制同面板6/8、+10379.25。两版均不扩展/冻结/晋级。
4. 两版各4seed席0保存动作精确诊断重放，共8次；719步现金和双方终局奖励相同，现金流守恒。ddbi逃逸5/3/20/5，ddbj为4/2/4/6；不能把存活改善当竞技证明。
5. `audit_goal_prerequisites.py`及v2：21源中，1101个下一成功任务查询因当前不可执行被标成WAIT；609缺种子/仓库物资，492田块前置条件或其他条件不满足。详细输出 `diagnostics/task_prerequisites{,_detailed}.json`。

本轮新增 **16条动态开发比赛**，63+8次诊断重放不算新独立比赛。所有开发候选hash未变、完整719步、预算非负。正式门控/确认从未使用。

## 新发现：下一版不应只继续加字段或调分类权重

当前分解只允许“现在可执行的服务目标”。它把“先采购/建造/播种，随后才能做的任务”与“没有任务”折叠为WAIT，采购模型往往看不到真正需求。

609个资源等待：PICKUP SHEEP73、COW116、WHEAT149、GOOSE8、FERTILIZER43；PLANT缺MELON28、STRAWBERRY83、CARROT64、WHEAT45。

492个其他等待的主要类型：目标空地上WATER161、FEED75、PLACE36、CARE26；目标仍为PLANT时新PLANT58、BUILD_PASTURE25；LOCKED上PLANT44；空PASTURE上CARE22/FEED22。详细列表在audit输出。说明既有采购依赖，也有跨工人建造/播种/安置/扩地依赖。少数WATER:PLANT等仍需具体检查，不能简单按kind断言全部根因。

这些只是源标签分解的覆盖缺口，不证明1101次WAIT都错误，也不证明修复后可赢。

## ddbk 建议路线（尚未创建）

研究带前置依赖的生产意图：让高层先输出“某格安装何种动物/种何种作物”等目标，将BUY→PICKUP→BUILD/PLANT→PLACE→FEED/CARE/WATER串成依赖任务，给采购明确的资源承诺；工人调度可以提前知道另一工人正在建造/播种的目标。

- 不要只把当前非法动作全部解禁。既有1101等待中492是跨工人田块转移，单独放宽PICKUP/PLANT物资约束不够。
- 仅用下一服务PICKUP无法告诉其他工人未来安置位置；可能需要从实际PLACE/PLANT追溯采购/搬运/建造链，形成带位置的高层选项。可参考旧 `compile_executed_animals.py` 的物品溯源/分组，但不能重新调用整套旧策略为新候选出动作。
- 这些高层意图是根据回放推断的监督标签，不能冒称教师内部真实计划。未来事件可构造标签，未来观测/市场/商店/对手私有状态不可入输入。协作特征只能由此前已输出的计划产生。
- 需要明确承诺数量、部分成交/部分取料、取消条件、到期、预算和维护容量；不能把资金释放再投入到无人维护的动物。先做标签与执行小闭环，再完整动态对局。
- 原始请求市场分支ddbj是当前这组参数化模型里更好的开发起点，但仍大幅弱于ddam。ddbi/ddbj共享单位模型，不能因两个名字计作两个实质独立成功模型。
- 另一待验证方向是市场请求顺序/历史：现有prefix只有计数与数量之和，没有最近token序列；不应未经对照认定这是主要原因。

## 文件与环境

- 本轮说明 `MAINTENANCE_DISTILLATION.md`；对比 `diagnostics/maintenance_task_comparison.json`；hash和计时核验 `diagnostics/{ddbi,ddbj}_development_audit.json`。
- `task_policy_data/ddbi`与`ddbj`，编译manifest按all_splits筛除test后的28源索引；不要把这个index和teacher_market_audit的21训练prototype index混用，按source path/hash/seed匹配。
- 根 `.venv/bin/python` 做官方模拟和编译；`dd_family/.venv/bin/python` 训练sklearn。未安装torch/xgboost/lightgbm/catboost。
- 候选里py/json/npy/npz在运行时不可修改。文件复制不要原地改hardlink；ProcessPool每24/36任务重建，不用max_tasks_per_child。
- `evaluate.py VERSION --run development01 --workers 4 --opponents y68v` 为原4开发seed双席8局。不要复用run名覆盖，正式seed不要用于调参。
- 当前本地官方daily目录仍只到2026-09-18，已核实没有19/20；source_56216119_episodes_20260919.json只是另一提交的episode元数据列表，不是Boey新轨迹。若扩数据优先CLI/API，不读凭据到输出。
- 旧上下文：NEXT_STEPS_pre_ddbi.md、NEXT_STEPS_pre_ddbe.md。ddam全20开发seed双席24/40，ddax24/40均值+2402.95，仍未稳定。

## 目标和门控

每候选独占16新seed×双席×全部33对手，每对手≥30/32、每席≥14/16，paired-seed均值bootstrap95%下界>0，无异常/超时；再另16独占新seed确认。三模型需实质差异。当前0/3，goal保持active，禁止按离线指标或少数开发局改写成功标准。
