#!/usr/bin/env python3
"""只读已冻结汇总和审计文件，制作结果报告；不调用候选或引擎。"""
import collections,hashlib,json,statistics
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
sources={}
def read(p):
 p=Path(p).resolve();raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest()
 if str(p) in sources:assert sources[str(p)]==h
 sources[str(p)]=h;return json.loads(raw)
d=read(P/'assessment_v2/assessment.json');am=read(P/'assessment_v2/manifest.json')
for path,h in am['sources'].items():assert sha(path)==h;sources[path]=h
rows=d['per_game'];groups=[];per_game=[]
for r in rows:
 ap=Path(r['audit_directory']);av=read(ap/'validation.json');plants=read(ap/'plant_lifetimes.json');assert sources[str(ap/'plant_lifetimes.json')]==av['files']['plant_lifetimes.json']
 crop=collections.Counter(e['crop'] for e in plants if e['seat']==r['seat']);assert sum(crop.values())==r['denominators']['plantings_all']
 metrics=r['G1_numeric_companions'];ledger=metrics['procurement_confirmation_and_targets']['actual_engine_ledger']
 expenses={k[:-5]:sum(v.values()) for k,v in ledger.items() if k.endswith('_cash') and k!='SELL_cash'};sales=sum(ledger['SELL_cash'].values());residual=3000+sales-sum(expenses.values())-r['own_cash'];assert residual==0
 early={}
 for day,values in r['first_sale']['daily'].items():
  if int(day)<=9:
   for item,v in values['by_item'].items():
    target=early.setdefault(item,collections.Counter());target.update(v)
 per_game.append({**{k:r[k] for k in ['version','opponent','seed','seat','source_key','own_cash','opponent_cash','margin']},'plantings_by_crop':dict(crop),'early_nonwheat_by_item':early,'expenses':expenses,'sales_cash':sales,'cash_bridge_initial_cash':3000,'cash_bridge_residual':residual})
for opp in ('PASS','V120'):
 for version in ('R7','R8'):
  rr=[r for r in rows if r['version']==version and r['opponent']==opp];pp=[r for r in per_game if r['version']==version and r['opponent']==opp]
  crop=collections.Counter();cost=collections.Counter();early={};overflow=collections.Counter();terminalqty=collections.Counter();natural=collections.Counter()
  for p,r in zip(pp,rr):
   crop.update(p['plantings_by_crop']);cost.update(p['expenses']);overflow.update(r['overflow']['eod_qty']);natural.update(r['actual_flow'].get('standing_yield_decay',{}));terminalqty.update(r['G1_numeric_companions']['terminal_liquidation']['terminal_mature_field_and_fertilizer_qty'])
   for item,v in p['early_nonwheat_by_item'].items():early.setdefault(item,collections.Counter()).update(v)
  seatcare={}
  for seat in (0,1):
   sr=[r for r in rr if r['seat']==seat];m=[r['G1_numeric_companions'] for r in sr];losskeys=['plant_loss','plant_eod_denominator','planting_denominator','animal_loss','animal_eod_denominator','placed_animal_denominator'];loss={k:sum(z['care_losses'][k] for z in m) for k in losskeys}
   closes=[z['terminal_liquidation'] for z in m];num=sum(z['numerator'] for z in closes);den=sum(z['denominator'] for z in closes)
   seatcare[str(seat)]={'care':loss,'first_watered':sum(z['planting_first_day_water']['numerator'] for z in m),'plantings':sum(z['planting_first_day_water']['denominator'] for z in m),'invalid':sum(z['action_validity']['numerator_confirmed_invalid'] for z in m),'actions':sum(z['action_validity']['denominator'] for z in m),'unknown_actions':sum(z['action_validity']['uncertain_count'] for z in m),'closing_sold_at_final_quote':num,'closing_denominator':den,'closing_ratio':num/den,'closing_all_material_closed':all(z['material_closed'] for z in closes),'closing_any_bought':any(z['final_day_bought'] for z in closes),'closing_remaining_value':sum(z['terminal_remaining_at_final_quote'] for z in closes),'closing_ready_destroyed_value':sum(z['ready_destroyed_at_final_quote'] for z in closes)}
  totalpurchased=sum(r['latency']['total']['purchased'] for r in rr);totalplaced=sum(r['latency']['total']['placed'] for r in rr)
  assert totalplaced==sum(r['denominators']['animal_placed'] for r in rr)
  groups.append({'opponent':opp,'version':version,'plantings_by_crop':dict(crop),'early_nonwheat_by_item':early,'expenses':dict(cost),'sales_cash':sum(p['sales_cash'] for p in pp),'own_cash_sum':sum(p['own_cash'] for p in pp),'opponent_cash_sum':sum(p['opponent_cash'] for p in pp),'cash_bridge_residual':sum(p['cash_bridge_residual'] for p in pp),'actual_animals_purchased':totalpurchased,'actual_animals_placed':totalplaced,'actual_product_harvest_placement_objects':sum(r['latency']['total']['placed_objects_with_actual_product_harvest'] for r in rr),'wait_sum':sum(r['latency']['total']['truncated_wait']['sum'] for r in rr),'overflow_units_by_item':dict(overflow),'natural_standing_yield_decay_all_days':dict(natural),'terminal_mature_products_qty':dict(terminalqty),'per_seat_g1_numeric_companions':seatcare})
