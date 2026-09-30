#!/usr/bin/env python3
"""将本次审计证据汇成可携带 HTML 的规范输入；不运行比赛或训练。"""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import sqlite3

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREFIX = str(HERE.relative_to(ROOT))
WT = '.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'

def read(name):
    return json.loads((HERE / name).read_text())

title = 'V125：金牌策略研究进展'
now = datetime.now(timezone.utc).isoformat()
manifest = dict(version=1, surface='report', title=title, generatedAt=now,
                description='持续研究快照 · 候选、机制、失败与冻结门控',
                blocks=[], charts=[], tables=[], cards=[], sources=[])
datasets = {}
source_ids = set()
chart_map = []

def source(sid, label, path, description='', href=None):
    if sid in source_ids:
        return sid
    obj = dict(id=sid, label=label, path=path)
    if href:
        obj['href'] = href
    obj['query'] = dict(engine='已保存本地实验与审计', description=description,
                        executed_at=now, tables_used=[path])
    manifest['sources'].append(obj)
    source_ids.add(sid)
    return sid

def md(bid, body, sid=None):
    b = dict(id=bid, type='markdown', body=body)
    if sid:
        b['sourceId'] = sid
    manifest['blocks'].append(b)

def table(tid, title_, rows, columns, sid, sort=None, subtitle=None):
    datasets[tid] = rows
    cols = []
    for c in columns:
        field, label, *rest = c
        cols.append(dict(field=field, label=label, **({'format':rest[0]} if rest else {'type':'text'})))
    t = dict(id=tid, title=title_, dataset=tid, sourceId=sid, columns=cols,
             defaultSort=dict(field=sort[0] if sort else columns[0][0], direction=sort[1] if sort else 'asc'),
             density='dense' if len(rows)>12 else 'spacious', layout='full')
    if subtitle:
        t.update(subtitle=subtitle, showDescription=True)
    manifest['tables'].append(t)
    manifest['blocks'].append(dict(id=tid+'_block', type='table', tableId=tid, layout='full'))

def chart(cid, title_, rows, x, y, sid, kind='bar', group=None, fmt='number', subtitle='', horizontal=False):
    datasets[cid] = rows
    enc = dict(x=dict(field=x[0],type='quantitative' if kind=='line' else 'nominal',label=x[1]),
               y=dict(field=y[0],type='quantitative',label=y[1],format=fmt))
    if group:
        enc['color'] = dict(field=group, type='nominal', label='对象')
    c = dict(id=cid, title=title_, type=kind, dataset=cid, sourceId=sid,
             encodings=enc, valueFormat=fmt, layout='full',
             settings=dict(orientation='horizontal' if horizontal else 'vertical', sort='none',
                           showPoints='never', groupMode='grouped' if group else 'single'),
             labels=dict(values='none' if kind=='line' else 'auto'))
    if subtitle:
        c.update(subtitle=subtitle, showDescription=True)
    manifest['charts'].append(c)
    manifest['blocks'].append(dict(id=cid+'_block',type='chart',chartId=cid,layout='full'))
    chart_map.append(dict(id=cid, type=kind, question=title_, rows=len(rows), fields=[x[0],y[0],group],
                          palette_policy='shared-native-tokens; single series or explicitly labeled groups',
                          sourceId=sid))

def sections_from_markdown(path, prefix, sid=None, exclusions=()):
    text = (HERE/path).read_text()
    text = text.replace(str(ROOT)+'/', '')
    chunks = re.split(r'(?m)(?=^## )',text)
    for i,chunk in enumerate(chunks):
        if i==0 and chunk.startswith('# '):
            chunk = re.sub(r'^# [^\n]*\n','',chunk).strip()
            if not chunk:
                continue
        if any(chunk.startswith('## '+e) for e in exclusions):
            continue
        if chunk.strip():
            md(prefix+str(i),chunk.strip(),sid)


registry=read('iteration_registry.json')
s_log=source('log','V125研究账本',PREFIX+'/EXPERIMENT_LOG.md','每代单机制、新开发块、淘汰与重设计；不代表金牌门通过。')
s_registry=source('registry','候选与面板注册',PREFIX+'/iteration_registry.json','当前状态；冻结候选及结果另有原始清单。')
s_gate=source('gate','冻结金牌门1.3',PREFIX+'/GATE_PROTOCOL.md','G0到G5全部必选；每阶段证据独立登记。')
s_audit=source('mechanisms','R0逐步机制账本',PREFIX+'/research/mechanism_analysis/r0_pass_s0/analysis.json','仅重放既有动作，不产生新对局；物料守恒、在途、缺水与仓容。')
md('title','# '+title)
run_rows=[]
for summary_path in sorted((HERE/'evaluation').glob('*/summary.json')):
 if summary_path.parent.name.startswith('harness_'):
  continue
 raw=summary_path.read_bytes();summary_data=json.loads(raw)
 if summary_data.get('schema','').startswith('v125-natural'):
  run_rows.append(dict(path=str(summary_path),sha256=hashlib.sha256(raw).hexdigest(),completed=summary_data.get('done_games',0),status=summary_data.get('status')))
count_complete=sum(r['completed'] for r in run_rows)
failed_candidates=sum(c['status'].startswith('RETIRED') for c in registry['candidates'])
(HERE/'report_evidence_snapshot.json').write_text(json.dumps(dict(generated_at=now,registry=registry,completed_full_local_games=count_complete,runs=run_rows,exclusions='harness_*工程冒烟、失败未完成场、保存动作重放及人工短场景不计完整研究对局'),ensure_ascii=False,indent=2))
s_current=source('current_snapshot','本次报告状态和完整对局计数',PREFIX+'/report_evidence_snapshot.json','从各运行summary及注册表派生；保存每个来源的哈希，不把仍未完成的场计入。')
md('summary','## 技术摘要：继续检验资金、生产与竞争力能否同时成立\n\n**当前仍未达到金牌门。** 初版之后已有'+str(failed_candidates)+'个候选因完整开发检查失败而退役，原结果全部保留。V125从当前观察生成自己的计划、任务和动作，没有调用旧对手的完整agent或复播教师动作路线。\n\n最近冻结候选为**'+registry['current_candidate']+'**，研究阶段为'+registry['program_status']+'。本页生成时累计完成'+str(count_complete)+'场本地研究对局；人工微测、保存动作重放和工程冒烟另计。单场现金、局部机制改善及本地锚点都不能代替真实线上金牌资格。下面把当前结果与失败证据一起列出，全部冻结门通过后才结束研究。',s_current)
if (HERE/'research/claude_v25_v26_review/root_review.json').exists():
 s_claude=source('claude_review','Claude V25与V26A30源码、发布包及实际入口审查',PREFIX+'/research/claude_v25_v26_review/REPORT.md','20份文件身份复核、8次官方市场函数控制、1次A30真实入口调用；未增加完整比赛。')
 md('claude_review_result','## Claude 最新模型：可借鉴市场时机，不能照搬做市解释\n\nV25请求低吸的草莓、奶、羊毛和瓜不在官方BUY_PRODUCT支持范围内，发单后的内部持仓会与实际成交脱节。V26A30的F动作表在进入执行核前被V120旧表覆盖，一次真实末入口调用已核实。因此，旧高分不能直接证明“四商品低吸”或“F路线”有效。\n\n可保留的方向是合法小麦扰动、自产库存销售时机和采购顺序保护；必须分别消融，并按下一帧真实库存确认成交。旧M6共1,152行的数字能复算，但缺少当时源码、入口与引擎的完整运行绑定，尚不足以认证当前包。完整审查见 [V25 / V26A30 HTML](research/claude_v25_v26_review/report.html)。Claude文件未改动。',s_claude)
