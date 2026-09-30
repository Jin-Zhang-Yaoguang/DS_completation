import datetime,hashlib,json,re
from pathlib import Path
B=Path(__file__).resolve().parent
D=json.loads((B/'online_summary.json').read_text());labels={56044732:'V41-RB',56044730:'V41-F',56036496:'V32',56033998:'V26-a53'}
ts=datetime.datetime.fromtimestamp((B/'submissions.json').stat().st_mtime,datetime.timezone(datetime.timedelta(hours=8))).isoformat()
lines=['# 最新四个提交审查与浅规则树框架修订','',f'线上评分快照：{ts}。以该次CLI查询按提交日期选取最新4个提交；公开对局清单分别冻结在随后一次CLI查询，未追逐查询后新增局。','',
'结论：采用浅规则树与同一个状态驱动调度器。V41两版的开局胜率值得继续观察，但仍是固定母带加条件修补；V32和a53的后段胜率已显著低于开局。四版均未证明2500或2900目标，均未形成目标所需的生产结构适应。','',
'本次读取287份去重公开对局，复用100份已有Replay，新增下载187份；不含4场Validation。287份均720状态，身份对应CLI提交的episode列表，规则配置SHA一致、module_version=1.32.7。终态均DONE且奖励可读；这不证明没有被引擎静默忽略的无效动作。没有运行候选agent或新对局，没有修改Claude工作树，没有提交Kaggle。','',
'## 线上结果','',
'|版本|提交ID|评分|公开W/L/T|纯胜率|前40局|41–80局|最近40局|',
'|---|---|---:|---|---:|---|---|---|']
def cell(x):return '—' if not x['n'] else f"{x['W']}/{x['n']} ({x['pure_win_rate']:.1%})"
for r in D['summaries']:
 v=r['verified'];lines.append(f"|{labels[r['submission_id']]}|{r['submission_id']}|{r['score']}|{v['W']}/{v['L']}/{v['T']}|{v['pure_win_rate']:.1%}|{cell(r['first40'])}|{cell(r['games41to80'])}|{cell(r['latest40'])}|")
lines+=['','V41不足40场的栏为全部已完成公开局，不能解释为完整40场样本。评分显示来自提交列表，不是终局金币；不同版本的对手、匹配时段和样本年龄不同，表内差异不是随机化A/B或直接对轰结果。','',
'V41-F在seat0仅2场（1胜1负），seat1为11胜0负；V41-RB两席分别9胜0负与5胜1负，均不足以证明稳定。V32两席39/62与38/60；a53两席41/70与34/67。','',
'对手开局BUY_PRODUCT WHEAT请求量≥20只是预先定义的可观察分组，不是对手实力或真实机制家族：a53在该组37/80=46.25%，V32为44/64=68.75%。对照组构成不同，不能由此精确归因于53对30的差异。V41-F尚无该类对手样本；RB只有3场。','',
'## 多样性：完整动作hash容易产生假象','',
'|版本|完整动作序列种数/局数|农民+工人指令序列种数|采购请求总量组合种数|单位指令与本版固定母带吻合率|',
'|---|---:|---:|---:|---:|']
for r in D['summaries']:
 lines.append(f"|{labels[r['submission_id']]}|{r['unique_full_actions']}/{r['verified']['n']}|{r['unique_unit_sequences']}|{r['unique_procurement_requests']}|{r['template_unit_match_fraction']:.3%}|")
