# 当前：ddbu神经联合策略失败，下一版本ddbv，0/3

目标active：3个实质不同、全33个y68门控及独立确认稳定胜出的模型。唯一写目录dd_family。当前没有外部阻塞，没有已知活跃进程；未提交Kaggle、未推送git。不要complete/blocked。

## 本轮新增真实进展

- 完成较强控制ddam四败局经济/执行诊断、闲工肥料机会审计、146条训练源精确状态索引及雇工编号等价索引。后两者在真实四局均只step0/1有分支，day3以后为0。
- 原型35同时占满100格，不能只重排位置就减少土地。均是可行性否定，没有为这些不活跃方案浪费版本号。
- 实际创建、训练并测试ddbu，8局新完整动态开发；另4局精确现金重放及1局直接官方请求效果重放，不算额外独立样本。
- 全部说明、参数、限制在NEURAL_JOINT.md。

## ddbu结果

146训练/40验证，29test未读；104974训练帧，725原始请求类；输入2531，384/192编码器+192GRU，26槽回合内自回归。1399989参数，约72.9秒14epoch，验证CE选第9轮。没有跨回合隐藏状态。
训练标签是原始请求不是实际成交，未用y68标签。归一化仅训练集，输入没有seed/episode/teacherID。验证28个未知请求不计CE并报告。最佳验证已知请求准确率39.4667%，teacher-forced整回合2.7851%，不代表闭环胜率。

check_neural_joint.py：PyTorch/NumPy teacher-forced和自主前缀各1664动作相等，logit最大误差1.24e-5；16源状态encoder精确。ddbu/weights.npz SHA=15f53e0d0d4662dc4567cb7008a608a2ff55c3657323bcc62d52efb090e35988，约5.23MB。

ddbu/development01：919260010..13双席对y68v，0/8，mean_cash4.5，mean_margin-182369.125，719步和预算全过，hash不变。最大单步含初始化0.02575秒。registry状态DEVELOPMENT_FAILED，next_version=ddbv；ddbv未创建。

四席0 diagnose_task_execution_v2.py 重放现金/终局exact、守恒。该工具successful_services是影子逐单位推演，对原子PLANT可能不能当实际事件；本轮另audit_neural_requests.py直接hook官方_apply_unit_action，对919260010席0确认：PLANT252请求/12状态改变，WATER436/5，BUILD_PASTURE27/2，HARVEST4/0，无FEED/CARE，全部请求进入函数。不是导出失配或超时。

## 下一步已明确的结构假设

ddbv仅增加显式局部田块输入。当前GRU本地输入只有unit16维位置/库存，棋盘被全局2531→192压缩；它没有直接看到所在格及四邻格的105维特征。可以从contract.encode原本完整units[:,16:]取得；neural_joint_data目前只存units[:,:16]，须新建/追加独立数据文件，不能改旧数据/候选。

可直接从neural_joint_data的raw_x按global175、board2100、units256解析原始坐标与21通道board生成16×105，边界通道0=1，与features.py中的五方向顺序(0,0),(0,-1),(0,1),(1,0),(-1,0)严格对齐；用原回放encoder抽样逐元素核对。

保持同教师、原始标签、切分及训练预算，先验证此架构单改动。训练端可复用neural_joint_torch.py/train_neural_joint.py的流程，但要参数化新版本，不覆写ddbu；runtime同理另存。保留原始请求语义，不在同版同时改legal mask、市场裁剪、任务规则。新模型仍需完整闭环，不能用准确率晋级。局部输入缺失只是待验证假设。

训练设备：dd_family/.venv已安装torch2.14.0，MPS可用，根.venv仍无torch但有官方环境1.32.7。新训练使用dd_family/.venv，推理导出NumPy后用根.venv evaluate.py。

## 进程都已exit0，不要重启

25831严格支持审计；16288雇工编号等价；37551安装torch；97153编译神经数据；53726 MPS前反向检查；15904训练；17420数值检查；17833八局开发；77769四现金重放；77179直接官方请求审计；76491临时原始动作查看。旧49084/90427/50751也结束。没有后台工作。

## 文件和协议

prepare_neural_joint.py -> neural_joint_data/{train,validation}_{x,y,mask,counts}.npy + vocabulary + manifest。训练原始源SHA全部来自task_policy_data/ddbo/manifest.json的已验证146train+40validation；不读29test。

strict索引prefix_policy_data/；worker等价索引prefix_policy_data/worker_orbit/，后者仅覆盖上界，工人重编号不保证共享资源顺序执行等价。新代码worker_orbit_support.py、audit_worker_orbit.py。

较强ddam旧20seed双席24/40、mean+2104.5，不是合格。此前完整固定计划重扫、单次作物替换、日期价值表等失败历史见README、NEXT_STEPS_pre_ddbu.md、ROUTING_VALUE.md，勿换名重复。

正式协议未使用：每候选独占16seed×双席×33，每对手>=30/32，每席>=14/16，paired bootstrap95%下界>0，完整/预算/无异常；再独占16seed确认。三模型需实质区别，同权重小修不可算多个。y68仅黑盒动态对手，不读取动作生成候选/训练标签。

不使用max_tasks_per_child。候选运行时不能改py/json/npy/npz；旧data有hardlink禁止原地修改。本轮没有使用或更新memory文件，不需memory citation。
