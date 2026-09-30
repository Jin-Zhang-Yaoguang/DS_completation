> 2026-09-09：本文件保留历史研究协议与机制证据，不是当前金牌候选名单。当前名单仅以 [golden_model.md](golden_model.md) 和 [registry.json](gold_candidates/registry.json) 为准；V120、V123 活动目录已淘汰删除。

# Kaggriculture 原创机制登记簿

更新时间：2026-08-29

本文件只登记主要因果机制，不按版本号数量计数。同一机制的阈值、窗口、step、产品白名单或重新打包版本都属于同一谱系。

## 历史原创机制

| 身份 | 代表版本 | 主要因果杠杆 | 当前证据 | 本批角色 |
|---|---|---|---|---|
| `OG_DEMAND_TIMING` | V20 | 商店需求发生前后的商品出售时机 | 已有独立确认 | 固定原创代表 |
| `OG_PRODUCTION_ROUTER` | V21/V29 | 完整生产专家的阶段切换与安全执行 | 已有独立确认；V29 为行为别名 | 固定原创代表 |
| `OG_OPPONENT_PREEMPT` | V32 | 对手公开结构相似度驱动的多步出售抢跑 | 已有盲确认 | 固定原创代表 |
| `OG_TERMINAL_LOGISTICS` | V54 | 终局物流、回收和无价值动作旁路 | 已有盲确认 | 固定原创代表 |
| `OG_MARKET_MICROSTRUCTURE` | V66 | 商品净 margin 驱动的同回合市场队列规划 | 已有盲确认 | 固定原创代表 |
| `INCUMBENT_STACK` | V76 | V20/V21/V32/V54/V66 等机制叠加后的最强冻结完整栈 | 已有盲确认和官方复算 | 强度基线，不单独计原创配额 |

## 2026-08-29 五谱系研究组合

