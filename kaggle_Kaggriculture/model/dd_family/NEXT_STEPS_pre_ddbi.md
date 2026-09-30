# 当前研发接续：ddbh 已完成，下一版 ddbi

目标仍为3个有实质差异、通过全部33个y68对手冻结门控和独立确认的模型。当前 **0/3**。所有本轮进程已实际收到 exit_code=0，无活跃训练/评估。未提交Kaggle或推送Git。

## 本轮完成的实际工作

从固定整局轨迹切换到条件任务策略，建立ddbe/ddbf/ddbg/ddbh，新增32条完整开发比赛。12次保存动作的精确诊断重放不算新独立比赛。完整说明见 TASK_DISTILLATION.md。

| 版本 | 同4开发seed双席y68v | 平均胜差 | 平均自身现金 |
|---|---:|---:|---:|
| ddbe | 0/8 | -183287.125 | 3.25 |
| ddbf | 0/8 | -88594.875 | 51641.25 |
| ddbg | 0/8 | -52478.5 | 42888.625 |
| ddbh | 0/8 | -61198.75 | 65952.125 |
| 既有ddam控制 | 6/8 | +10379.25 | 93094.25 |

全部新比赛完整、源码/模型hash与计划一致、计时预算非负。四版均失败，不扩展，不冻结。对局同seed不保证商店路径相同：官方杂草随机数消耗依农场空地变化，不能把差额全当固定世界下的单一机制收益。

## 实现和数据

- ddbe/main.py及后续版：状态到下一成功服务目标的候选排序，输出xy/action、独立数量回归，最短路径持续执行；不调用完整旧策略，不在推理读取源轨迹。
- 市场是共享自回归ExtraTrees模型；以真实成交为标签，输入只推进我方动作/此前订单的shadow，不读取本回合未来对手成交。零成交槽用BUY_SEED WHEAT 0保留占位。末尾STOP。
- compile_task_policy.py：官方引擎1.32.7重放Boey的21训练/7验证（沿用ddbd源seed切分）。6条测试仍未打开。20132逐步状态的farms/private/market/town精确相等。训练76303成功服务，89628查询含等待，5199数量样本，89205市场样本。
- task_policy_data/ddbe与ddbf位于候选外，含每源hash、源seed、数组hash、编译plan/manifest。两套是同28条数据的不同负采样，不是56独立源。
- 首次编译把回放version误当module_version而失败，未产样本；failed_schema_plan.json保留，后改为核验module_version=1.32.7。成功plan和manifest完整。
- train_task_policy.py/v2.py 用dd_family/.venv sklearn。goal_rank HistGradientBoosting二分类候选排序，quantity/market为ExtraTrees；导出npz，tree_runtime.py纯numpy推理，导出数值误差小于1e-6（实际约1e-14）。不是PPO/self-play/DAgger。
- ddbe模型100轮31叶，920个留出完整候选查询Top1=61.63%、Top5=91.09%；市场验证准确率57.53%。实际第一天取羊被预测WAIT，生产停摆。
- ddbf：compile_task_policy_v2.py强制非WAIT任务负例含WAIT；动作逆平方根频率权重上限8，前三日×4；400轮63叶，市场64树balanced。Top1=68.91%、Top5=92.61%，市场50.31%。修复初始取羊，但取放空转严重。
- ddbg：ddbf四模型原样，过滤已有同类物品再取料及刚取料原样放回；保留有效动物安置、日末返还。平均PICKUP从845.5降至288.875，HARVEST293.5升至387.25。平均自身现金下降，虽净胜差改善仍全负。
- ddbh：保留ddbg，每种种子库存限制为当前工人数，t718不买种子。平均现金上升、竞争胜差恶化，失败。
- ddbf/ddbg/ddbh共享四模型权重，不可按名字计作3个实质独立成功模型。

## 新的关键归因（下一版必须利用）

1. diagnose_task_execution.py及v2.py重放ddbf/ddbg/ddbh各4个开发seed席0。与原719步现金和双方终局奖励精确一致，所有交易/雇工/土地现金流守恒。输出diagnostics/{version}_{seed}_execution.json及两个manifest。
2. ddbg的4局买种子355/850/778/1544颗，实际PLANT230/373/191/421次。ddbh限库存后变306/138/204/356，PLANT297/129/193/354；种子囤积确实基本消除。
3. 但释放资金没有自动变成更优策略：种子919260010/11，ddbg买动物14/17、逃逸2/5；ddbh买40/46、逃逸30/24。前24日已逃逸25/15，不能解释成全部末期主动退役。采购、维护能力和任务选择不一致。
4. 教师Boey首日现金同样常只有1..24，不能单凭低现金判定预算错误，见ddbf_source_opening_cash.json。
5. 当前247维goal特征未直接编码consecutive_unfed、consecutive_unwatered、pending_care_bonus。源专家健康轨迹难以覆盖学生损坏状态，单纯增加树数/全局准确率不足。
6. 市场模型逐槽分类验证仅50%，存在大量WHEAT/FERTILIZER同回合往返；未证明这些往返完全无价值。净额化前必须审计教师实际现金贡献，不能直接删除后声称等价。

## 下一步 ddbi（尚未建立）

不要继续堆小阈值版本。优先把采购与可执行生产任务/维护负担连接起来：先审计源和学生的市场往返净贡献、动物采购到安置到维护/逃逸的链路，然后设计有状态的生产意图或资源承诺。新模型需补入可见的饥饿/缺水/照料积累与剩余成熟周期，并在学生偏离源轨迹时有可验证的纠错来源。仅增加存活不能当超越y68的证明。

可复用官方原语、任务标签编译器、四模型导出、评价driver；不能调用y68动作当训练标签。若用源队列或规则产生纠错标签，明确其弱教师性质，不冒称可查询原专家或DAgger。

- train_task_policy_v2.py当前硬编码28源/21训练/7验证、源manifest为ddbd；扩大教师池需要新脚本/新版本并检查seed隔离。
- token特征切片依赖尾部UT+11布局；扩展特征必须同步训练/audit并记录schema，避免静默错列。
- 不修改已评估候选。新版本模型/配置需要在正式评估前固定；evaluate.py snapshot会检查候选内所有py/json/npy/npz。

## 文件与运行

- 对比：diagnostics/task_policy_comparison.json；独立核验：diagnostics/{ddbe,ddbf,ddbg,ddbh}_development_audit.json。
- 模型验证：ddbe/training_report.json、ddbf/training_report.json；细分：diagnostics/{ddbe,ddbf}_teacher_forced.json。
- 编译Python：根.venv；训练Python：dd_family/.venv（sklearn，没有torch/xgboost/lightgbm/catboost）。全部只改dd_family。
- 新版例：OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python kaggle_Kaggriculture/model/dd_family/evaluate.py VERSION --run development01 --workers 4 --opponents y68v
- ProcessPool每24/36任务重建普通pool，不用max_tasks_per_child；有hardlink的数据只能原子替换，不可原地改。
- 旧上下文留在 NEXT_STEPS_pre_ddbe.md，尤其固定轨迹/作物反事实失败、旧控制、独立开发种子池。

## 验收边界

正式门控和确认从未跑。每候选独占16新seed×双席×33对手，每对手≥30/32胜、每席≥14/16、paired-seed均值bootstrap95%下界>0，无异常/超时；另16独占新seed重复确认。当前0/3，goal保持active。