if (HERE/'research/r12_daily_survival/engineering_root_review.json').exists():
 s_r12=source('r12_engineering','R12当日完整浇水路线及真实短执行',PREFIX+'/research/r12_daily_survival/engineering_root_review.json','30投影案例、291次官方单位函数、36纯检查、96完整入口短步，以及96保存动作审计步；零新增完整比赛。')
 md('r12_latest','## R12：给当天全部危险作物保留可完成的路线\n\nR11已退役：对空场死亡只降13.0%；对V120虽然降26.5%，但仓满损失增加33.5%，且配对强度不达标。新原型再次从R0出发，在发出当前动作前检查：现有工人能否在日终前完成全部危险作物的必要浇水。如果当前动作会破坏这份余量，就执行已核路线的第一步。\n\n这是当前日的水服务检查，不是整场生产保证。证书找不到时会明确记录并保留原动作，不假称可行或无解；实际新雇工到场后重新计算。经营、市场及终局day29保持R0。\n\n30个动作投影案例与官方单位执行一致，另6个证书控制通过。双席连续一天的短对照均从死亡1株变为0；18次喂养相同、零逃逸、零实际溢出，但R12每席少收1份肥料。96步保存动作重放与输出完全一致，物料残差为零。随后进入一场已打开种子的完整诊断；这些工程结果尚不构成策略晋级。',s_r12)
if (HERE/'research/r12_daily_survival/opened_root_review.json').exists():
 s_r12diag=source('r12_natural','R12完整自然诊断与机制审计',PREFIX+'/research/r12_daily_survival/opened_root_review.json','已开5001席0PASS，参照同当前引擎的R0；完整候选与另行保存动作审计分开计数。')
 r12diag=read('research/r12_daily_survival/opened_root_review.json')
 md('r12_natural_result','### R12完整诊断结果\n\n'+r12diag['narrative'],s_r12diag)
if (HERE/'research/r11_survival_routes/opened_root_review.json').exists():
 s_r11=source('r11_deadline','R11真实截止与完整诊断',PREFIX+'/research/r11_survival_routes/opened_root_review.json','R0与R11同一已开种子、同一当前引擎；两场完整719步，保存动作另审计1438步。')
 md('r11_latest','## R11：恢复纯浇水任务的最后两个小时\n\nR10的晚期销售与相对R0强度均失败，已正式退役。新研究回到扩张更强的R0：同一12场中，R0投放222只动物、发生192株缺水死亡；R10投放120只、零缺水死亡。这个对照暴露了规模与照护的矛盾，并不证明单一原因。\n\n锁定的真实反例是第15日的一株小麦：第22小时两名工人就在相邻格且PASS，任务只需WATER，却因人工截止21小时不能接单。原动作逐帧复核后，官方两步反事实确认：R0死亡，R11完成移动和浇水后存活，双席一致。\n\nR11只把**普通日危险植物、且任务恰为一次WATER**的截止改成23小时。经营目标、匹配权重、采购、其他任务和终局分支保持R0。首次微测有时间字段赋值错误，已作废并保留；修正工具后每步检查时钟，不能把错误实验当成候选失败或成功。',s_r11)
 r11_diag=read('research/r11_survival_routes/opened_root_review.json')
 table('r11_opened','已打开5001席0对PASS：只作诊断',[dict(candidate=k.upper(),cash=v['cash'],plants=v['denominators']['plantings_all'],deaths=v['denominators']['plant_eod_drought_deaths'],animals=v['denominators']['animal_placed'],overflow=v['overflow_quote'],residual=v['mature_quote']) for k,v in r11_diag['metrics'].items()],[('candidate','版本'),('cash','终局现金','number'),('plants','播种','number'),('deaths','缺水死亡','number'),('animals','动物投放','number'),('overflow','溢出报价','number'),('residual','成熟残留报价','number')],s_r11)
 md('r11_boundary','R11单场现金增加821，缺水从9株降至7株，仍是7/120，高于G1的1%。这只是进入新开发块的依据。正式源码SHA为1d9ce5dc05bcce400787563c69c74a40cc78bc67f2e9ca3511146f8adaaece57；6101–6103双席、R0/R11、PASS/V120共24场预先冻结，不能在结果出现后调整20%保活主指标或配对强度条件。',s_r11)
if (HERE/'research/r11_survival_routes/fresh_strength_assessment/assessment.json').exists():
 s_r11strength=source('r11_strength','R11新24场完整配对强度',PREFIX+'/research/r11_survival_routes/fresh_strength_assessment/assessment.json','R0与R11在新三种子双席上分别对PASS和V120；强度及机制分别裁决。')
 r11strength=read('research/r11_survival_routes/fresh_strength_assessment/assessment.json')
 md('r11_strength_result','### R11新开发强度裁决\n\n完整性：'+str(r11strength['data_integrity_pass'])+'；配对强度通过：'+str(r11strength['development_strength_guard_pass'])+'。每对手独立要求至少4/6正向、中位数大于零、两个席位均值不负。',s_r11strength)
 table('r11_strength','R11相对R0的配对分差',[dict(opponent=g['opponent_label'],positive=str(g['positive_deltas'])+'/'+str(g['expected_pairs']),mean=g['mean_margin_delta'],median=g['median_margin_delta'],passed=str(g['pairwise_guard_pass'])) for g in r11strength['pairwise_groups']],[('opponent','对手'),('positive','正向配对'),('mean','平均分差变化','number'),('median','中位数变化','number'),('passed','通过')],s_r11strength)
if (HERE/'research/r11_survival_routes/fresh_mechanism_assessment/assessment.json').exists():
 s_r11mechanism=source('r11_mechanism','R11新24条实际保活与守护指标',PREFIX+'/research/r11_survival_routes/fresh_mechanism_assessment/assessment.json','实际官方动作重放；全部缺水死亡均计入，不事后豁免。两种暴露分母、首水、逃逸、溢出与终局资产同时保留。')
 r11mechanism=read('research/r11_survival_routes/fresh_mechanism_assessment/assessment.json')
 md('r11_mechanism_result','### R11真实保活主指标\n\n每对手独立六局要求全部缺水死亡数下降至少20%，各席不增加。主指标通过：'+str(r11mechanism['primary_mechanism_pass'])+'；其他守护指标通过：'+str(r11mechanism['companion_guard_pass'])+'。这里的开发改善不代表正式G1全部通过。',s_r11mechanism)
 table('r11_mechanism','R11全部缺水死亡对照',[dict(opponent=g['opponent'],parent=g['parent']['deaths'],child=g['child']['deaths'],reduction=g.get('relative_death_reduction'),primary=str(g['primary_pass']),guard=str(g['guard_pass'])) for g in r11mechanism['groups']],[('opponent','对手'),('parent','R0死亡','number'),('child','R11死亡','number'),('reduction','降幅','percent'),('primary','主指标'),('guard','守护线')],s_r11mechanism)