for path,h in sources.items():assert sha(path)==h
result={'source_assessment':str(P/'assessment_v2/assessment.json'),'groups':groups,'per_game':per_game,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0}
dump(P/'companion_details.json',result)
lines=['# R8 完整开发块：首卖提前成立，强度仍失败','', '冻结的首卖主指标在两个对手块均满足阈值，全部 24 局来源完整。R8 每局首卖都是第 96 个决策步的一份肥料，elapsed 为 97；此后前 10 日实际自产收入有限。根任务的独立 36 局强度门已失败，R8 退役；这里不授予 G1/G2/金牌资格。','', '本次只重放 24 条已经保存的轨迹，共 17,256 次官方状态转移。候选调用 0、新独立比赛 0。原始运行的双方 719 次调用、无异常、官方/快引擎 parity 均已核对。','', '## 冻结主指标','', '| 对手 | R7 elapsed 总和 / 6 | R8 elapsed 总和 / 6 | 提前比例 | seat 0 / seat 1 均不晚 | 数值结果 |','|---|---:|---:|---:|---|---|']
for g in d['groups']:lines.append(f"| {g['opponent']} | {g['timing']['R7']['elapsed_sum']} / 6 = {g['timing']['R7']['T']:.4f} | {g['timing']['R8']['elapsed_sum']} / 6 = {g['timing']['R8']['T']:.4f} | {g['relative_T_reduction']:.4%} | 是 / 是 | 通过 |")
lines+=['','两席分别使用各自 3 个种子的平均。没有事件时按 719 完整纳入，不删局；本批无此类局。所有首卖由零初始、零外购非麦库存与官方真实采收/消耗/丢弃/SELL 的闭合物量证明，24 局均为 NUMERIC_COMPLETE。任何来源 PENDING 都会阻断对手组。','', '## 首卖之后的规模','', '| 对手 | 版本 | 首笔品种、量、收入 | 前 10 日自产非麦收入 / 数量（6 局合计） | 真实购入 / 投放动物 | 实际播种 | 日末溢出估值 |','|---|---|---|---:|---:|---:|---:|']
for g in d['groups']:
 for version in ('R7','R8'):
  c=g['companions'][version];r=c['raw_counts'];rr=[x for x in rows if x['opponent']==g['opponent'] and x['version']==version];cash=sorted({x['first_sale']['first_sale_cash'] for x in rr});basket='1 肥料' if version=='R8' else '12 甜瓜'
  lines.append(f"| {g['opponent']} | {version} | {basket}；{','.join(map(str,cash))} | {c['early_days_0_9_cash_sum']} / {c['early_days_0_9_units_sum']} | {r['latency_purchased']} / {r['latency_placed']} | {r['plantings_all']} | {r['overflow_quote_value']} |")
lines+=['','R8 每局前 10 日仅售 2 份肥料和 6 份羊毛：对 PASS 六局收入 9,034（每局均值 1,505.67），对 V120 为 8,238（每局 1,373）。R7 前 10 日均无自产非麦收入。首卖提前说明开局兑现更早，不证明资金约束或投资规模已解决。','', 'R8 对 PASS 的动物规模从 R7 的 12 只增至 30 只；对 V120 从 44 只变为 41 只，同时组成从 42 羊、2 牛转为 17 羊、24 牛。R8 的 71 只全部实际投放，全部对应置放对象实际采收到奶或羊毛；未投放和投放前遗失均为 0。对手块的规模差异不能简单归因为“买不起动物”。','', '| 对手 | 版本 | 麦 | 胡萝卜 | 番茄 | 草莓 | 甜瓜 |','|---|---|---:|---:|---:|---:|---:|']
for g in groups:lines.append('| '+g['opponent']+' | '+g['version']+' | '+' | '.join(str(g['plantings_by_crop'].get(c,0)) for c in ['WHEAT','CARROT','TOMATO','STRAWBERRY','MELON'])+' |')
lines+=['', '## 竞争现金与投入','', '| 对手 | 自身平均现金 R7 → R8 | 对手平均现金 R7 → R8 | 平均现金差变化（R8−R7） |','|---|---:|---:|---:|']
for g in d['groups']:
 a,b=g['companions']['R7'],g['companions']['R8'];lines.append(f"| {g['opponent']} | {a['mean_own_cash']:.2f} → {b['mean_own_cash']:.2f} | {a['mean_opponent_cash']:.2f} → {b['mean_opponent_cash']:.2f} | {b['mean_margin']-a['mean_margin']:+.2f} |")
