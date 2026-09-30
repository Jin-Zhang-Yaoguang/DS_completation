#!/usr/bin/env python3
"""只读已经冻结计算的R9指标，输出轻量报告。"""
import collections,hashlib,json,statistics
from pathlib import Path
from datetime import datetime,timezone
P=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def main():
 source=P/'assessment_v2/assessment.json';source_sha=sha(source);d=json.loads(source.read_text());lpath=P/'all_24_latency/results.json';ls=sha(lpath);lat=json.loads(lpath.read_text());lm=json.loads((P/'all_24_latency/manifest.json').read_text());lv=json.loads((P/'all_24_latency/validation.json').read_text());assert sha(lpath)==lv['files']['results.json'];assert lm['script']['sha256']=='d67e06b4995a946f05e2baff0d73470a176fca8a696d6ac5b8b9aaad2736cf55'
 for item in lm['sources']:
  for f,h in item['files'].items():assert sha(f)==h
 lmap={r['source_game_key']:r for r in lat};rows=d['per_game'];assert len(rows)==24 and len(lmap)==24
 groups=[];per_game=[]
 for r in rows:
  g1=r['G1_numeric_companions'];ledger=g1['procurement_confirmation_and_targets']['actual_engine_ledger'];fullcost={op:sum(ledger.get(op+'_cash',{}).values()) for op in ['BUY_SEED','BUY_ANIMAL','BUY_PRODUCT','BUY_LAND','HIRE']};sales=sum(ledger['SELL_cash'].values());assert 3000+sales-sum(fullcost.values())==r['own_cash']
  early=r['early_actual_costs'];e={op:sum(v for k,v in early['unit_market_cash'].items() if k.startswith(op+':')) for op in ['BUY_SEED','BUY_ANIMAL','BUY_PRODUCT']};e.update({op:z['cash'] for op,z in early['land_and_hire_cash'].items()});lt=lmap[r['source_key']]['seats'][r['seat']]['total'];close=g1['terminal_liquidation'];fs=r['first_sale']
  per_game.append({'candidate_id':r['candidate_id'],'opponent':r['opponent'],'seed':r['seed'],'seat':r['seat'],'source_key':r['source_key'],'early_cash':fs['early_days_0_9_cash'],'early_units':fs['early_days_0_9_units'],'first_elapsed':fs['restricted_elapsed_decisions'],'first_items':fs['first_sale_items'],'first_cash':fs['first_sale_cash'],'early_costs':e,'early_feed_units':early['actual_early_feed_units'],'early_planted':early['actual_early_plantings'],'early_placed':early['actual_early_placed_animals'],'full_costs':fullcost,'full_sale_cash':sales,'animal':lt,'own_cash':r['own_cash'],'opponent_cash':r['opponent_cash'],'margin':r['margin'],'closing':{'ratio':close['ratio'],'sold_value':close['numerator'],'denominator':close['denominator'],'remaining_value':close['terminal_remaining_at_final_quote'],'ready_destroyed_value':close['ready_destroyed_at_final_quote'],'material_closed':close['material_closed'],'bought':close['final_day_bought']}})
 for opponent in ('PASS','V120'):
  for v in ('V125-R8','V125-R9'):
   rr=[r for r in rows if r['candidate_id']==v and r['opponent']==opponent];pp=[r for r in per_game if r['candidate_id']==v and r['opponent']==opponent];assert len(rr)==len(pp)==6
   ec={op:sum(p['early_costs'][op] for p in pp) if all(p['early_costs'][op] is not None for p in pp) else None for op in pp[0]['early_costs']};fc={op:sum(p['full_costs'][op] for p in pp) for op in pp[0]['full_costs']};den=collections.Counter();earlypl=collections.Counter();earlyan=collections.Counter();animals=collections.Counter();products={};earlyproducts={};overflow=collections.Counter()
   for r,p in zip(rr,pp):
    den.update({k:x for k,x in r['denominators'].items() if type(x) is int});earlypl.update(p['early_planted']);earlyan.update(p['early_placed']);animals.update(r['actual_flow'].get('buy_animal',{}));overflow.update(r['overflow']['eod_qty'])
    for item in set(r['actual_flow'].get('harvested',{}))|set(r['actual_flow'].get('sell',{})):
     x=products.setdefault(item,collections.Counter());x['harvested']+=r['actual_flow'].get('harvested',{}).get(item,0);x['sold']+=r['actual_flow'].get('sell',{}).get(item,0);x['cash']+=r['actual_flow'].get('sell_cash',{}).get(item,0)
    for day,z in r['first_sale']['daily'].items():
     if int(day)<10:
      for item,q in z['by_item'].items():earlyproducts.setdefault(item,collections.Counter()).update(q)
   bought=sum(p['animal']['purchased'] for p in pp);placed=sum(p['animal']['placed'] for p in pp);assert placed==den['animal_placed'];wait=sum(p['animal']['truncated_wait']['sum'] for p in pp)
   sc={}
   for seat in (0,1):
    mm=[r['G1_numeric_companions'] for r in rr if r['seat']==seat];cl=[z['terminal_liquidation'] for z in mm];num=sum(z['numerator'] for z in cl);de=sum(z['denominator'] for z in cl)
    sc[str(seat)]={'first_water':sum(z['planting_first_day_water']['numerator'] for z in mm),'plantings':sum(z['planting_first_day_water']['denominator'] for z in mm),'invalid':sum(z['action_validity']['numerator_confirmed_invalid'] for z in mm),'actions':sum(z['action_validity']['denominator'] for z in mm),'unknown_actions':sum(z['action_validity']['uncertain_count'] for z in mm),'care':{k:sum(z['care_losses'][k] for z in mm) for k in ['plant_loss','plant_eod_denominator','planting_denominator','animal_loss','animal_eod_denominator','placed_animal_denominator']},'closing_sold_value':num,'closing_denominator':de,'closing_ratio':num/de if de else None,'closing_all_material_closed':all(z['material_closed'] for z in cl),'closing_any_purchase':any(z['final_day_bought'] for z in cl),'closing_ready_destroyed':sum(z['ready_destroyed_at_final_quote'] for z in cl)}
   groups.append({'candidate_id':v,'opponent':opponent,'early_cash_sum':sum(p['early_cash'] for p in pp),'early_units_sum':sum(p['early_units'] for p in pp),'early_cash_by_item':earlyproducts,'early_actual_costs':ec,'early_actual_plantings':dict(earlypl),'early_actual_placed_animals':dict(earlyan),'early_actual_feed_units':sum(p['early_feed_units'] for p in pp),'full_costs':fc,'full_sale_cash':sum(p['full_sale_cash'] for p in pp),'full_buy_animals':dict(animals),'full_animal_purchased':bought,'full_animal_placed':placed,'full_animal_lost':sum(p['animal']['lost_before_place'] for p in pp),'full_animal_unplaced':sum(p['animal']['still_in_transit'] for p in pp),'actual_main_product_placement_objects':sum(p['animal']['placed_objects_with_actual_product_harvest'] for p in pp),'animal_wait_sum':wait,'animal_wait_mean':wait/bought if bought else None,'denominators':dict(den),'products':{k:{**x,'realized_sale_mean':x['cash']/x['sold'] if x['sold'] else None} for k,x in products.items()},'mean_own_cash':statistics.mean(p['own_cash'] for p in pp),'mean_opponent_cash':statistics.mean(p['opponent_cash'] for p in pp),'mean_margin':statistics.mean(p['margin'] for p in pp),'overflow_units':dict(overflow),'overflow_quote_value':sum(r['overflow']['eod_quote_value'] for r in rr),'per_seat_g1_numeric':sc,'closing_min_individual':min(p['closing']['ratio'] for p in pp),'closing_final_remaining_value':sum(p['closing']['remaining_value'] for p in pp),'procurement_status_counts':dict(collections.Counter(r['G1_numeric_companions']['procurement_confirmation_and_targets']['status'] for r in rr))})
 summary={'role':'R9_COMPLETE_DEVELOPMENT_MECHANISM_NOT_GOLD','primary':d['groups'],'data_integrity_pass':d['data_integrity_pass'],'primary_mechanism_numeric_threshold_pass':d['primary_mechanism_numeric_threshold_pass'],'strength_guard_pass':d['strength_guard_pass'],'groups':groups,'per_game':per_game,'official_saved_actions_replayed':17256,'candidate_calls':0,'new_independent_matches':0,'measurement_sha256':'556a00b14d842e85609d7a75fc97209474182b32d0b232931abc70a5bc718797','assessment_sha256':source_sha}
 dump(P/'summary.json',summary)
 lines=['# R9 完整新块：早收入增加，强度仍未通过','', '固定1950905901/5902/5903、双席、PASS/V120的R8/R9共24条保存轨迹已全部官方重放，合计17,256步；候选调用0、新独立比赛0。根的36局冻结强度结果完整性通过、强度未通过；本审计的主机制阈值通过，二者分别保留，不授予正式G1/G2/金牌。','', '| 对手 | R8前10日实际自产收入/数量（6局合计） | R9收入/数量 | 收入变化 | 两席各3局不退 |','|---|---:|---:|---:|---|']
 for g in d['groups']:
  a,b=g['stats']['V125-R8'],g['stats']['V125-R9'];lines.append(f"| {g['opponent']} | {a['cash_sum']}/{a['units_sum']} | {b['cash_sum']}/{b['units_sum']} | {g['relative_cash_change']:.4%} | 是/是 |")
 lines+=['','主窗始终为决策0..239。全部24局自产来源NUMERIC_COMPLETE，零早卖局为0；没有删局。整数规则5×R9总收入≥6×R8总收入未改变，逐席也独立满足。根完整36局包含R0，它只参与独立强度门，本表未混入R0。','', '## 实际早期投入','', '| 对手 | 版本 | 种子 | 动物 | 商品（小麦） | 土地 | 雇工 | 早期播种 / 动物投放 |','|---|---|---:|---:|---:|---:|---:|---:|']
 for g in groups:
  e=g['early_actual_costs'];lines.append(f"| {g['opponent']} | {g['candidate_id']} | "+' | '.join(str(e[k]) for k in ['BUY_SEED','BUY_ANIMAL','BUY_PRODUCT','BUY_LAND','HIRE'])+f" | {sum(g['early_actual_plantings'].values())} / {sum(g['early_actual_placed_animals'].values())} |")
 lines+=['','以上全为实际支出；小麦采购可能用于饲料或再售，不把消耗已有小麦的机会成本当现金。HIRE/LAND补核239→240实际现金/土地变化，不能把step239前累计错当完整十日，也不能因日终手数清零把已付工资记零。候选条件信用与prefix预测原样保留在大JSON中，它们不是实际收入。','', '## 规模、照护与仓容','', '| 对手 | 版本 | 动物采购 / 投放 / 实采主产品对象 | 截断等待均值 | 首日水 / 播种 | 旱死 / 逃逸 | 溢出报价估值 |','|---|---|---:|---:|---:|---:|---:|']
 for g in groups:
  z=g['denominators'];lines.append(f"| {g['opponent']} | {g['candidate_id']} | {g['full_animal_purchased']}/{g['full_animal_placed']}/{g['actual_main_product_placement_objects']} | {g['animal_wait_mean']:.4f} | {z['planting_day_watered']}/{z['plantings_all']} | {z['plant_eod_drought_deaths']}/{z['animal_eod_escapes']} | {g['overflow_quote_value']} |")
 lines+=['','动物等待以总等待/真实采购数计算，未投放/丢失按719截断；投放对象实际奶/羊毛/蛋采收与预测首产区分。溢出是丢弃当时的卖价估值，并非已实现现金损失。分席动作、照护原分母与末日闭合见summary.json，不以席位之间抵消异常。采购逐笔净目标与确认链缺证据仍PENDING；该开发块也不是正式8种子×双席G1块。','', '## 双方现金','', '| 对手 | 版本 | 自身平均现金 | 对手平均现金 | 平均分差 |','|---|---|---:|---:|---:|']
 for g in groups:lines.append(f"| {g['opponent']} | {g['candidate_id']} | {g['mean_own_cash']:.2f} | {g['mean_opponent_cash']:.2f} | {g['mean_margin']:.2f} |")
 lines+=['','完整强度判断必须对照双方现金差，不能以自身收入或现金增加替代。','', '## 每种真实产物','', '每格为采收量/实际售量/成交收入/成交收入÷售量。WHEAT包括潜在外购转售，不能全部称为自产。','']
 for opp in ('PASS','V120'):
  a,b=[g for g in groups if g['opponent']==opp];lines += [f'### {opp}','','| 产品 | R8 | R9 |','|---|---|---|']
  for item in sorted(set(a['products'])|set(b['products'])):
   values=[]
   for g in [a,b]:
    z=g['products'].get(item);values.append(f"{z['harvested']}/{z['sold']}/{z['cash']}/{z['realized_sale_mean']:.2f}" if z and z['sold'] else '0/0/0/—')
   lines.append('| '+item+' | '+' | '.join(values)+' |')
  lines.append('')
 lines+=['## 序列化修复保留证据','', '原冻结measurement346在第一条记录误报FIRST_SALE_AUDIT_NOT_REPRODUCIBLE：冻结v3内存daily以整数日为键，JSON对象回读后键为字符串。逐字段确认仅daily表示不同。原脚本、tool_freeze及assessment/failure完整保留。','', '派生v2工具556a00b只将audit结果按v3 JSON形式归一后做全字段严格比较；34项验证通过，包括24条真实证据完全一致，篡改daily现金或首笔basket仍被拒绝。主指标、域检查、费用函数AST未变。v2运行在assessment_v2/，无新增引擎或候选调用。','', '初次v2测试继承的一句“没有R9轨迹”来源说明已在test_measurement_v2_final及validation_v2_final更正；它实际只读了已完成24条R8/R9证据，无新比赛。旧测试稿保留，不作为正式来源说明。','', '根/HTML优先读取summary.json和本报告；assessment_v2/assessment.json保留逐局官方状态及未解释的候选自报预测。']
 (P/'REPORT.md').write_text('\n'.join(lines)+'\n')
 assert sha(source)==source_sha and sha(lpath)==ls
 dump(P/'compact_report_manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'assessment_sha256':source_sha,'latency_results_sha256':ls,'outputs':{n:sha(P/n) for n in ['summary.json','REPORT.md']},'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
 print(json.dumps({'groups':[{k:g[k] for k in ['candidate_id','opponent','early_actual_costs','full_animal_purchased','full_animal_placed','animal_wait_mean','denominators','mean_own_cash','mean_opponent_cash','mean_margin','overflow_quote_value','closing_min_individual']} for g in groups]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
