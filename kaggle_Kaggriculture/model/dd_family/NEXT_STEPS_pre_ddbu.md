# 当前：ddbo至ddbs均已完成，0/3，下一版本ddbt

目标3个实质不同、全33个y68对手门控并独立确认的稳定胜者，goal active。只写dd_family，未提交/推送。正式门控与确认从未使用。

## 活跃句柄

没有已知活跃进程。全部训练/对战/诊断均已收到exit_code=0；不要重启旧session。最近98772(ddbs对战)、5612(精确执行)、90816(空闲归因)、12244(采收浇水归因)已结束。ddbq62614、ddbr5569以及旧ddbo/ddbp所有句柄也已结束。

## 本轮完整结果

固定4开发seed919260010..13 ×双席 × y68v：
- ddbo 0/8，cash33993.25，margin-104381.25。
- ddbp 0/8，cash6759.25，margin-112900.875。
- ddbq 0/8，cash34312.25，margin-123733；源教师每日用工预测新增64树MAE.74104，彻底消除四席0有钱有资产却无HIRE的日子，但未改善竞争力。
- ddbr 0/8，cash45746，margin-84007；保留ddbq五权重，只在PASS时选原rank里有物资/日内可达/未认领的维护和采收。8局PASS19614→7151，四席0逃逸全0，仍全负且弱于ddbj。
- ddbs 0/8，cash79233.125，margin-42847.25；比ddbj现金+10619.875、胜差+2577.125，仍全负。
- 以上audit_option_development.py均完整/hash不变/预算非负，diagnose_task_execution_v2.py四席0现金和终局精确、守恒，registry已失败登记。

## 为什么转ddbs

- audit_crop_replacement.py ddbo ddbp：只有ddbo seed010有2株未成熟麦被DIG，其余近乎无此问题，不支持频繁拆作物是主因。
- audit_idle_jobs.py ddbq：9807个PASS，9058无任务，其中7081有可达服务（重叠机会，不是独立工作量或利润）。
- ddbr回退有局部用工价值，因此核对更强的ddbj：5362个PASS全部对应旧main.py的token0统计；3285次有可达服务。旧日志无goals，诊断有显式代码语义和count一致断言，不把缺字段自动当无任务。
- ddbs index70 parentddbj：四权重不变，不用M&M用工头/宏生产/维护强制；只PASS后按原rank选择可执行服务。原子FEED必须手持WHEAT，不能假称会返仓。CARE需已喂养且晚于今晚还有兑现日，第29天不启用fallback。
- 新runtime跳过叶子仅等价计算优化；ddbs四模型1/63/64/批量输入与父版逐位一致；check_service_idle_transfer.py通过资源/时限/去重/CARE/权重检查。

## 接下来

1. 不重复这些8局。ddbs已完整审计，无晋级；registry next_version=ddbt，尚未创建。自身现金提高不能掩盖0/8。
2. 新证据：ddbs席0空闲且有可达服务从父版3285→544，但仍逃逸5/12/3/3、未浇植物日383/158/350/308。吞吐改善尚未补足收益差距。不要继续无限叠加“存活/有工做”规则，也不要重复大扫固定原型或单次品种替换。
3. audit_harvest_water.py ddbj ddbs已结束：非持续作物采收991/777次，漏当天增产浇水只有1/5次，额外单位上界2/5。规模太小，不作为下一主版本；诊断未执行反事实，不能称利润。
4. 下一可研究方向：从学生实际到达的状态，用官方动态续局的终局现金/胜差给**协作计划或候选排序方式**提供价值监督；初始化和候选仍来源于replay蒸馏，不用y68动作作标签。不把静态预测精度或局部服务数作为目标。先设计一个小而可归因的对照，再扩数据；避免重复已有单次作物替换搜索。
5. 如果用日初分支，可复用diagnose_terminal_guard.py的官方前缀精确重放办法；Agent每日goals/previous清空，日初可新建，但需逐步验证无干预续局等于原终局。中途分支必须恢复Agent持久状态，不能擅自清零。任何分支结果都不是完整候选计时/竞技证明。学生只读取合法obs，模拟器未来/seed不能进入特征。
6. 目标0/3保持active，不complete、不blocked。没有外部阻塞。后续报告仍明确不等于达到3个稳定胜者。

## 固定边界

根.venv官方引擎1.32.7，dd_family/.venv sklearn。不用max_tasks_per_child，长池分批重建；候选运行时不改py/json/npz；hardlink数据不原地改。正式每候选独占16seed×双席×全33，每对手30/32、每席14/16、paired-bootstrap95%下界>0，无异常超时，再独占16seed确认。三模型实质不同；同权重执行修补不凭版本计独立者。

强控制ddam20开发seed双席24/40、mean+2104.50仍不稳。M&M源146train/40val（29test没开）；ddbp70/22按训练多数开局筛，非按收益筛。Boey21train/7val（6test没开）。y68只动态评估，不读取动作训练，不可当可查询教师。旧大扫固定整局原型/单次作物替换不重复。MM_OPTIONS.md / PRODUCTION_OPTIONS.md / NEXT_STEPS_pre_ddbo.md有前文。无memory文件引用，无需memory citation。