if (HERE/'research/r10_service_calendar/fresh_strength_assessment/assessment.json').exists():
 s_r10strength=source('r10_strength','R10新36场完整配对强度',PREFIX+'/research/r10_service_calendar/fresh_strength_assessment/assessment.json','6001–6003双席，R0/R9/R10分别对PASS/V120；每参照与对手独立评判，胜PASS本身不构成强度资格。')
 r10_strength=read('research/r10_service_calendar/fresh_strength_assessment/assessment.json')
 md('r10_fresh_strength','## R10新场景裁决\n\n完整性检查：**'+str(r10_strength['data_integrity_pass'])+'**；开发强度门：**'+str(r10_strength['development_strength_guard_pass'])+'**。必须同时超过R0与R9，任何一组失败均不晋级。表中“正向配对”指同一seed、席位和对手下，自己的现金减对手现金所得分差，比参照更高。',s_r10strength)
 table('r10_paired_strength','R10相对两代参照的分差',[dict(reference=g['reference'],opponent=g['opponent_label'],positive=str(g['positive_deltas'])+'/'+str(g['expected_pairs']),mean_delta=g['mean_margin_delta'],median_delta=g['median_margin_delta'],passed=str(g['pairwise_guard_pass'])) for g in r10_strength['pairwise_groups']],[('reference','参照'),('opponent','对手'),('positive','正向配对'),('mean_delta','平均分差变化','number'),('median_delta','中位分差变化','number'),('passed','该组通过')],s_r10strength,subtitle='每组至少4/6正向，中位数大于零、两个席位均值不负；完整主机制与G0–G5另判。')
if (HERE/'research/r10_service_calendar/fresh_mechanism_audit/assessment/assessment.json').exists():
 s_r10metric=source('r10_late_sales','R10新24条实际自产销售',PREFIX+'/research/r10_service_calendar/fresh_mechanism_audit/assessment/assessment.json','只统计R9/R10各12条保存轨迹，day11..29非WHEAT实际SELL（含自产肥料）；每局物料与零外购来源核对，非新比赛。')
 r10_metric=read('research/r10_service_calendar/fresh_mechanism_audit/assessment/assessment.json')
 md('r10_late_result','### 晚期自产销售主指标\n\n24条来源完整性：**'+str(r10_metric['data_integrity_pass'])+'**；原定主指标门：**'+str(r10_metric['primary_mechanism_numeric_threshold_pass'])+'**。每个对手独立累计6局真实现金，要求相对R9增加至少20%，两个席位各自不退。销售额没有扣成本，不能等同利润，也不能覆盖上面的强度失败。',s_r10metric)
 table('r10_late_sales','第11至29日实际自产销售',[dict(opponent=g['opponent'],parent=g['stats']['V125-R9']['cash_sum'],candidate=g['stats']['V125-R10']['cash_sum'],change=g['relative_cash_change'],passed=str(g['primary_numeric_threshold_pass'])) for g in r10_metric['groups']],[('opponent','对手'),('parent','R9六局','number'),('candidate','R10六局','number'),('change','增幅','percent'),('passed','该组通过')],s_r10metric)
if (HERE/'research/r10_service_calendar/stage_b/optimization_05/root_review.json').exists():
 s_p5=source('r10_opt5','P5自然局与真实物料审计',PREFIX+'/research/r10_service_calendar/stage_b/optimization_05/root_review.json','冻结a0e4源码；官方719步及1440状态一致；保存动作另重放719步，候选调用零，实际物料守恒核对。')
 md('r10_opt5_outcome','## 新结果：完整自然局现金增加3.9%，进入冻结对照\n\nP5在同一已打开种子席0对PASS，现金从R9的**133,227升至138,419，增加5,192（约3.9%）**。719步与1,440次引擎状态检查全部完成，零异常，最慢入口0.148秒。109次救援批准涉及37个不同目标；这两个数字都不是新增执行项目数。\n\n实际重放确认：80次播种全部首水，零缺水死亡和动物逃逸；11只动物全部投放，物料守恒残差为零。仍有两次仓满损失，按当时报价合计3,070；末局留下9粒瓜种和4份成熟未收萝卜。采购目标、任务兑现与末日调度仍需检验，G1未通过。\n\nR10正式开发源码与P5逐字节相同，内部诊断版本名保留OPT05。预留的新种子6001–6003已冻结为36格：R0/R9/R10、双席、PASS/V120。晚期自产销售各对手至少增加20%、各席不退，并同时通过R0/R9配对分差门；不能用本场3.9%改善代替。',s_p5)
 s_p4=source('r10_opt4','P4长任务排序及期末储备失败',PREFIX+'/research/r10_service_calendar/stage_b/optimization_04/root_review.json','唯一P4自然诊断，原失败完整保留；95次日程检查通过，均在后续储备门拒绝。')
 md('r10_opt4_lessons','### 两个阻碍，以及保留下来的拒绝条件\n\n第一处是短任务优先导致远端动物长任务饥饿。改用完整服务跨度排序后，同一预测日的89项服务均通过原checker和双席官方48步；60组纯调度与3个负例也通过。P4自然局由此有95次日程进入原检查器，但还没产生投资。\n\n第二处是预测日程的卖麦公式只分别保护储备与待喂需求，实际取两者最大，未同时保留两者。原期末小麦门将这些日程全部拒绝。P5修正卖麦上限：0、3、10单位储备的三个控制全部保留对应终存；双席官方执行也确实保住3单位。独立checker、期末储备门和实际策略的市场执行代码均未降低要求。',s_p4)
if (HERE/'research/r10_service_calendar/stage_b/optimization_03/opened_natural_diagnostic_01/root_review.json').exists():
 s_p3natural=source('r10_opt3_natural','P3首个完整自然局及R9保存对照',PREFIX+'/research/r10_service_calendar/stage_b/optimization_03/opened_natural_diagnostic_01/root_review.json','源码b5bc、固定runner和引擎；seed1950905001席0对PASS；43来源核对，719动作与旧R9逐帧比较。已打开开发种子。')
 md('r10_opt3_natural','## P3首场：自然局不卡顿，救援没有增益\n\nP3完成**719步、1,440次状态一致性核对**，零异常，最慢调用**0.128秒**。现金133,227，全部719个动作和最终状态与同引擎的R9保存参照完全相同。\n\n207次救援全部失败：169次没有排出完整服务日程，34次启动边界无法表征，4次命中已知不可能的照护历史。没有任何一次进入独立checker；这不是checker检查失败，而是前面的调度或编译已经拒绝。\n\n这轮只支持“有界计算能控制本场耗时”，没有自然局投资或收益增益。随后锁定首个失败step270进行归因，形成上方P4和P5；本轮原动作、失败和阈值保留。',s_p3natural)