lines+=['','采购组合只统计整季BUY_SEED/BUY_ANIMAL请求数量，不把请求当作真实采购或投放。单位吻合率比较每帧farmer/hands请求槽位，V41比较其包内_ACTIONS，V32/a53比较真正被内层使用的_V120_DISTILLED_ROUTE；分母为候选与模板槽位并集。它不是合法动作率或真实生产完成率。','',
'V32的122局完整动作hash全部不同，但采购数量组合只有1种；V41两版各自的工人整季指令序列都只有1种。这直接说明“每局动作hash不同”不足以证明生产自适应。','',
'## 系统与数据流','',
'V41-F和RB本地包的主文件只有第11行压缩动作数据不同，其余247行一致。主agent用day*24+hour索引_ACTIONS，复制farmer/hands/market；随后叠加动物护栏、LEAD、就地fill和价格回升追加卖单。没有按本局商店或对手产能重新生成基础生产计划。[VERIFY: snapshots/56044730/main.py:17] [VERIFY: snapshots/56044732/main.py:11] [VERIFY: snapshots/56044730/main.py:60] [VERIFY: snapshots/56044730/main.py:163] [VERIFY: snapshots/56044730/main.py:242]','',
'核心状态包括：_ACTIONS固定动作表、_V17_EXPECT累计购买意图、_V17_BOUGHT补买次数、_MM_STATE中的pos/last价格触发记忆。这些均不能当作真实采购/生产完成账本。[VERIFY: snapshots/56044730/main.py:11] [VERIFY: snapshots/56044730/main.py:34] [VERIFY: snapshots/56044730/main.py:66] [VERIFY: snapshots/56044730/main.py:198]','',
'## 可保留、需修正与不可作为主线的部分','',
'### 1. V41简化入口可保留，纯母带不能作为目标最终实现','',
'简化调用链有利于验证真实入口和状态。固定带本身可以作为强基线与工作节奏样本，但改变未来生产需求时不会重新生成单位任务；“带即调度”描述的是固定时序输出，不是当前状态驱动的排程。[VERIFY: snapshots/56044730/main.py:17]','',
'### 2. V26/V32母带替换被覆盖：必须修正解释和实现边界','',
'外层载入_F_ACTIONS并赋给_ACTIONS，但_V17_BASE_AGENT保存的内层agent调用_v120_distilled_expert，后者每次执行又将_ACTIONS设回_V120_DISTILLED_ROUTE，然后调用_V19_CORE。因此包内新母带的存在不等于它成为运行时基础动作源。[VERIFY: snapshots/56036496/main.py:2238] [VERIFY: snapshots/56036496/main.py:2259] [VERIFY: snapshots/56036496/main.py:2267] [VERIFY: snapshots/56036496/main.py:2273] [VERIFY: snapshots/56036496/main.py:2301]','',
'相同调用链存在于a53包。两个版本的生产采购组合在全部所查对局一致，也与固定旧骨架主导相容；不能把线上成绩归因于fam_F换血成功。[VERIFY: snapshots/56033998/main.py:2238]','',
'### 3. 动物护栏的目的可保留，当前计数实现不可照搬','',
'真实tile为kind=PASTURE、animal="COW"或"SHEEP"；当前函数只处理animal字典，或kind本身等于COW/SHEEP，漏掉已投放动物。四个本地包均有该问题。[VERIFY: snapshots/56044730/main.py:41] [VERIFY: snapshots/56036496/main.py:2282] [VERIFY: snapshots/56033998/main.py:2282]','',
'在保存的真实观测中单独调用此纯辅助函数（未调用候选agent）得到8个反例：例如episode105981812/state24，场上2牛2羊、仓内及携带无动物，函数返回0牛0羊，正确总数为2牛2羊。漏数会使need=expected-have错误为正，进入补买判断；最终收益影响仍需新同源消融确认，不从此反例臆测已损失多少金币。[VERIFY: snapshots/56044732/main.py:73]','',
'此外_BOUGHT在发出补买时即增长，不能表示已经成交的补买次数，应改成真实状态确认。[VERIFY: snapshots/56044730/main.py:79]','',
'### 4. MM应作为卖出触发规则，不能作为套利账户','',
'a53仍会向STRAWBERRY/MILK/WOOL/MELON发送BUY_PRODUCT，本次137局共有1436条该类请求；这些商品不属于引擎允许购买的WHEAT/FERTILIZER。V32和V41本地包已删掉挂单，但保留pos增长作为价格事件记忆。应保留可消融的真实库存卖出规则，并重命名/重新定义这份内部状态，禁止把它解释成真实持仓或利润。[VERIFY: snapshots/56033998/main.py:2426] [VERIFY: snapshots/56033998/main.py:2472] [VERIFY: snapshots/56036496/main.py:2472] [VERIFY: snapshots/56044730/main.py:229]','',
'LEAD从下一步固定表读取SELL意图，用当前shed截断后提前出售；这里读取的是自己固定计划，不是未来真实观测泄漏。它是可保留的战术候选，不能证明产能结构适应。[VERIFY: snapshots/56044730/main.py:82]','',
'fill仅替换原PASS，依据脚下状态选择浇水/收获/收肥；方向可作为调度候选，但其机会成本与仓容影响仍需完整回合验证，不能仅用“没改变位置”认定零风险。[VERIFY: snapshots/56044730/main.py:120]','',
'### 5. V34商店配额方向可用，当前供需模型不够','',
'本地未提交的V34读取已揭示YARN、奶店、莓店、PET数量，调整待购动物、牧场预留及作物配额。这比固定带更接近生产结构条件化，但这些规则没有在该块扣除对手预计供给，且保留了固定的日程投入基线。[VERIFY: development_snapshots/v34_demand_align/main.py:28] [VERIFY: development_snapshots/v34_demand_align/main.py:204]','',
'其所谓速率匹配为每步q<=int((2+店铺加项)*rate_mult)，而当前真实配置为商店每4步消费、中心每24步消费。以无店的中心消费品为例，默认批量上限3并非真实平均需求1/24；因此它应称启发式批量帽，不能把“我方供给≤总需求”的成立视为已证明。更不能忽略对手也在出售。[VERIFY: development_snapshots/v34_demand_align/main.py:650]','',
'已读开发记录中“价位分布翻转→剩余全是工程”“调度器在高分池自然恢复”“固定带来自高分选手→本带具有相同分数上限”等推断均不足以成立。产销结构、市场反馈、执行密度仍须联合验证。','',
'## 本地门控为何不能直接推到2500/2900','',
'fam_matrix会运行自然RNG和双席位，这是可保留的设计；但按当前实现只打印分组汇总，不落逐局seed/seat/源文件SHA。fidelity支持tape/mod/sub三类不同入口，精确命令缺失时无法追认原来究竟运行哪个。[VERIFY: supporting_snapshots/v16_online_fidelity/fam_matrix.py:10] [VERIFY: supporting_snapshots/v16_online_fidelity/fidelity.py:26]','',
'fidelity把agent异常替换成PASS继续比赛，只在前3步输出异常文本。正常终局或分数表不等于候选零异常；应把异常数写入门控结果并失败。[VERIFY: supporting_snapshots/v16_online_fidelity/fidelity.py:59]','',
'sweep_seeds的单人198k比较固定8家商店且对手PASS，只是该环境的生产/执行参考，不是强对手胜率。其产出估计来自相邻随身库存增量并排除前步PICKUP商品，也不等同于引擎逐次HARVEST的完整事件账本。[VERIFY: supporting_snapshots/v16_online_fidelity/sweep_seeds.py:5] [VERIFY: supporting_snapshots/v16_online_fidelity/fidelity.py:64]','',
'## 版本处置建议','',
'- V41-RB：保留为当前强基线和线上观察对象；14/15的起步值得继续看，但非已证实2500，更非生产自适应。','- V41-F：保留独立对照；12/13且席位、对手覆盖不足，不能凭当前评分低于RB认定更弱。','- V32：保留旧生态基准和清除废单的处理；不继续沿用深层旧agent作为新浅树底座。','- V26-a53：保留反例及压力对手；137局最近40仅45%，且仍挂非法商品购买请求，不作为新框架默认主线。','',
'## 框架调整','',
'完整修订见[FRAMEWORK.md](FRAMEWORK.md)：浅规则树输出当前经营配额与投资数量，共同调度器从真实状态生成任务；保留需求适应、任务承诺、成交确认及胜率门，移除HMoE/多专家/PPO的架构前提。先证明固定配置可兑现，再证明浅树优于固定配置，最后验证对手供给信号的增益。','',
'## 数据与验证边界','',
'- 在线数据为本账号提交的真实PUBLIC对局；没有打开既有封存Blind，也没有把官方日包混入本账号统计。','- 四个代码快照取自按提交描述和路径对应的本地tar主文件，保存tar/main SHA；未取得Kaggle服务器保存文件的独立字节证明。因此代码结论指向本地候选包，行为结论由真实Replay支持。','- 采购、动作、非法购买请求均为请求层统计，不能冒充已执行投入、成交或损失金额。','- 不同版本线上匹配不随机对齐，评分与胜率差异不能单独证明某一层改动的因果收益。','- 287局输入SHA与身份在online_rows.json；汇总在online_summary.json；8个计数反例亦在汇总。','- 分析程序analyze.py可复算；缓存只复用本轮已经解析的同一submission/episode记录，完整重算可将两个online结果文件移开后执行。','']
# 精确引用登记与文件内容哈希。
refs=sorted(set(re.findall(r'\[VERIFY: ([^\]]+)\]', '\n'.join(lines))))
lines+=['## VERIFY清单','']+[f'- {r}' for r in refs]
(B/'REVIEW.md').write_text('\n'.join(lines)+'\n')
manifest=[]
for p in sorted(B.rglob('*')):
 if p.is_file() and 'replays' not in p.parts and p.name!='artifact_manifest.json':manifest.append({'path':str(p.relative_to(B)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(B/'artifact_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
for r in refs:
 f,ln=r.rsplit(':',1);assert (B/f).is_file(),r;assert 1<=int(ln)<=len((B/f).read_text().splitlines()),r
assert not D['issues'];assert sum(r['verified']['n'] for r in D['summaries'])==287
print('report generated; references verified',len(refs),'games 287; issues 0')
