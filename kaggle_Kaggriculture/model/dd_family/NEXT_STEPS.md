# 当前：ddbv–ddbx完成且失败，下一版本ddby，0/3

目标active：3个实质不同、全33个y68门控及独立确认稳定胜出的模型。唯一写目录dd_family；没有外部阻塞，没有活跃进程；未提交/推送。不要complete/blocked。上一turn真实新增23局完整对战+1异常中断，及因果特征/导出/官方执行审计，属于进展。

## 最新版本与结果（同919260010..13双席对y68v）

- ddbu：旧全局压缩+16维工人状态，0/8，cash4.5，margin-182369.125。
- ddbv index73：每工人加当前格与N/S/E/W邻格的105维状态，其余相同。0/8，cash605.125，margin-159972.875。
- ddbw index74：冻结ddbv权重，按合法token及共享影子资源选最高概率单位请求。仅完成7局、0胜；919260013席1原始HIRE过多导致count>16 assertion。DEVELOPMENT_ERROR，不把7局均值当8局或把缺失当输。
- ddbx index75：同权重，在市场阶段对HIRE按16模型槽预留容量，即当前units+发出的HIRE<=16；即使订单资金不足也保守占名额。完整0/8，cash1358.875，margin-150245.125。DEVELOPMENT_FAILED。
- registry next_version=ddby，尚未创建。三个变体尤其ddbv/ddbw/ddbx相同权重，不算三个独立模型。
- ddbx与ddbw原7局：六局全动作/现金/终局同；919260013席0只有step429等两帧动作不同，现金及双方终局同。最初“七局动作全同”的检查被assert否定，已经精确记录，不能重复错误结论。

## 这轮确证了什么

- prepare_neural_local.py从neural_joint_data原始x派生局部105维：global[0:175], board[175:2275]reshape100x21, units[2275:2531]reshape16x16，坐标rint(*9)。未存在单位全0，边界通道0=1。neural_local_data/{train,validation}_local.npy，形状N,16,105。40源状态与contract完整units[:,16:] float16精确。
- 原146train/40validation/29test不变，29test未读。104974/28760帧，725原始请求类，28未知验证有效请求不计CE并报告。标签未改变，没有y68训练标签。
- ddbv：2531→384→192编码器不变，GRU输入96→201（previous64+slot16+unit16+neighbor105），hidden192。1460469参数；相同AdamW/cosine/最多20epoch/patience5，实际18轮96.75秒，选13轮。验证CE.953986，准确率67.7969%，teacher-forced整回合9.9965%。ddbu选9轮39.4667%/2.7851%。不能当竞技胜率。
- ddbv PyTorch/NumPy teacher-forced和自主前缀各1664 argmax全同，最大误差1.335e-5；16源线上encoder与训练输入精确。
- 512固定验证状态自主回合内前缀：ddbv整体66.62%，移动47.22%，维护88.87%，采集71.51%，生产56.30%。销售精确请求6.19%含数量，不能等同方向准确率。仍给真实环境状态，不是自主闭环。
- ddbv真实919260010席0：1198次PLANT，1163被官方解释器转PASS（共享种子不足），35进入单动作函数/32改变状态。WATER114/89，FEED49/11。局部特征有实际作用，但采购与播种组合不一致。
- ddbx四席0×719：单位影子推演后的自身farm和private，与官方_process_market入口逐元素一致；全部播种预算和HIRE容量通过，现金/双方终局exact。
- ddbx919260010席0所有非PASS请求都改变状态；PLANT117/117，WATER428/428，HARVEST94/94，FEED26/26，无原子取消，但仍只有4366现金。可执行≠生产规划有效，继续堆合法性不是主要方向。
- ddbv/ddbx完整8局都719步且预算通过，最大单步含初始化.02663/.01729秒，所有候选hash不变。ddbw异常原封保留。

## 下一研究方向（尚未实施）

