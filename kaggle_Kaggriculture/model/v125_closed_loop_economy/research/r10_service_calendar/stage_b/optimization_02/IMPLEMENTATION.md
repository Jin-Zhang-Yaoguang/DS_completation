# OPT02 实现范围

P1 已存实测完整plan/state及8次接口对照通过，但内部经济函数18.025442334秒仍未达到性能要求。本轮按已批准设计，只缩小完整校验成功后缓存与传递的证据对象；不减少服务、求解或独立重演，不改变劳动/现金准入规则。

新单文件 SHA为 `370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895`，CID为 `V125-R10-OPT02-PROTOTYPE`。其余P0/P1源码、附件及实验文件原位保留，P1源码副本在 `p1/`，身份见 `p1_preservation.json`。

`PlanRouteCache(..., evidence_mode="full")` 和 `route_admission(..., evidence_mode="full")` 默认保持完整审计路径。full保留P1的key材料、完整problem/certificate/verification缓存、deepcopy输出与自定义hook隔离；新增模式域检查不参与经营判断。静态选取full分支并去掉新增模式输入域检查后，route AST等于P1。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/route_admission.py:243]

生产接入只在context cache构造和route调用两处显式传 `production_compact_v1`。PARAMS、经济函数、原compact_result消费者和最终receipt写法均不变。mode不写进plan/st/receipt，避免改变既有诊断结果。

compact只允许原schedule/check参数均为None；显式hook组合返回 `COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS`。cache模式不同返回 `CACHE_EVIDENCE_MODE_MISMATCH`。私有cache由本次plan独占，模式不在内部切换；它仍是Python对象，不宣称能防止外部代码直接篡改cache内部。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/route_admission.py:267]

compact key绑定完整problem、三实现ID、admission语义版本、12人、mode及摘要schema；entry另保存problem摘要和相同身份。miss仍执行原scheduler、独立checker和全部后验守卫。全部通过才建立entry：checker_valid、12人/376费用事实、EOD溢出事实及4项stats（completed_service_count、delivered_goods、purchased_goods、terminal_shed）。完整problem、certificate、verification、逐服务/市场收据不存入compact cache。checker本身仍生成并验证完整结果。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/route_admission.py:209]

每个entry的产品、终仓、IDs和溢出字典独立创建；对外evidence再复制4项stats的商品字典，start_shed/reserved_shed/buy也另建小字典。entry不会通过proof/receipt泄露可变引用。hit核身份、schema、费用、终粮和零溢出，返回值不指回cache。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/route_admission.py:221]

仍在所有失败日通过后一次commit staged；中途失败不提交已成功日。未增加负缓存、跨plan缓存、lazy规则、限额截断或提前现金拒绝。legacy_fields_unchanged深拷贝保持原样。compact首次仍生成完整checker日志，本轮只减少后续复制与驻留，尚不知实际省时幅度。

静态检查20/20：calendar、scheduler、checker和inliner字节同P1；P1→P2仅route/cache及两处integration函数改变，新增3个摘要helper；45个R9函数中44个同源，经济函数保持P1原样。所有差异另存 `.diff`。

本轮候选定义加载、new_state、内部经济、完整agent、solver、checker、engine均0。静态检查不是等价或性能实测。根后续可用已存P1完整输出作参照，只运行登记P2控制；无需重跑P0/P1。目标仍是完整plan/st和所有计数逐值相同，不忽略诊断差异。
