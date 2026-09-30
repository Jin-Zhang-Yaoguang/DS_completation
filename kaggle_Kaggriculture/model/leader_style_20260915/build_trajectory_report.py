from pathlib import Path
import json,hashlib,statistics
B=Path(__file__).resolve().parent
T=json.loads((B/'trajectory_analysis.json').read_text());S=json.loads((B/'shop_response_analysis.json').read_text());timing=[];daily=[];shops=[]
for sid,label in [('56156662','榜首版'),('56216119','新版'),('historical','历史同名')]:
 g=T[sid];a=g['first_accounted_seconds'];timing.append({'version':label,'submission':sid,'games':g['n'],'medianSeconds':a['median'],'q25Seconds':a['q25'],'q75Seconds':a['q75'],'minSeconds':a['min'],'maxSeconds':a['max'],'laterExcessGames':g['later_excess_n']})
 if sid!='historical':
  for d in g['daily']:daily.append({'version':label,'day':d['day']+1,**d,'gameDay':d['day']+1})
for r in S['56156662']['by_reveal_and_shop']:
 if r['reveal']==2:shops.append({'shop':r['shop'],'games':r['n'],'cows':r['after_COW'],'sheep':r['after_SHEEP'],'geese':r['after_GOOSE']})
sections=[
{'id':'startup-timing','title':'首步耗时：已核实','queries':['startupTiming'],'text':'''## 9. 首步约 19—20 秒：不是经济启动，而是程序首次执行

本次直接读取全部 820 局的 remainingOverageTime，并核对与 replay 版本相同的 Kaggle environments 1.32.7 官方发行包 core.py，第 629—632 行：每步扣除 max(0, duration − actTimeout)。本比赛 actTimeout=1 秒，因此余额下降的步骤可由“1 + 余额下降量”还原引擎计入的执行耗时。

榜首版 381 局首步中位数 **19.18 秒**，中间 50% 为 **15.94—21.04 秒**，范围 12.29—38.19 秒；新版 193 局中位数 **20.15 秒**，中间 50% 为 **16.92—21.96 秒**。历史同名 246 局中位数 18.37 秒。

**820/820 局均只在首步消耗额外时间，后续 718 个决策没有再次扣减。** 包括商店解锁时，也没有新的超时余额下降。这只能说明后续每步没有超过 1 秒的计入耗时，不能把它解释为每步零耗时或毫秒级推理。它也不是纯模型加载计时：进程与依赖初始化、编译、读取文件、预计算和首次决策都可能包含其中。

例：Episode 107673304，Majkel 在 seat 1，余额从 60 降至 42.096693，首步计入耗时为 18.903307 秒，余下整局余额不变。必须按本人 seat 读取，不能误读 seat 0 对手的时间。'''},
{'id':'shop-response','title':'商店刷新后的调整','queries':['shopResponse'],'text':'''## 10. 商店刷新后如何更新决策

这里将“上线刷新”理解为新商店解锁。每 3 个游戏日新增一家商店，可重复出现；已有商店继续消费，并非全部替换。分析分别对齐第 1—8 次解锁，统计之后 72 步的实际采购。行为调整不等于在线更新神经网络权重。

**第一次解锁后不急于改变牲畜规模。** 在全部 574 局，第一家商店出现后的三天均未新增牛羊鹅。此时继续原生产节奏，草莓种子购买均值在不同首店组大致为 6.7—7.1（榜首版）。不能用全季首店相关性，直接声称见到首店就立即转型。

**第二次解锁与首轮羊毛回款、扩地相邻，配置分支非常清晰。** 榜首版前两家店至少一家为毛线店的 88 局，随后三天 88/88 局购入额外羊，数量为 4—7 只；前两家均非毛线店的 293 局，293/293 局都没有增购羊。

进一步固定第一家店为面包店：第二家是毛线店的 6 局，之后三天平均买羊 6.67 只；第二家不是毛线店的 45 局，平均买羊 0。这个分组比单看整季相关性更接近“新信息出现后改变策略”的证据，但仍未控制种子、对手、资金和全部状态。

下表按第二家新店分组，列之后三天平均实际购入数量；第一家店不同，不能将所有差异归因于第二家店。

**后期调整幅度收缩。** 新增毛线店后 72 步的平均购羊量，第 2—8 次解锁依次为 6.23、6.12、2.31、1.24、0.57、0.02、0。与此同时，后期宠物咖啡店组的胡萝卜种子采购更高。行为符合剩余生产周期缩短后减少长期牲畜投入、调整作物组合的解释；不同解锁阶段的样本和既有资产不同，不能把递减数列当成纯时间效应。'''},
{'id':'trajectory-repeat','title':'每天与跨局轨迹相似度','queries':['trajectoryDaily'],'text':'''## 11. 低重复率要拆开看

本次对齐同版本、同一天、同一步，比较农夫及按索引排列的工人坐标、完整单位动作，以及单个单位槽位动作。采用所有不同 replay 对的平均一致率，不使用“最常见动作占比”替代。两种指标不可混用。

榜首版第 1 天：全队同一步位置一致率 **98.91%**，全队动作一致率 **93.84%**，全天位置轨迹仅 4 种、全天动作序列仅 5 种。前 20 个单位决策完全相同，开局存在很强的共同骨架。

第 12 天：全天动作已有 358 种，但同一步农夫位置一致率仍达 **89.20%**，单个单位槽位动作一致率 **66.03%**；要求“整队同时完全一样”时才降至 **14.77%**。因此“全局或全天序列几乎不重复”并不意味着每个单位都在采取全新的策略。

第 21 天：381 局全天轨迹全部不同，但单个单位槽位动作一致率仍有 **38.95%**。人员越多、比较时间越长，完整序列完全相同这一条件越难满足。

**商店条件能解释部分分化。** 第 7 天全队动作一致率从无条件的 39.71%，升至前两家商店顺序相同条件下的 **75.84%**（1,145 对）；第 10 天为 27.22% → 46.05%（153 对）。后期相同完整商店历史的样本迅速变少，第 21 天没有可比较的同历史对局，不能外推。

新版第 1 天全队动作一致率为 57.84%，全天动作序列 48 种，确实比旧版更早分化。但两个版本的主要产出节点仍基本一致。

**同一局的相邻两天也不是重复播放相同日程。** 按同一时刻对齐，榜首版相邻日全队位置一致率的各日均值约 4.2%—12.1%；工人数、成熟状态和生产阶段都在变化。此指标会受工人索引、队伍规模及时间偏移影响，不能用于判断是否复用了相似空间路线。

限制：坐标是绝对坐标，工人按日内索引匹配，不代表跨天持续存在的同一名工人；单位槽位比较只纳入双方都存在的槽位。位置/动作一致是严格相等，不是路径距离、允许时移的相似度或算法身份识别。日末最后一天只有 23 个有效决策。'''},
{'id':'model-hypotheses','title':'它可能在加载什么','queries':['startupTiming','trajectoryDaily','shopResponse'],'text':'''## 12. 如何更新对深度学习模型的判断

首步稳定耗时十几至二十多秒，是上一轮仅分析经济启动时遗漏的重要证据。结合后续所有步骤均未再次消耗额外时间，应提高对“首次执行有较重初始化、之后使用较轻在线决策”的重视。

**深度学习模型是合理候选，但尚不能排到明显领先的位置。** 导入推理框架、读取权重、首次推理预热可以产生这种计时形态；JIT 编译精确模拟器/规划器、加载并解压计划库、建立路径或状态缓存，同样符合首步重、后续轻的表现。启动时间不能反推出权重大小或模型层数。

首个动作在所有 574 局相同，内容也简单：农夫 PASS，买 1 牛和 5 小麦。因此这段耗时更像可复用的初始化或通用预计算，尚无证据表明它花 20 秒专门搜索这个简单动作。首步还没有未来商店信息，若预计算，也只能是通用计划、候选分支或基于当前信息的推演。

低整局轨迹重复率主要支持“状态相关决策”，对区分深度学习与规则/搜索的辨识力弱。尤其是前两家毛线店与是否加羊呈 88/88、293/293 的清晰分界，而且固定商店历史后动作相似度明显回升，这些现象与条件计划或规则分支也高度相容；神经网络同样能够学出这种分界。

当前更稳妥的结构判断是：**首步初始化某种可复用计算或策略资产 → 保留稳定生产节奏 → 根据商店历史、资源和当前状态选择动作。** 最值得并列保留的两个技术假设是“加载/预热学习策略”和“编译/预计算后运行规划或混合控制器”。没有权重文件、依赖清单、初始化日志或 profiler，无法确认它究竟加载了什么。

也不能从商店刷新后的动作变化推断它在比赛中训练或更新权重。本次只能确认行为随着信息变化。''' }
]
header='# Majkel1337：首步耗时、商店响应与轨迹重复性\n\n基于原冻结窗口；820 局计时、574 局活跃版本行为。所有数字由实际 replay 或已核验成交账本重新统计。\n\n'
md=header+'\n\n'.join(s['text'] for s in sections)
md+='\n\n## 逐日明细：榜首版本\n\n| 第几天 | 全天动作种数 | 全队位置一致率 | 全队动作一致率 | 农夫位置一致率 | 工人单槽动作一致率 | 同商店历史全队动作一致率 | 同历史对数 |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
for d in T['56156662']['daily']:
 pct=lambda x:'—' if x is None else f'{x*100:.2f}%'
 md+=f"| {d['day']+1} | {d['day_action_hash_unique']} | {pct(d['positions_pair_equal'])} | {pct(d['actions_pair_equal'])} | {pct(d['farmer_positions_pair_equal'])} | {pct(d['worker_action_pair_equal_given_present'])} | {pct(d['actions_pair_equal_same_shop_history'])} | {d['shop_history_pair_count']} |\n"