优先研究时间记忆/持续任务目标，先归因再动手。当前模型每个环境回合重置GRU，只在26个动作槽之间传播；既没有跨回合隐藏状态，也没显式之前动作/目的地。局部维护已较容易，但移动约47%，自主生产仍崩，支持检验“持续意图不足”，尚未证明为唯一原因。

一个可控的ddby候选：在ddbv局部特征模型上加入过去4个回合、同一工人的已发动作编码（严格左移，日初及新雇工清空），训练仍原教师原切分；推理用自己的历史，不得偷读teacher历史。市场槽可另显式定义历史，但不要不加说明地混用。过去动作只是可观测行为历史，不是教师身份标签。需先核验无跨episode/跨日错位、teacher历史与自己历史评估区别；完整对战最终裁决。也可先从现有轨迹审计移动反复和维护遗漏，再决定具体结构。

ddbx是当前神经执行基底，权重从ddbv继承；较强竞技控制仍是旧ddam（原4seed双席6/8,+10379.25；20seed双席24/40,+2104.5），不能把当前弱神经版当新强基线。正式门控未用。

## 实现文件

- neural_local_torch.py / neural_local_runtime.py / train_neural_local.py：ddbv专用训练与导出；不要覆写其数据/权重。训练脚本目前硬编码ddbv，下一版需另存或正确参数化新脚本。
- prepare_neural_local.py已完成，不重跑（目录exist_ok=False）。数据旧x2531不动；训练输入拼成4211，但global encoder只看前2531，局部序列从后1680取。
- check_neural_local.py已经完成，numerical parity不等于竞技。
- compare_neural_prefixes.py ddbu ddbv：固定512状态，输出diagnostics/neural_prefix_ddbu_ddbv.json。旧脚本通过GRU输入>96推断局部类型，若以后加历史维度需要显式扩展，不能原样误用。
- build_neural_guard.py创建ddbw；ddbx是保存原7局后新复制、仅HIRE容量遮罩修改。ddbx/main.py是当前实际执行代码。父源hash存parent_provenance.json。
- audit_neural_requests_v2.py：任意version/seed直接hook实际官方单位调用。v3另记整回合播种预算。v3输出与v2同名，因此仅对新版本调用，别覆盖旧证据。
- audit_neural_guard.py ddbx：4席0官方市场前状态与影子资源精确核验。
- diagnose_task_execution_v2.py ddbv：4席0现金守恒与终局exact；其中successful_services是影子模拟，原子PLANT有提前取消时不能作为实际成功数。实际调用计数优先v2/v3直接hook。
- NEURAL_JOINT.md有完整历史；diagnostics/neural_family_comparison.json有结果。NEXT_STEPS_pre_ddby.md保存ddbu结束状态，NEXT_STEPS_pre_ddbu.md更早路线。

## 进程全部结束，不重启

20124局部数据，38598训练，64926数值检查，46482前缀诊断，57695 ddbv8局，6640实际请求，92394四现金重放，25459 ddbx8局，42885四资源审计，22483实际请求，均exit0。
70264 ddbw评估exit1，明确一局异常，已由新版本ddbx完整对照，不续写旧run。
上一turn所有句柄也已结束。当前无后台任务。

## 不变边界

唯一写dd_family；旧数据有hardlink不可原地修改。根.venv官方kaggle-environments1.32.7；dd_family/.venv有torch2.14.0/MPS和sklearn。训练可用GPU，评估是NumPy无需torch。禁止max_tasks_per_child；普通进程池分批重建。候选运行时不能改py/json/npy/npz；新修改另版本或另新研究源。
正式每候选独占16seed×双席×33，逐对手>=30/32、逐席>=14/16、paired bootstrap95%下界>0，完整预算/无异常；另独占16seed确认。三模型须实质差别，不能把同权重修补当多个。y68只动态评估，不能读动作生成学生或训练标签。
无memory使用或更新，无需memory citation。goal保持active，失败不是blocked。
