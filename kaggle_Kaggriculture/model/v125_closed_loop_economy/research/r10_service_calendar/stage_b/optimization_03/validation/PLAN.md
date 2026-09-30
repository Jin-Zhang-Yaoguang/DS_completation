# P3 有限验证预登记

仅对五份已打开人工输入各一次默认 new_state/economic_plan_prefix：day8 的 funded/zero × 两席，以及 day3 在途动物且原 R9 许可 24 MELON 的 seat0。五次均不加 profile，120 秒保护只保留完整诊断，仍逐次按 1 秒要求判断。6 次定义加载=纯helper独立1+经济各独立5。P0/P1/P2/R9均不重跑，完整agent/engine/新完整比赛0。

经济中的 route_attempts 每帧至多1，合计至多5；日solver/checker各至多110=4×21+26。计数读取 receipt.r10_future_route.counts；无route且route_attempted=false、无新rescue许可时空字典才可解释为0。route_attempted=true必须有明确route_attempts=1，日solver可因绑定检查早拒而为0。缺失审计不能伪造0。只使用原生产审计，不在计时中插入profile或其它监控。

真实生产helper纯序列固定8 select、3 fail、7 key：A失败→同帧拒绝→跨日B→出现低分未试C优先→同帧拒绝→后续帧新轮A→另一seat独立A→原seat再次返回未认证A提案。key测试玩家隔离、跨日/价格/单位位置稳定、目标tile kind变化。全程无solver；最后一步只说明返回未认证提案，不声称真实重新求解或已批准。所有原offers须不变，返回q必须是原元素。

四个day8旧参照完整plan/state都为0 cheap许可。若本次未批准rescue，将按旧冻结normalizer的同一JSON表达精确比较所有原经营字段，不能声称原始Python类型已被旧JSON保存。明确新增plan字段仅rescue_expert、r10_route_feasibility_by_day、r10_effective_labor_feasible；新增receipt字段仅r10_rescue、r10_future_route；新增state为_r10_rescue_cycles（这是新轮转状态，并非可忽略的经营无关装饰）。这些新增字段全部另存、另核，不从原字段中选择性删值。

day3正例没有完整原内部state。原完整经济回执含24个许可；market_intents/unit_investment_intents是旧完整agent随后补入，因此只从经济回执比较中排除这两项。必须核cheap_accepted_count=24和原24许可的项目、顺序、位置、真实原报价值；未批准rescue时所有经济回执原字段应相同。批准1个rescue时保留全部差异，分别报告cheap不变字段、24原许可和唯一新增许可，不能把后续资金/劳动/土地变化说成原回执全等。

成功rescue还需原当前日劳动无失败、future proof覆盖所有原失败日、完整实际田块/在途/旧合同/cheap许可来源数量闭合、原资金前缀通过。无profile下能从保存proof与源分支核对的事实明确注明；不能从现有回执唯一重建的同trial中间状态标PENDING。不因未命中成功后现金门而捏造该分支已覆盖。

所有源、旧参照、fixture和harness先锁SHA，根签独立release后才可单轮执行。错误/超时/差异保存，不重复择优，不扩大旧规则suite。