if (HERE/'research/r10_service_calendar/stage_b/optimization_03/continuous_official_01/root_execution_review.json').exists():
 s_opt3=source('r10_opt3','OPT03完整入口与真实执行证据',PREFIX+'/research/r10_service_calendar/stage_b/optimization_03/continuous_official_01/root_execution_review.json','冻结b5bc源码，双席各72个连续官方时步；92份来源和完整事件输出核对。人工初态，不属于自然完整比赛或晋级。')
 md('r10_opt3_outcome','## 新机制：保留原批量投资，每帧最多额外验证一个项目\n\nP3先执行原便宜的农业准入，再从被未来劳动门拒绝的正净值项目中挑一个，检查全部未来服务及原资金条件。失败项目按稳定身份轮换，避免每帧反复卡在同一个项目。全部在田、合同、在途及本帧已接受项目仍进入完整检查。\n\n五个固定内部场景耗时0.102至0.196秒。旧场景的24个MELON批量许可保持；零现金两席没有额外投资。随后双席各运行72个真实官方时步，完整入口最慢**0.169秒**，全部144次返回。这解决了已测场景中的超时，尚不能覆盖完整比赛的最坏情况。\n\n每席有5次批准事件，但只涉及3个不同目标：MELON(4,4)已播种并在下一步完成首水，COW(5,5)已建场、投放并照护；MELON(1,6)只买种子，窗口内未播种。批准、采购和最终兑现必须分别计数。',s_opt3)
 table('r10_opt3_execution','P3人工连续执行：两个席位结果相同',[dict(target='MELON(4,4)',approved='210 / 211',actual='211播种，212首水',state='已落地'),dict(target='COW(5,5)',approved='216 / 219',actual='218建场，225投放，随后喂养照护',state='已落地'),dict(target='MELON(1,6)',approved='225',actual='买种子1，窗口内未播种',state='兑现待查')],[('target','不同目标'),('approved','批准时步'),('actual','官方真实动作'),('state','窗口结论')],s_opt3,subtitle='起点为注入100,000现金和48格草莓的人工农场。每席末现金98,844，无销售；不能作为自然强度证据。')
if (HERE/'research/r10_service_calendar/stage_b/optimization_02/root_decision.json').exists():
 s_opt2=source('r10_opt2','OPT02完整等价、性能失败与汇总路径更正',PREFIX+'/research/r10_service_calendar/stage_b/optimization_02/root_decision.json','唯一P2内部经济调用；82份冻结来源及17份输出核对。完整计划状态逐字段相等，四项原接口和七项compact控制通过。原汇总脚本错误保留，只读更正。')
 md('r10_opt2_outcome','## 第二轮优化：缓存精简有效，13.31秒仍未达标\n\n精简完整校验成功后的缓存与日志后，同一人工输入从P1的**18.03秒降到13.31秒**，本次与保存参照相比约减少26.2%。这是单次测量；仍超过1秒门槛。计划、状态、报价和全部原计数完全一致，26个MELON仍只是模型许可，没有新增实际比赛。\n\n四项完整接口对照和七项compact控制全部通过：包括返回值修改不污染缓存、身份和模式错配拒绝、显式自定义函数拒绝，以及第9日已获证但第10日失败时整批缓存不提交。原完整求解和独立检查均保留。\n\n原汇总脚本少读了一层counts，因而把四个计数误读为null并标记等价失败。保存输出本身完整，根已按正确路径核出342次route、1,038次scheduler、926次checker、4次命中；完整typed计划与状态哈希也相同。原脚本、原失败汇总和输出均保留，只读更正不重跑。性能失败结论不变。\n\n后续P3调整规划方式，减少逐报价重复求解；属于新的策略机制，必须重新验证投资节奏和收益。原资金、服务覆盖和金牌门槛不放宽。',s_opt2)
if (HERE/'research/r10_service_calendar/stage_b/optimization_01/root_decision.json').exists():
 s_opt1=source('r10_opt1','OPT01完整计划等价与单次耗时',PREFIX+'/research/r10_service_calendar/stage_b/optimization_01/root_decision.json','P0/P1各一次无监控内部经济调用，完整plan/state逐字段、类型和顺序一致；8项纯接口控制通过。不是完整比赛。')
 md('r10_opt1_outcome','## 第一轮优化：完整计划一致，18.03秒未达到时限\n\n只移除3次默认路径的重复外层复制后，同一人工初态的完整经济计算从**21.20秒降至18.03秒**，约减少15%。这是一对单次测量；P1仍远超1秒门槛。完整计划、状态、报价、诊断计数以及8项接口控制均与原型相同；自定义函数和缓存的隔离保留。\n\n较长的诊断保护时间让两个版本都返回了完整计划：选择种植专家、许可26个MELON，模型剩余现金97,097。这里只计算了计划，没有实际采购或播种。一次计划有342次路线尝试、1,038次调度和926次独立检查，仅4次路线缓存命中；这些数量也完全相同。\n\n随后完成了上方的生产缓存精简实验。原始10秒入口超时与P1的18.03秒失败均保留，1秒门槛不变。',s_opt1)
if (HERE/'research/r10_service_calendar/stage_b/integration_validation/prototype_decision_v1.json').exists():
 r10e=read('research/r10_service_calendar/stage_b/integration_validation/prototype_decision_v1.json')
 s_r10e=source('r10_integration','R10 原型完整入口与内部经济工程结果',PREFIX+'/research/r10_service_calendar/stage_b/integration_validation/prototype_decision_v1.json','170次完整入口尝试、168官方短步、8次内部经济调用；首轮ERROR原样保留。根与独立审查另核所有冻结输入、14个保存run及部分报价。')
 md('r10_integration_outcome','## 首轮接入：入口超时，部分报价单列\n\n**R10默认入口两次都在约10.003秒触发保护，没有返回动作，不能进入新比赛。** 关闭新功能后，6对短场景的60个配对时步逐帧复现R9动作与官方后观测。源码和输入未漂移，全部超时保留，没有重跑择优。\n\n部分报价已验证：4个人工压力输入各有3个报价用完整未来服务路线解除原劳动拒绝，并继续调用原现金门；零现金两席的6个报价全部被现金门拒绝。已完成的24个初次报价，旧成本、容量和评分逐值相同。首轮新默认经济计划全部被保护中断，**首轮部分报价本身不是完整许可或整计划现金证明**；后来单独登记的完整等价参照见上方OPT01。',s_r10e)
 table('r10_engineering_counts','首轮工程调用与结果',[dict(scope='R9完整入口',attempts=108,returned=108,result='返回；其中48步检查真实执行器'),dict(scope='R10关闭新功能',attempts=60,returned=60,result='6对场景动作与官方后观测相同'),dict(scope='R10默认完整入口',attempts=2,returned=0,result='两次10秒保护超时；官方步0'),dict(scope='内部经济函数（带监控）',attempts=8,returned=4,result='4个legacy返回；4个默认30秒保护中断')],[('scope','调用范围'),('attempts','尝试次数','number'),('returned','正常返回','number'),('result','结果')],s_r10e,subtitle='完整入口尝试170；实际官方短步168；内部函数调用单列；新增完整比赛0。监控耗时不作普通入口性能。')
 md('r10_executor_boundary','### 48格草莓：货物保住了，同日销售没有完成\n\n真实R9执行器两席各采收48份，主动PLACE和当日SELL均为0；48份全部在日末自动入仓，零丢弃，现金只扣376雇工费。前面的保存路线则完成了当日主动入仓和出售。两者证明的是不同执行结果，不能用路线存在替代策略兑现。\n\n原资金账从采收日的下一日才计信用，并先扣费用；本次未运行下一日，不能据此声称产品损失、信用提前或以后无法出售。本轮默认杂草率0.005，前面证书控制为0，差异发生在末日结算，不能混称相同完整末态。后续只在已打开人工输入上完成性能剖析与优化，结果分轮列在上方。正式门槛不变。',s_r10e)