md+='\n## 复现与来源\n\n- `analyze_trajectory.py` → `trajectory_rows/`、`trajectory_analysis.json`：直接读取全部原始 replay，保留每局逐日指纹和超时余额变化。\n- `analyze_shop_response.py` → `shop_response_analysis.json`：对齐每次商店解锁，统计实际采购及固定首店的分组。\n- `build_trajectory_report.py`：生成本专题并增补现有交互报告；若重跑旧 `build_report.py`，之后需再运行本脚本恢复专题。\n- `raw/kaggle_core_timing_v1.32.7.py`：从官方同版本发行包提取，计时公式在第 629—632 行。发行包只下载、未安装。\n- `raw/timing_package/kaggle_environments-1.32.7-py3-none-any.whl`：官方发行包存档。\n- 原始对局路径与 SHA 见 `episode_table.json`；全部分析沿用已冻结样本。\n'
(B/'TIMING_TRAJECTORY_AND_SHOP_RESPONSE.md').write_text(md)
# Preserve prior app identity, presentation revision, and authored sections.
app=B/'report_app/src';data=json.loads((app/'data.json').read_text());content=json.loads((app/'content/report/content.json').read_text())
for q,rows,files,definition in [('startupTiming',timing,['trajectory_analysis.json','raw/kaggle_core_timing_v1.32.7.py'],'首步计入耗时=actTimeout+超时余额下降；余额不降只能给出每步<=1秒。'),('trajectoryDaily',daily,['trajectory_analysis.json'],'同版本跨局同日同步的配对严格一致率；单单位槽位只比较双方均存在的索引。'),('shopResponse',shops,['shop_response_analysis.json'],'第二家新店出现后的72步实际购入；不同首店、资金和对手未全部控制。')]:
 data['queries'][q]={'rows':rows,'source':{'title':'官方 replay 再分析 · '+q,'files':[str((B/f).resolve()) for f in files],'metricDefinitions':[{'label':'统计口径','definition':definition}],'evidenceFlow':[{'title':'冻结样本','detail':'原820局；版本56156662共381局，56216119共193局，历史同名246局。'}]},'methods':[{'language':'python','code':'python analyze_trajectory.py\npython analyze_shop_response.py\npython build_trajectory_report.py'}]}
ids={s['id'] for s in sections};content['sections']=[s for s in content['sections'] if s['id'] not in ids]+sections;data['buildStatus']='complete'
(app/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2));(app/'content/report/content.json').write_text(json.dumps(content,ensure_ascii=False,indent=2))
p=B/'REPORT.md';s=p.read_text();marker='## 首步计时、商店响应与轨迹专题'
if marker not in s:p.write_text(s+'\n\n'+marker+'\n\n见 [详细专题](TIMING_TRAJECTORY_AND_SHOP_RESPONSE.md)：820 局首步计时核查、30 天轨迹一致率、8 次商店解锁后的配置响应，以及对深度学习与编译/预计算假设的更新。\n')
print('report and app sections updated')