lines+=['','对 V120，R8 自身平均现金虽增加 3,571，对手平均增加 22,978.83，故现金差反而恶化 19,407.83。只看自己的现金会误判竞争结果。以下费用均为官方实际成交/雇工扣款，非请求金额；六局初始现金合计 18,000，加销售减费用均严格等于终局现金。','', '| 对手 | 版本 | 总销售收入 | 动物 | 种子 | 商品采购 | 土地 | 雇工 |','|---|---|---:|---:|---:|---:|---:|---:|']
for g in groups:lines.append(f"| {g['opponent']} | {g['version']} | {g['sales_cash']} | "+' | '.join(str(g['expenses'].get(c,0)) for c in ['BUY_ANIMAL','BUY_SEED','BUY_PRODUCT','BUY_LAND','HIRE'])+' |')
lines+=['','## 实际分产品采收与销售','', '每格依次为“采收量 / 实际售量 / 成交收入 / 收入÷售量”。均价为整个对应六局的数量加权成交均价，不是挂单价；WHEAT 可能含外购转售，不能把其全部售出都称为自产。其余产品已通过来源闭合。','']
for g in d['groups']:
 lines += [f"### 对手 {g['opponent']}",'','| 产品 | R7 | R8 |','|---|---|---|']
 for item in sorted(set(g['companions']['R7']['products'])|set(g['companions']['R8']['products'])):
  vals=[]
  for v in ['R7','R8']:
   a=g['companions'][v]['products'].get(item,{});price=a.get('realized_mean_sale_price');vals.append(f"{a.get('harvested',0)} / {a.get('sell',0)} / {a.get('sell_cash',0)} / {price:.2f}" if price is not None else '无销售')
  lines.append(f"| {item} | "+' | '.join(vals)+' |')
 lines.append('')
lines+=['## 照护、仓容和末日','', '下列为 R8 两个对手、两个席位各自 3 局的原分子/原分母。它们是机制诊断，不替代正式 8 种子 × 双席 G1 块；采购逐笔目标与下一帧确认链仍全部 PENDING。','', '| 对手 | 席位 | 播种首水 | 无效 / 非PASS非移动动作 | 旱死 / 播种 / 株日 | 逃逸 / 投放 / 动物日 | 末日兑现（终局价分子 / 分母） |','|---|---:|---:|---:|---:|---:|---:|']
for g in groups:
 if g['version']!='R8':continue
 for seat,z in g['per_seat_g1_numeric_companions'].items():
  c=z['care'];lines.append(f"| {g['opponent']} | {seat} | {z['first_watered']}/{z['plantings']} | {z['invalid']}/{z['actions']}（不确定{z['unknown_actions']}） | {c['plant_loss']}/{c['planting_denominator']}/{c['plant_eod_denominator']} | {c['animal_loss']}/{c['placed_animal_denominator']}/{c['animal_eod_denominator']} | {z['closing_sold_at_final_quote']}/{z['closing_denominator']} = {z['closing_ratio']:.4%} |")
lines+=['','R8 全部 1,365 次实际播种首日获水，缺水死亡与动物逃逸均为 0。对 PASS 未喂食暴露 0/621；对 V120 为 3/766，仍没有逃逸。日末未浇水标记不等同旱死，成熟后停止水等情况保留原始暴露而不制造死亡。','', 'R8 对 PASS 日末溢出 6,748，对 V120 为 0；它是当时卖价估值，不是已经实现的利润损失。全部 12 局末日无外购商品、物料闭合，末日已经可售而销毁的量为 0，最终仓内产品全空；成熟田间产品及可收肥仍计入末日残留分母，没有因仓空忽略。末日逐局兑现率最低 97.1476%，并不等于所有资源都完全售清。','', '## 逐局首卖与规模','', '| 对手 | 版本 | seed末四位 | 席位 | elapsed | 前10日收入 | 动物采购 | 播种 | 自身 / 对手现金 |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:lines.append(f"| {r['opponent']} | {r['version']} | {str(r['seed'])[-4:]} | {r['seat']} | {r['first_sale']['restricted_elapsed_decisions']} | {r['first_sale']['early_days_0_9_cash']} | {r['latency']['total']['purchased']} | {r['denominators']['plantings_all']} | {r['own_cash']:.0f} / {r['opponent_cash']:.0f} |")
lines+=['','## 校验和更正记录','', '所有 24 条官方重放校验、源候选/运行器/引擎 SHA、原动作轨迹 SHA、首卖工具来源指纹均保存于对应 manifest。根开发块的强度裁决独立保存，本报告不复制或重解释其阈值。','', '初版聚合器 247a187f 的伴随 raw_counts.animal_placed 重复加了 analyzer 投放数与 latency 投放数；原文件和原输出完整保留，不能引用其中这个计数。修正版 00e8f2df 将 latency 计数改为独立前缀，原始逐局数据与全部主机制结果逐字典比较一致；详见 companion_v1_failure.json 和 v2_regression_validation.json。只读重汇总，候选/引擎调用均为 0。','', '正式引用 assessment_v2/assessment.json、companion_details.json、all_24_first_sale/first_sale.json；assessment/ 仅保留初版更正证据。']
(P/'REPORT.md').write_text('\n'.join(lines)+'\n')
dump(P/'report_manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'sources':sources,'outputs':{str(P/n):sha(P/n) for n in ['REPORT.md','companion_details.json']},'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
print(json.dumps({'groups':groups,'output':str(P/'REPORT.md')},ensure_ascii=False,indent=2))