if (HERE/'research/r10_service_calendar/stage_b/executor_return_attribution.json').exists():
 s_return=source('r10_return','空闲返仓条件的保存事件归因',PREFIX+'/research/r10_service_calendar/stage_b/executor_return_attribution.json','只读两席保存原子事件与24个观察，以原定价公式核当前预测价格；不运行候选或改变返仓阈值。')
 md('r10_return_reason','### 为什么采完后仍不主动返仓\n\n原普通返仓移动要求随身货值超过1,800，同时满足距离和时间条件。保存场景中，每人最多携带4份草莓，当前预测价格为120至128，最大货值只有512；这个返仓分支整天都不可能触发。到达仓口的少数载货动作还受前面任务分配优先级影响。\n\n这解释了为什么有空闲时槽也不会自动完成主动交付。返仓阈值尚未修改；是否应改为按截止时间、仓容和任务机会成本决策，要另做完整比赛验证，不能把这个人工反例直接当收益提升。',s_return)
if (HERE/'research/r10_service_calendar/stage_b/root_official_v1_review.json').exists():
 s_r10b=source('r10_b','未来完整服务的官方短控制',PREFIX+'/research/r10_service_calendar/stage_b/OFFICIAL_CONTROLS_REPORT.md','首轮12个人工服务日与40个短规则片段；保存实际收据、前后库存和现金，根另核全部文件哈希。')
 md('r10_b_status','## R10 前置证据：完整服务路线的官方规则检查\n\n编译器在1,440组纯函数对照中保持原产量、劳动量和饲料预测不变，并增加逐资产服务、物料、时间窗和交付义务。首轮官方控制执行352步，覆盖12个人工完整服务日、40个短场景，3,005项断言通过。12名雇工的真实费用为376；出生时序、共享取粮、分品种入仓、满仓后出售及末日h22边界均已核对。\n\n这些控制使用明确注入的资产、充足初始现金和关闭随机杂草的条件。部分短反例的土地元数据未同步，证据只用于对应动作规则；它们不能证明真实未来一定可达或费用一定可付。其后的首轮准入原型暴露了上面的性能失败；当时尚未冻结正式R10。后续P3至P5和新开发状态见页首。',s_r10b)
 if (HERE/'research/r10_service_calendar/stage_b/official_pressure_delivery.json').exists():
  s_pressure=source('r10_pressure','48格草莓的官方压力控制',PREFIX+'/research/r10_service_calendar/stage_b/PRESSURE_OFFICIAL_REPORT.md','保存problem与certificate原样执行，四象限明确解锁；双席共48步。不是自然生长得到的农场。')
  md('r10_pressure_result','### 旧劳动估算确实可能拒绝一条可执行路线\n\n人工48格草莓场景中，旧劳动量366超过旧容量298。新路线在两个席位都完成48次采收、全部入仓及出售，最后交付发生在h23；每席实际雇工费376，销售3,692，零日末丢弃。这48步官方追加控制与首轮分开保存。\n\n另一个16牛加16格草莓的人工组合仍未找到完整日程，保持拒绝；没有删去动物照护来换取通过。成功的草莓场景只覆盖采收和交付，不能替代混合服务控制。',s_pressure)
 if (HERE/'research/r10_service_calendar/stage_b/review_impossible_history_probe_20260905T125932437784Z.json').exists():
  s_history=source('r10_history','已知不可能首水的条件状态反例',PREFIX+'/research/r10_service_calendar/stage_b/review_impossible_history_probe_20260905T125932437784Z.json','仅纯编译器与日末状态函数调用，官方/候选调用均零；冻结原模块保留。')
  md('r10_history_boundary','### 接入前发现并封住的历史状态缺口\n\n新小麦若被模型安排在h24首次浇水，当天已经没有这个时槽；原条件推演仍应用了浇水，使下一日出现健康作物。不执行这次不可能的首水，日末结果应是杂草。反例已经保存，新的投资准入层已增加历史检查，7项纯路径回归通过。\n\n“启动日期未知”与“已知照护不可能”分开处理：前者可以只保留受影响日的旧门，后者不能靠第二天重新生成健康资产获得通过。这是人工规则反例及其修复，不是已发现自然比赛中的实际误放；完整候选资格仍待定。',s_history)