| 槽位 | 预注册谱系 | 主要因果杠杆 | 与历史最近邻 | 状态 |
|---|---|---|---|---|
| A | 商店需求—生产契约 | 未来需求向量与库存缺口共同选择完整生产专家 | V20、V21 | `V77 REJECT_DEVELOPMENT`：POU −11.20pp，弱专家代差不可补偿 |
| B | 对手信念—最佳响应 | 对手公开路径的概率信念与低置信回退 | V32 | `V78 REJECT_DEVELOPMENT`：POU −51.56pp，资产存量无法预测下一市场槽 |
| C | 现金流—尾部风险 | 破产、锁仓和终局兑现风险选择增长/保本/清算专家 | V54 | `V79 REJECT_DEVELOPMENT_INERT`：POU 0，`0/768/0`，真实样本无联合偿付冲突 |
| D | 空间物流—产能瓶颈 | 拓扑、运输和劳动力占用选择物流/生产调度专家 | V54 | `V80 REJECT_DEVELOPMENT`：总体 POU −2.21pp；赢 V76 但跨谱系退化 |
| E | 共享市场—商品级 MPC | 商品级反事实收益和对手市场响应选择买卖专家 | V66 | `V81 REJECT_DEVELOPMENT_AND_LATENCY_GATE`：POU −33.40pp，且 P99 为父代 1.451× |
| F | 价值感知任务编排 | 公开需求吸收能力约束闲置维护专家 | V20、V80 | `V82 REJECT_PRECONSTRUCTION_SYNTHETIC`：WATER/CARE 无收益效果，FEED 只有负翻转 |
| G | 联合棚容量—现金仲裁 | 现金与可部署容量在动物扩张、生产投入间仲裁 | V66、V76 | `V83 REJECT_PRECONSTRUCTION_INERT`：48 局、34,512 次决策中所需相邻结构为 0 |
| H | 首店条件完整专家路由 | 首个公开商店选择整局生产专家 | V21 | `V84 REJECT_PRECONSTRUCTION_DOMINATED_EXPERT_POOL`：8/8 商店 regime 均由 V76 排名第一 |
| I | 肥料副产品后置控制 | 父代 PASS 后追加肥料收集 | V80、V76 | `V85 SAME_LINEAGE_PATCH_NOT_COUNTED`：Confirmation POU +7.42pp，但完整调用 V76 agent，不是独立模型 |
| J | 多时间尺度需求—任务 MoE | 商店制度 Router × 三生产蓝图 × 事件恢复 Router × 商品市场 Router × 自有安全执行器 | V21（仅蓝图形态最近） | `V86 REJECT_PRECONSTRUCTION_ARCHITECTURE_DESTRUCTIVE`：原创实现成立，但 full 比 ablation −11.46pp、对 V76 0% |
| K | 跨团队行为簇 continuation MoE | 多团队 Replay 行为簇 → 首分歧/置信度 Router → 整段 continuation 专家 | V17 portfolio（但专家来源、Router 状态与对手制度均不同） | `V87 REJECT_PRECONSTRUCTION`：960 局零错误，但 5 条路线仅 lucaskna 达标；专家池 1/3 |
| L | 参考轨迹—状态管道 MoE | 强参考轨迹定义状态管道；偏差 Router 选择资产、物流、库存或现金恢复专家，再回归原轨迹 | 最接近控制论 option/recovery，不继承历史完整策略 | `V88 REJECT_DEVELOPMENT_TAIL_RISK`：POU +11.52pp、MCU +10.94pp，但灾难率恶化 +3.39pp |
| M | 日级案例检索—Option MoE | 从同一高分策略的多场状态—动作轨迹学习日级专家库；日边界最近邻 Router 选择并承诺 24 步 option | 案例推理/非参数 episodic control，与单轨迹状态管道不同 | `V89 REJECT_PRECONSTRUCTION`：MCU −22.40pp、灾难率恶化 +15.10pp，跨日共同适配被破坏 |
| N | 因子化浅树行为克隆 MoE | 首店 Regime Router → 角色条件单位动作树 / 市场动作树 → 冲突安全执行器 | 学习型状态策略，不检索或拼接历史动作段 | `V90 REJECT_PRECONSTRUCTION`：OOF 单位 91.3% 但闭环 0%，162,002 次动作丢弃导致全局崩溃 |
| O | 置换不变劳动力匹配 MoE | 参考任务集合 → 当前位置/库存/合法性代价 → worker—task 全局匹配 → 专家任务执行 | V80 仅做 PASS 工作窃取；本谱系重建整组 hand 身份分配 | `V91 REJECT_PRECONSTRUCTION`：重分配覆盖 192/192 局，但 MCU −1.04pp、`0/190/2`，任务不可交换假设被证伪 |
| P | 事件驱动期权—资源 Petri 网 MoE | 资源 token、生产前置与事件时钟定义可达任务图；Router 只在事件边界选择可证明可完成的生产期权 | 与轨迹模仿、案例检索和固定蓝图均不同 | `V92 REJECT_PRECONSTRUCTION_TAIL_RISK`：MCU +4.69pp、`9/183/0`，但灾难率恶化 +6.25pp |
| Q | 语义作物组合—空间动作原语 MoE | 空间动作只作为无商品语义的 motor primitive；需求、价格与剩余成熟期 Router 独立选择粮食/速生/高价/终局作物专家 | 与固定生产蓝图和市场时点控制不同 | `V93 REJECT_PRECONSTRUCTION`：11,712 次改种导致 full 0%，成熟期与后续动作不可解耦 |
| R | 市场交易依赖图 MoE | 把同回合市场意图编译为库存变现、固定资本、生产投入和扩张交易 DAG，由可行性 Router 拓扑执行 | V66 只做局部相邻重排；V81 做短视界 MPC | `V94 REJECT_PRECONSTRUCTION`：MCU −28.65pp；可支付顺序破坏竞争价值 |
| S | 路径不变控制屏障 MoE | 固定空间生产路径上，按动作前置条件选择原任务、同位置修复、资源封顶或安全空闲；禁止任何改道恢复 | V88 会主动空间回归，V92 会延期并重试任务 | `V95 REJECT_PRECONSTRUCTION_TAIL_RISK`：MCU +0.52pp，但灾难率恶化 +21.88pp |
| T | 座位优先权—稳健路线 MoE | 利用市场同槽 player-order 非对称性，在整局开始按公开 seat 选择稳健或高收益完整路线专家，不做中途拼接 | 与按商店/状态检索路线不同 | `V96 REJECT_PRECONSTRUCTION_TAIL_RISK`：MCU +2.60pp、`5/187/0`，但新 seed 灾难率恶化 +9.38pp |
| U | 对手市场冲击—槽位节奏 MoE | 从连续公开 market inventory/price 冲击估计对手上一回合买卖方向，Router 选择同槽竞争、错槽等待或需求边界抢跑专家 | V32 预测路径距离；V66 只看自身净 margin | `V97 REJECT_PRECONSTRUCTION`：预测 OOF 98.04%、MCU +3.13pp，但总分 59.90%、灾难率恶化 +18.75pp |
| V | 随机扰动—状态图生产 MoE | 当前地块即时生成除草、播种、浇水、收获任务图；商店 Router 选择作物专家 | 与 Replay 路线和父代策略均独立 | `V98 REJECT_PRECONSTRUCTION`：错误把 yield_units>0 当成熟，过早 HARVEST 导致 full/ablation 均 0% |
| W | 成熟时钟—Temporal Petri MoE | 作物年龄、首次成熟日、持续产出间隔和寿命构成时间 token；阶段 Router 选择建田、维护、成熟收获、再播种专家 | 与 V98 的即时反应图不同 | `V99 REJECT_PRECONSTRUCTION_ECONOMIC_SCALE`：成熟机制生效但平均仅 3,067 金币，面板 0% |
| X | 因子化可行域—专家仲裁 MoE | 日边界分别以拓扑状态和资产负债状态选择生产动作专家与市场动作专家；可行域屏障阻止跨域不兼容组合 | V89 选择整日单案例；本谱系按动作域独立仲裁 | `V100 REJECT_PRECONSTRUCTION`：四路线均覆盖，但 MCU −16.15pp、`0/161/31` |
| Y | 合法性共识否决 MoE | 冻结强公开专家合法时保持完整动作；仅在动作非法且至少两个独立专家同意同一合法替代时恢复 | V95 用手写局部修复；本谱系以专家共识作为反事实证据 | `V101 REJECT_PRECONSTRUCTION_INERT`：30,558 次非法动作中共识恢复为 0，`0/192/0` |
| Z | 公开比分—效用状态 MoE | 公开双方现金差、我方即时可变现资产与剩余期限路由增长、追平、领先锁定市场专家 | 历史机制优化生产/市场利润，本谱系直接优化胜负效用状态 | `V102 REJECT_PRECONSTRUCTION`：灾难率降至 0，但 MCU −68.23pp，提前清仓摧毁价格与复利 |
| AA | 供给冲击—商品执行 MoE | 逐商品市场库存相对基准供给与城镇消费时钟路由稀缺立即卖、过供给等待、需求后释放专家 | V20、V33、V34 | `V103 REJECT_THINKING_SAME_LINEAGE_PATCH`：把需求时点控制改成实时库存条件，仍是已有市场出售时机谱系，不构造、不消耗对局 |
| AB | 全局需求图—整局承诺 MoE | 完整已解锁商店商品超图和席位条件公开状态，在同步边界选择一个协同完整的生产路线专家并整局承诺 | V21 只做固定阶段切换；V84 只看首店 | `V104 REJECT_SOURCE_QUALIFICATION`：3,072 局，交叉验证 `0/384/0`、金币差 −30.23，无可学习优势 |
| AC | 轨迹委员会—共识 MoE | 多条强独立轨迹逐槽提出动作，共识动作构成主策略，分歧动作仅经公开价值与状态兼容仲裁进入 | V101 只对非法动作做共识恢复；本谱系由委员会生成全部策略 | `V105 REJECT_SOURCE_QUALIFICATION`：top-3/5/8 最好仍 −28.13pp，逐槽投票破坏时序契约 |
| AD | 保形支持域—Option MoE | 多参考轨迹定义状态支持域与不确定性；只在受支持状态承诺完整 continuation，否则进入独立保本 option | V88 是单轨迹确定性恢复；本谱系以多参考统计支持和风险覆盖为因果杠杆 | `V106 REJECT_PRECONSTRUCTION`：风险 OOF 可识别，但新面板风险 option 0 次、`0/192/0`，机制无得分贡献 |
| AE | 隐藏随机流后验—未来需求 MoE | 公开杂草与商店事件更新 episode RNG 后验，预测未来商店序列并路由完整生产专家 | 历史 Router 只响应已发生需求；本谱系预测未发生随机需求 | `V107 REJECT_PREDICTABILITY`：1,024 留出准确率 11.13%，低于 12.5% 先验 |
| AF | 进化式宏 Option 重组 MoE | 质量多样性搜索只在日边界重组完整 24 步生产 option，再由公开状态浅 Router 选择经留出验证的宏专家 | V89 按最近邻每日报例；本谱系以闭环反事实适应度搜索兼容 option | `V108 REJECT_OPTION_SOURCE_QUALIFICATION`：140 个整日变体均无胜负翻转，最好仅金币 +84.16 |
| AG | 相位同步有限状态 MoE | 从联合公开/私有状态推断生产潜在相位，由停留、正常、追赶专家重定时整组协同动作 | V88 固定时间轴后局部修复；V89 按日换案例；本谱系改变自动机相位而不拆动作 | `V109 REJECT_PRECONSTRUCTION`：RC2 full 82.29% vs 消融 84.90%，`0/187/5`，尾部 +12.5pp |
| AH | Fitted-Q 完整 Continuation MoE | 浅层 Q 模型只在日边界给完整剩余局 continuation 专家估值并承诺，禁止动作级/单日拼接 | V104 只在固定 step216 路由；本谱系学习多决策边界 option value | `V110 REJECT_CONTINUATION_QUALIFICATION`：140 条完整 continuation 均无翻转，最好金币差仍 −35.69 |
| AI | CVaR 策略组合 MoE | 共同前缀后，浅层下行风险价值模型在完整增长 continuation 与完整恢复 continuation 间一次选择并承诺 | V88 单策略确定性恢复；V106 规则触发保全；本谱系学习完整策略 option 的风险收益前沿 | `V111 REJECT_EXPERT_DOMINANCE_FAKE_MOE`：相对增长 +9.29pp，但比始终恢复 −1.04pp 且尾部更差 |
| AJ | 恢复专家流形 MoE | 多条完整生产 continuation 先投影到共享可恢复状态流形，再由需求图 Router 选择有 OOF 条件优势的完整专家 | 与 V104 的裸 continuation、V111 的二选一策略组合不同 | `V112 REJECT_EXPERT_MANIFOLD_BEST_EXPERT_DOMINANCE`：8 专家、1,024 局，Router 与最佳固定专家同为 93.75%，BEU=0 |
| AK | 契约式路径森林 MoE | 首店需求浅 Router 只在共享前缀边界承诺完整生产专家；滞后公开市场冲击只控制商品出售节奏 | V86、V90、V97、V21 | `V115 REJECT_PRECONSTRUCTION_BEST_EXPERT_DOMINANCE_AND_STATE_DRIFT`：672 局，full 8.33%，最佳固定 dairy 89.58%，BEU −81.25pp |

五个金牌槽位必须各自从 `strategy_parent=null` 的独立策略架构出发。V76 只用于强度比较，不能提供候选默认动作。一个候选只有通过静态/运行时无父代调用审计和原创性消融门，才把状态改为 `CONFIRMED_NEW_LINEAGE`；否则登记为同谱系补丁或淘汰，并另补新的原创槽位。