if (HERE/'research/r9_cash_prefix/frozen_bundle.json').exists():
 s_r9plan=source('r9_plan','R9冻结设计与36场方案',PREFIX+'/research/r9_cash_prefix/development_protocol.json','源码及测量器在任何R9完整比赛和590x比赛前冻结；资金前缀是条件预测，实际市场只使用观察现金。')
 md('r9_model','## R9：逐日资金检查已实现，预测收入必须接受真实回款检验\n\nR9保留R8的项目净终值选择和执行，只改变资金可行性：每天先扣预计费用，再加入此前已在田资产的延后回款。小麦、肥料、在途动物、仓库商品和本帧新项目都不提供预测信用；任何早期赤字不能靠更晚的收入补过去。\n\n77项微测通过，原资金模式的6对短控制与R8动作及终态一致。计算优化把人工100空格规划从约1.8秒降至0.21秒，保留了原慢版本及逐值对照。它仍依赖未来照护、搬运、仓容和价格假设，不能称作保证偿付。\n\n新开发块固定3个新种子、两个席位；R0、R8、R9各对PASS及V120，共36场。主指标是前十天实际自产非麦销售现金：每个对手独立至少比R8增加20%，每席不退。强度另外比较双方现金分差，须同时超过R0与R8。',s_r9plan)
 r9_strength_path=HERE/'research/r9_cash_prefix/fresh_strength_assessment/assessment.json'
 if r9_strength_path.exists():
  r9_strength=json.loads(r9_strength_path.read_text())
  s_r9strength=source('r9_strength','R9完整配对强度检查',PREFIX+'/research/r9_cash_prefix/fresh_strength_assessment/assessment.json','5901–5903双席；完整性与强度分别裁决；每组6个配对，原始分差=自身现金−对手现金。')
  md('r9_strength_intro','### 新场景强度裁决\n\n下表以同一新种子、同一席位、同一对手配对。分差变化会扣除对手现金的同步变化，正向配对数按严格大于零计算。完整性检查结果为'+str(r9_strength['data_integrity_pass'])+'；开发强度条件为'+str(r9_strength['development_strength_guard_pass'])+'。任何一组失败都不能凭其他组的改善晋级。',s_r9strength)
  table('r9_competitive','R9新场景配对分差',[dict(reference=g['reference'],opponent=g['opponent_label'],positive=str(g['positive_deltas'])+'/'+str(g['expected_pairs']),mean_delta=g['mean_margin_delta'],median_delta=g['median_margin_delta']) for g in r9_strength['pairwise_groups']],[('reference','参照'),('opponent','对手'),('positive','分差改善'),('mean_delta','平均分差变化','number'),('median_delta','中位分差变化','number')],s_r9strength,subtitle='全部36场；按参照与对手分别判断，两个席位也须独立不退。')
 r9_comparison_path=HERE/'research/r9_cash_prefix/opened_trace_audit/comparison/comparison.json'
 if r9_comparison_path.exists():
  comparison=json.loads(r9_comparison_path.read_text())
  s_r9diag=source('r9_opened','R9首场实际产销与收支',PREFIX+'/research/r9_cash_prefix/opened_trace_audit/comparison/comparison.json','同一已打开seed1950905001席0对PASS；官方保存动作重放，不新增比赛；首卖来源、费用和物料守恒核实。')
  md('r9_diagnostic','### 早期销售增加，同时出现仓满损失\n\n同一已打开首场中，R9现金为133,227，R8为117,856，增加15,371。R9对PASS分差为130,227，两项分开记录。前十天自产非麦销售从1,485升至3,243，实际动物投放从1只升至4只。资金放开确实伴随更早的投入与产出。\n\n代价也已出现：R9全期超仓损失当时报价3,592，R8为零；112次播种均有首水，没有缺水死亡或逃逸。末日兑现率98.88%，仍留成熟萝卜和可收肥料。采购逐笔目标证据未齐，不能称G1通过。单场变化也不能证明新种子或强对手优势。',s_r9diag)
  revenue_rows=[]
  for v in comparison['versions']:
   daily=v['first_produced_sale']['daily'];cumulative=0
   for day in range(30):
    actual=daily.get(str(day),{}).get('cash',0);cumulative+=actual
    revenue_rows.append(dict(day=day,version=v['version'],daily_cash=actual,cumulative_cash=cumulative))
  chart('r9_real_sales','首场累计自产非麦销售',revenue_rows,('day','比赛日'),('cumulative_cash','累计实际销售现金'),s_r9diag,kind='line',group='version',subtitle='day0–29，每日实际成交累计；含自产肥料，排除混合来源小麦；没有预测信用。')
  md('r9_curve','曲线使用30个比赛日的真实自产销售累计，表示回款节奏。它不是利润曲线：种子、动物、买麦、雇工和土地支出尚未扣除。全期R9销售多17,774，扣除各项费用变化后，现金净增15,371；该现金桥残差为零。',s_r9diag)
 r9_metric_path=HERE/'research/r9_cash_prefix/fresh_mechanism_audit/summary.json'
 if r9_metric_path.exists():
  s_r9metric=source('r9_metric','R9完整24条实际产销机制',PREFIX+'/research/r9_cash_prefix/fresh_mechanism_audit/summary.json','全部24条保存动作重放，候选调用0；原首卖来源v3，指标聚合v2仅修JSON日键表示，原失败和脚本保留。')
  md('r9_primary','### 主机制成立，整体晋级失败\n\n前十天实际自产非麦销售，相对R8在PASS组增加96.70%，V120组增加127.95%；两个席位分别不退，预定20%主指标通过。全期12场R9共1,386次播种均有首水，零缺水死亡与动物逃逸。\n\n副作用仍需面对：V120组超仓报价损失从2,632升至5,666，动物采购到投放平均等待从6.42增至9.15步。更重要的是，相对R0两组整体分差仍全部退化。资金机制的局部收益不能覆盖这个失败，R9保持退役。',s_r9metric)
  table('r9_early_cash','新场景前十天自产销售',[dict(opponent='PASS',parent=9390,candidate=18470,change=0.966986155484558),dict(opponent='V120',parent=8450,candidate=19262,change=1.2795266272189347)],[('opponent','对手'),('parent','R8六场销售','number'),('candidate','R9六场销售','number'),('change','收入增幅','percent')],s_r9metric,subtitle='每组3个新种子×两席，真实执行0–239步；含自产肥料，排除小麦。')
if (HERE/'research/r10_service_calendar/DESIGN_PROPOSAL.md').exists():
 s_r10=source('r10_design','共享服务日程的实证反例与设计',PREFIX+'/research/r10_service_calendar/DESIGN_PROPOSAL.md','以R9保存实际连续浇水链为依据；18步闭合路径具有显式起终点条件，不是已授予的新投资能力。')
 md('r10_next','## 研究起点：把劳动估计改为可核查的服务日程\n\n当前模型分别向每块田收取到仓的移动成本，真实执行却会沿相邻田块连续作业。已有六格浇水反例：若从仓口出发并返仓，逐资产模型计27动作，一条明确合法的共享路线只需18动作；实际回放确认了其中连续六次浇水、五次移动。\n\n先实现当前日、已到场工人的浇水日程和独立检查器，核起点、每个时间槽、作业期限、重复服务与回仓。17个时间槽的负例也必须被拒绝。随后检查冻结执行器是否真的完成这些服务，以及投资被拒的决定性日期。这是R10最初的设计依据。存在一条路线也不等于实际完成或产生收益；后续实际结果见页首。',s_r10)
 r10_controls=HERE/'research/r10_service_calendar/stage_a/handoff_manifest.json'
 if r10_controls.exists():
  s_r10a=source('r10_a','共享WATER日程的官方短控制',PREFIX+'/research/r10_service_calendar/stage_a/REPORT.md','独立checker和真实官方前后帧；人工条件控制，非新完整比赛。')
  md('r10_a_result','### 阶段A已验证：服务路线可行，执行器的承诺仍有缺口\n\n独立检查器的28个测试方法、46条记录通过；官方短控制24/24断言通过，共92个官方时步，其中36次调用冻结R9。没有新增完整比赛。双席中，18步证书均完成六次浇水并返仓；R9也完成六次浇水，但从第60步开始PASS，未完成控制显式要求的返仓。\n\n植物仍活也不代表到达时仍可作业：临近寿命的负例在移动后变成杂草，下一步浇水无效，日程必须在预计衰退前完成。阶段A只覆盖指定WATER集合，不能据此放宽包含采收、搬运和动物照护的整场劳动门。',s_r10a)
 r10_probe=HERE/'research/r10_service_calendar/budget_probe/captured_r9_opened_s0/summary.json'
 if r10_probe.exists():
  probe=json.loads(r10_probe.read_text())
  assert probe['status']=='DIAGNOSTIC_COMPLETE' and probe['count_closure'] and probe['terminal_equal_source']
  s_r10probe=source('r10_probe','原R9完整轨迹的劳动拒绝定位',PREFIX+'/research/r10_service_calendar/budget_probe/captured_r9_opened_s0/summary.json','冻结源码return探针；719动作及完整收据相等，31原保存摘要和完整终态诊断闭合。报价尝试不是独立项目。')
  rows=[dict(kind=label,count=probe['counts'][key],share=probe['counts'][key]/probe['labor_rejections']) for key,label in [('current_only','仅当天超限'),('future_only','仅未来日超限'),('current_and_future','当天与未来均超限')]]
  table('r10_rejections','劳动拒绝主要发生在哪里',rows,[('kind','原模型失败日期'),('count','报价尝试数','number'),('share','占全部劳动拒绝','percent')],s_r10probe,subtitle='同一已打开首场；保留跨帧及站点重复报价，不是投资机会数。')
  md('r10_probe_meaning','仅未来日超限占62.90%，所以只改当天浇水表示不足以解决主要拒绝来源。下一实现优先检验未来整日的完整服务日程，当前日先保持原劳动估计；未来日的照护、采收、物料、搬运、雇工出生和费用都须明确表示。\n\n本次沿原动作运行719次官方步骤，同时重新调用冻结R9共719次，输出动作与收据全部相同。它是原轨迹的内部诊断，新独立比赛数为零。劳动失败先于现金检查，这些报价的财务可行性尚未判断，也未证明新增准入能获利。',s_r10probe)
if (HERE/'research/r8_development_assessment.json').exists():
 r8=read('research/r8_development_assessment.json')
 s_r8=source('r8_fresh','R8完整36场配对裁决',PREFIX+'/research/r8_terminal_net_selection/fresh_strength_assessment/assessment.json','5801–5803双席；源码与指标工具事前冻结，完整性通过，整体强度护栏失败。')
 table('r8_competitive','R8：生产改善与竞争退化同时出现',[dict(reference=g['reference'],opponent=g['opponent_label'],positive=str(g['positive_deltas'])+'/'+str(g['expected_pairs']),mean_delta=g['mean_margin_delta'],median_delta=g['median_margin_delta']) for g in r8['competitive_pairwise_summary']],[('reference','参照'),('opponent','对手'),('positive','分差改善'),('mean_delta','平均分差变化','number'),('median_delta','中位分差变化','number')],s_r8,subtitle='对V120的分差计入对手响应；全部36场保留，不挑选有利对手或席位。')
 s_r8diag=source('r8_opened','R8首场完整机制与收支',PREFIX+'/research/r8_terminal_net_selection/opened_trace_audit/REPORT.md','只重放已打开1950905001席0；官方收支与自产来源闭合，G1采购仍PENDING。')
 md('r8_diagnosis','### 改善与下一步缺口\n\n首场现金由80,473升至117,856，第一笔自产销售由第257步提前到第96步；但新首卖仅1份肥料、100金币，前十天自产非麦销售合计1,485。真实投资由2牛变为6牛2羊，89次播种全有首水，零缺水死、逃逸和日末溢出。末日仍有1个成熟萝卜未兑现。采购逐笔目标未完整验证，不能称G1通过。\n\n第1天有893现金，但模型为未来饲料预留831、雇工预留57，可用于新增投资只剩5。下一轮检验逐日资金前缀；信用只能来自明确的已有资产、可交付时间和预测售价，当前采购仍须有实际现金。',s_r8diag)
if (HERE/'research/r7_development_assessment.json').exists():
 r7=read('research/r7_development_assessment.json')
 s_r7=source('r7_fresh','R7完整36场配对裁决',PREFIX+'/research/r7_horizon_investment/fresh_strength_assessment/assessment.json','5701–5703双席；源码及所有36局计划事前冻结，完整性通过，四组强度护栏均失败。')
 table('r7_competitive','R7：四组比较全部失败',[dict(reference=g['reference'],opponent=g['opponent_label'],positive=str(g['positive_deltas'])+'/'+str(g['expected_pairs']),mean_delta=g['mean_margin_delta'],median_delta=g['median_margin_delta']) for g in r7['competitive_pairwise_summary']],[('reference','参照'),('opponent','对手'),('positive','分差改善'),('mean_delta','平均分差变化','number'),('median_delta','中位分差变化','number')],s_r7,subtitle='比较双方现金的分差变化；对V120不能只看自身现金。仅本地开发，不是金牌证据。')
 s_r7diag=source('r7_opened','R7开放诊断归因',PREFIX+'/research/r7_horizon_investment/ROOT_OPENED_DIAGNOSTIC.md','一个已打开seed；逐步预算与官方收支审计，单资产预测与真实产出分开。')
 md('r7_diagnosis','### 可保留的发现\n\nR7开放诊断现金80,473，R6同场127,093。125次播种全部当日首水、没有缺水死亡或动物逃逸；但仅购2只动物，且第10天末超仓丢26瓜。开局25格全瓜，直到第10天才有首次销售。第12天已有18,416现金，新增投资仍大量被劳动模型拒绝，因此不能把低收益全部归为现金预算过严。\n\n下一轮把“用于投资选择的预测净终值”与“用于执行任务的净值/劳动分数”拆开，后者保持原值。先验证一个明确变化，不把它写成组合优化或已成功的金牌策略。',s_r7diag)
if (HERE/'research/r5_economy_ablations/assessment.json').exists():
 fixed=read('research/r5_economy_ablations/assessment.json')
 s_fixed=source('fixed_plans','固定经营方案竞争诊断',PREFIX+'/research/r5_economy_ablations/assessment.json','同一个已公开诊断seed、双席位。四固定方案全部纳入；adaptive复用已有结果。新runner只修订单槽位，原ERROR保留。')
 labels={'adaptive':'原自适应','balanced':'均衡','dairy':'奶业','fiber':'羊毛','horticulture':'种植优先'}
 fixed_rows=[dict(profile=labels[r['profile']],cash=r['cash'][0],opponent_cash=r['opponent_cash'][0],margin=r['cash'][0]-r['opponent_cash'][0]) for r in fixed['results']]
 table('fixed_results','现有专家的竞争诊断',fixed_rows,[('profile','经营方案'),('cash','策略现金','number'),('opponent_cash','V120现金','number'),('margin','分差','number')],s_fixed,subtitle='各方案双席结果相同；只有1个已打开seed，不是独立确认或金牌证据')
 md('fixed_meaning','逐动作核查确认：原自适应与种植优先在双席的719个双边动作全部相同。此场景不能归因为Router选错；需要改进专家内部的投资表示与兑现能力。',s_fixed)
sections_from_markdown('EXPERIMENT_LOG.md','log',s_log,exclusions=('重设计 R4',))
rows=[]
for p in sorted((HERE/'research').glob('r*_development_assessment.json')):
 a=json.loads(p.read_text());pairs=a.get('pairs',[])
 if not pairs: continue
 rows.append(dict(candidate=a['candidate'],mean_delta=a['mean_cash_delta'],positive=a['positive_pairs'],pairs=len(pairs),decision=a['decision']))
s_comparison=source('comparison','新场景配对结论',PREFIX+'/research/r1_development_assessment.json','全部候选各自的新开发配对评估；原始数据各自保存games.jsonl与run_manifest。')
manifest['sources'][-1]['query']['tables_used']=[PREFIX+'/research/'+p.name for p in sorted((HERE/'research').glob('r*_development_assessment.json'))]
md('cash_intro','## 改善局部指标，尚未形成稳定生产增量\n\n图中每根柱是对应候选相对R0在三个新seed、双席位上的平均现金变化。各个候选使用不同开发块，不能据此横向排名；对手为PASS，尚未衡量竞争强度。已打开的块全部转为诊断数据。',s_comparison)
chart('mean_delta','新场景平均现金增量',rows,('candidate','候选'),('mean_delta','金币增量'),s_comparison,horizontal=True,subtitle='各自3个新seed × 两席位；对PASS的生产诊断')
table('results','候选增量与裁决',rows,[('candidate','候选'),('mean_delta','平均现金增量','number'),('positive','正向配对数','number'),('pairs','配对总数','number'),('decision','状态')],s_comparison)
md('why_fail','## 失败说明了约束之间的相互影响\n\n采购已确认，并不保证动物及时落地；动物及时落地，也不保证有足够劳动持续喂养。R2虽然减少缺水，却延长动物在途并加重仓满；R3释放投放容量后，供养压力又造成逃逸。新的执行层必须明确资源、截止、承诺和实际完成，不能只把每帧收益排序当完整经营系统。',s_log)
if (HERE/'research/r4_contract_design/DESIGN.md').exists():
 s_design=source('r4','短期合约设计',PREFIX+'/research/r4_contract_design/DESIGN.md','构造前定义的研究假设；原型微场景不是新场景强度证据。')
 sections_from_markdown('research/r4_contract_design/DESIGN.md','r4',s_design)
md('gate_intro','## 金牌门：本地资格与真实线上证据都必须过\n\nG0规则/包/延迟，G1机制闭环，G2旧锚点与增量，G3动态家族和Router，G4真实账号主裁决，G5官方未来独立确认。当前没有任何候选完成整套门。旧本地同源变体、固定录像代理和较高单人现金都不替代这些条件。',s_gate)
md('gold_rule','正式线上验证要求候选在覆盖多个对局日、对手与两个席位的真实样本中成立，并持续进入当时官方金牌范围。若只能取得实际线上强对手而无私有源码，按更严格的实际提交身份与家族分层补证；不把同队另一个高分active当成实际匹配对手的实力。\n\n当前只进行本地开发与诊断。提交包要先做到可审阅、通过本地资格，之后再请求该具体包的逐次上线授权。',s_gate)
md('limitations','## 尚未解决的问题\n\n新场景自然随机流会随双方地块使用变化，现金变化不能全部归因某一费用；已把市场序列与机制量分开记录。任务可执行也不等于产物及时卖出，未来仍需检验强对手下的市场反馈、仓容和终局兑现。公开强队源码不充分，因此真实线上家族验证仍是必要阶段。')

def save():
    # 读者的原生图表接口要求SQL；原始审计来自文件与Python，故保留其来源，
    # 并明确记录这层真实执行的SQLite JSON投影，不能伪装成原始交易数据库。
    reviewed_path=HERE/'reviewed_tables.json'
    reviewed_path.write_text(json.dumps(datasets,ensure_ascii=False,indent=2))
    conn=sqlite3.connect(':memory:')
    conn.row_factory=sqlite3.Row
    reviewed_json=reviewed_path.read_text()
    sql_bindings=[]
    parents={s['id']:s for s in manifest['sources']}
    for item in manifest['charts']+manifest['tables']:
        did=item['dataset'];rows=datasets[did]
        columns=list(rows[0]) if rows else []
        selections=',\n  '.join('json_extract(value, '+repr('$."'+key+'"')+') AS "'+key+'"' for key in columns)
        sql='SELECT\n  '+selections+'\nFROM json_each(:reviewed_json, '+repr('$."'+did+'"')+')\nORDER BY CAST(key AS INTEGER);'
        actual=[dict(r) for r in conn.execute(sql,{'reviewed_json':reviewed_json})]
        assert actual==rows, did+' 的SQL投影与已审数据不一致'
        parent=parents[item['sourceId']]
        sid='native_'+did
        native=dict(id=sid,label=item['title']+'｜数据与来源',path=PREFIX+'/reviewed_tables.json',
            query=dict(engine='SQLite 3 JSON1',language='sql',sql=sql,executed_at=now,
                description='展示层SQL投影；输入为本轮已审Python/人工分析行。上游证据：'+parent['path']+'。'+parent.get('query',{}).get('description',''),
                tables_used=[PREFIX+'/reviewed_tables.json',parent['path']],
                filters={'json_parameter':':reviewed_json = reviewed_tables.json 的UTF-8内容','dataset':did},
                transformation_context='原始实验：evaluation/run_match.py；机制重放：research/mechanism_analysis/analyze_trace.py；展示聚合：build_progress_report.py。此SQL只投影已审展示行。'))
        if parent.get('href'):
            native['href']=parent['href']
        manifest['sources'].append(native)
        item['sourceId']=sid
        sql_bindings.append(dict(dataset=did,source=parent['path'],sql=sql))
    conn.close()
    (HERE/'display_queries.json').write_text(json.dumps(sql_bindings,ensure_ascii=False,indent=2))
    artifact=dict(surface='report',manifest=manifest,snapshot=dict(version=1,generatedAt=now,status='ready',datasets=datasets),sources=manifest['sources'])
    (HERE/'artifact.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2))
    (HERE/'report_notes.json').write_text(json.dumps(dict(delivery='html',audience='technical',
        section_mapping='技术摘要→候选与机制→增量对比→重设计→金牌门→未决问题',
        chart_map=chart_map,validation='以report:deliver收据为准',
        table_rationale='逐候选增量和失败裁决需精确比较',
        authorized_actions='用户授权本地开发和新模拟比赛；未提交Kaggle或公开发布'),ensure_ascii=False,indent=2))
    print(json.dumps(dict(blocks=len(manifest['blocks']),charts=len(manifest['charts']),tables=len(manifest['tables']),datasets=len(datasets),bytes=(HERE/'artifact.json').stat().st_size)))

if __name__=='__main__':
    save()
