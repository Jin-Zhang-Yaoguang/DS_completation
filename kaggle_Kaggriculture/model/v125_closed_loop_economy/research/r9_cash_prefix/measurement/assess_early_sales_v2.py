#!/usr/bin/env python3
"""R9事前固定的只读早期自产收入指标；读取已存证据，不调用候选/引擎。"""
import argparse,collections,gzip,hashlib,importlib.util,json,math,sys,traceback
from datetime import datetime,timezone
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
VERSIONS=('V125-R8','V125-R9');OPPONENTS=('PASS','V120');SEEDS=(1950905901,1950905902,1950905903)
OUT_AUTHORIZED=False
EXPECTED={(v,o,s,t) for v in VERSIONS for o in OPPONENTS for s in SEEDS for t in (0,1)}
SHA={'assessor':'02c3041d3c3e34e7d5c9d2cf712e01522e70b563912b72b7d6444ef0e5737f0c','first_sale':'d353bd04bb4f86f492295a6d197389227934db87ff98414302538a04131a9c67','G1':'fe4ebdfebd652a93e0847d5330355f1280a5fcf91db4239f65bc57734dcf2399','analyzer':'cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def serialized_evidence(value):
 return json.loads(json.dumps(value,ensure_ascii=False,allow_nan=False))
def integer(value):return type(value) is int and value>=0
def assess(rows):
 """纯数据固定24格。零收入有效；缺重复格/来源不明/负数不准填零。"""
 issues=[];counts=collections.Counter((r['candidate_id'],r['opponent'],r['seed'],r['seat']) for r in rows)
 if set(counts)!=EXPECTED or any(v!=1 for v in counts.values()):issues.append('MISSING_DUPLICATE_OR_UNPLANNED_CELL')
 for r in rows:
  f=r['first_sale']
  if f.get('status')!='NUMERIC_COMPLETE':issues.append('PENDING_PROVENANCE:'+r['source_key'])
  if not integer(f.get('early_days_0_9_cash')) or not integer(f.get('early_days_0_9_units')):issues.append('INVALID_EARLY_CASH_OR_UNITS:'+r['source_key'])
 groups=[]
 for opponent in OPPONENTS:
  rr={v:[r for r in rows if r['candidate_id']==v and r['opponent']==opponent] for v in VERSIONS};valid=not issues
  stats={v:{'games':len(rr[v]),'cash_sum':sum(r['first_sale']['early_days_0_9_cash'] for r in rr[v]) if valid else None,'units_sum':sum(r['first_sale']['early_days_0_9_units'] for r in rr[v]) if valid else None,'zero_cash_games':sum(r['first_sale'].get('early_days_0_9_cash')==0 for r in rr[v])} for v in VERSIONS}
  seatstats={};nondecline=[]
  for seat in (0,1):
   ss={v:sum(r['first_sale']['early_days_0_9_cash'] for r in rr[v] if r['seat']==seat) if valid else None for v in VERSIONS}
   ss['nondecline']=ss['V125-R9']>=ss['V125-R8'] if valid else None;seatstats[str(seat)]=ss;nondecline.append(ss['nondecline'])
  parent=stats['V125-R8']['cash_sum'];new=stats['V125-R9']['cash_sum'];positive_parent=valid and parent>0
  threshold=5*new>=6*parent if positive_parent else None
  passed=threshold and all(nondecline) if threshold is not None else None
  groups.append({'opponent':opponent,'status':'NUMERIC_COMPLETE' if positive_parent else 'PENDING','reason':None if positive_parent else 'EVIDENCE_INVALID_OR_PARENT_CASH_SUM_ZERO','stats':stats,'per_seat':seatstats,'relative_cash_change':new/parent-1 if positive_parent else None,'at_least_20_percent':threshold,'primary_numeric_threshold_pass':passed})
 return {'issues':sorted(set(issues)),'data_integrity_pass':not issues,'groups':groups,'primary_mechanism_numeric_threshold_pass':all(g['primary_numeric_threshold_pass'] is True for g in groups),'expected_games':24,'observed_rows':len(rows),'rule':'各对手6局，5×R9现金sum≥6×R8现金sum；每席3局现金sum不退；parent0/PENDING不通过。'}

def boundary_atomic_costs(before_rows,after_rows,orders,events,seat,configuration):
 """官方固定规则：只有市场改变现金；土地按quadrants增量，剩余是雇工。"""
 result={'BUY_LAND':None,'HIRE':None,'status':'PENDING'}
 try:
  assert len(before_rows)==len(after_rows)==1
  before=before_rows[0];after=after_rows[0];farm=after['farms'][seat]
  assert before['step']==239 and before['day']==9 and before['hour']==23 and after['step']==240 and after['day']==10 and after['hour']==0
  old=before['quadrants'];new=farm['unlocked_quadrants'];assert new[:len(old)]==old and 1<=len(old)<=len(new)<=4
  requested=collections.Counter(o[0] for o in orders if isinstance(o,list) and o)
  bought=len(new)-len(old);assert bought<=requested['BUY_LAND']
  land=sum([1000,2000,4000][len(old)-1:len(new)-1]);sold=sum(e['quantity']*e['price'] for e in events if e['op']=='SELL');unit_buys=sum(e['quantity']*e['price'] for e in events if e['op'] in ('BUY_SEED','BUY_ANIMAL','BUY_PRODUCT'))
  atom=before['money']+sold-unit_buys-farm['money'];hire=atom-land
  assert type(hire) in (int,float) and math.isfinite(hire) and hire>=0 and int(hire)==hire
  count=before['hands'];assert type(count) is int and count>=0
  a,b=1,1
  for _ in range(count):a,b=b,a+b
  possible={0};fee=0
  for _ in range(requested['HIRE']):fee+=a*configuration.get('farmHandCostMult',1);possible.add(fee);a,b=b,a+b
  assert hire in possible
  result.update(BUY_LAND=land,HIRE=int(hire),status='NUMERIC_COMPLETE',cash_before=before['money'],cash_after=farm['money'],unit_sale_cash=sold,unit_buy_cash=unit_buys,atomic_cash_residual=atom,land_quadrants_added=bought,hire_requested=requested['HIRE'],post_eod_hand_count=len(farm.get('hands',[])),note='hour23 HIRE可付费后日终清空；费用由现金恒等式与土地增量核实，不按终态人数置0。')
 except (AssertionError,KeyError,TypeError,ValueError,IndexError) as exc:result['reason']='BOUNDARY_EVIDENCE_NOT_UNIQUELY_CLOSED:'+type(exc).__name__
 return result

def early_costs(game,events,trace,daily,configuration):
 """0..239真实单位事件；最后决策原请求+前后实际现金与土地数量拆分。"""
 seat=game['candidate_seat'];early=[e for e in events if e['seat']==seat and 0<=e['decision_step']<=239]
 costs=collections.Counter();quantities=collections.Counter();byday={};feed=0;placed=collections.Counter();plants=collections.Counter()
 for e in early:
  day=e['decision_step']//24
  if e['kind']=='market' and e['op'] in ('BUY_SEED','BUY_ANIMAL','BUY_PRODUCT'):
   assert type(e['quantity']) is int and e['quantity']>0 and type(e['price']) is int and e['price']>=0
   key=e['op']+':'+e['item'];cash=e['quantity']*e['price'];costs[key]+=cash;quantities[key]+=e['quantity'];byday.setdefault(str(day),collections.Counter())[key]+=cash
  elif e['kind']=='feed':feed+=e['quantity']
  elif e['kind']=='plant':plants[e['crop']]+=1
  elif e['kind']=='place_animal':placed[e['animal']]+=1
 snapshots=[pair[seat] for pair in game.get('daily',[]) if len(pair)==2 and pair[seat].get('step')==239]
 after=[r['states'][seat] for r in daily if r.get('recorded_step')==240]
 boundary=trace['actions'][239][seat];market=boundary.get('market',[]) if isinstance(boundary,dict) else []
 market=market[:configuration.get('maxMarketOrdersPerTurn',10)]
 tail=[e for e in early if e['decision_step']==239 and e['kind']=='market']
 end_costs=boundary_atomic_costs(snapshots,after,market,tail,seat,configuration)
 timed={}
 for op in ('BUY_LAND','HIRE'):
  if len(snapshots)!=1 or not isinstance(snapshots[0].get('audit_cumulative',{}).get('market'),dict):
   timed[op]={'status':'PENDING','cash':None,'reason':'缺step239官方累计市场账本'};continue
  ledger=snapshots[0]['audit_cumulative']['market'];value=sum(ledger.get(op+'_cash',{}).values());assert type(value) in (int,float) and math.isfinite(value) and value>=0 and int(value)==value
  terminal_value=end_costs.get(op)
  timed[op]={'status':'NUMERIC_COMPLETE' if terminal_value is not None else 'PENDING','cash':int(value)+terminal_value if terminal_value is not None else None,'source_snapshot_step':239,'executed_decisions_in_snapshot':[0,238],'through238_cash':int(value),'decision239_actual_cash':terminal_value,'boundary_evidence':end_costs}
 return {'window_decisions':[0,239],'unit_market_cash':dict(costs),'unit_market_quantities':dict(quantities),'daily_unit_market_cash':byday,'land_and_hire_cash':timed,'actual_early_feed_units':feed,'actual_early_placed_animals':dict(placed),'actual_early_plantings':dict(plants),'feed_cash_scope':'BUY_PRODUCT:WHEAT为实际小麦采购现金，可能用于喂养或再售；actual_feed_units为实际喂养量，不将库存耗用估值冒充当期现金。'}

def main():
 global OUT_AUTHORIZED
 ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--first-sale-dir',type=Path,required=True);ap.add_argument('--strength-dir',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir()),'REFUSE_EXISTING_OUTPUT';OUT_AUTHORIZED=True;inputs={};ownsha=sha(__file__)
 def pin(path,value=None):
  path=str(Path(path).resolve());h=sha(path)
  if value is not None:assert h==value,'SOURCE_SHA_MISMATCH:'+path
  if path in inputs:assert inputs[path]==h,'SOURCE_CHANGED:'+path
  inputs[path]=h
 def raw(path):
  path=str(Path(path).resolve());value=Path(path).read_bytes();h=hashlib.sha256(value).hexdigest()
  if path in inputs:assert inputs[path]==h,'SOURCE_CHANGED:'+path
  inputs[path]=h;return value
 def read(path):return json.loads(raw(path))
 freeze=read(HERE/'tool_freeze_v2.json');assert ownsha==freeze['aggregator_sha256'];plan=read(args.plan)
 assert plan['candidate']=='V125-R9' and set(plan['references'])=={'V125-R0','V125-R8'} and plan['seeds']==list(SEEDS) and plan['seats']==[0,1] and plan['opponents']==list(OPPONENTS)
 assert plan['engine_composite_sha256']=='77535fe62a057a70722db5c529d2c10cb0f0b08dd76c22a5d574758b6635be9f' and plan['runner_sha256']=='b92392363060f100c53c708dcf716515c39dc243b67526421ae47083a7bc0777'
 assert plan['formal_protocol_sha256']=='1fd7055674a2f79173b4bc8c466350cc57cba4f956206602f71dc8cb1288ebab'
 assert plan['expected_games']==36 and all(type(s) is int for s in plan['seeds']+plan['seats'])
 pin(HERE.parent/'development_protocol.json',plan['development_protocol_sha256'])
 paths={'assessor':ROOT/'evaluation/assess_paired_development.py','first_sale':ROOT/'research/r8_terminal_net_selection/summarize_first_produced_sale_v3.py','G1':ROOT/'evaluation/summarize_g1.py','analyzer':ROOT/'research/mechanism_analysis/analyze_trace.py'}
 modules={}
 for name,path in paths.items():
  pin(path,SHA[name])
  if name!='analyzer':
   spec=importlib.util.spec_from_file_location('r9_readonly_'+name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);modules[name]=m
 sm=read(args.strength_dir/'assessment_manifest.json');sr=read(args.strength_dir/'assessment.json')
 assert sm['assessor']['sha256']==SHA['assessor'] and sm['plan']['sha256']==inputs[str(args.plan.resolve())]
 for path,h in sm['source_files'].items():pin(path,h)
 sp,snapshots,errors,files=modules['assessor'].read_plan(args.plan.resolve());assert sp==plan
 for path,h in files.items():pin(path,h)
 recomputed=modules['assessor'].evaluate(sp,snapshots,errors);assert recomputed==sr,'STRENGTH_ASSESSMENT_NOT_REPRODUCIBLE'
 assert sr['data_integrity_pass'] is True and sr['observed_unique_cells']==36 and sr['expected_games']==36,'FULL_RUN_INTEGRITY_NOT_PASSED'
 fs=read(args.first_sale_dir/'first_sale.json');fm=read(args.first_sale_dir/'manifest.json');assert fm['script_sha256']==SHA['first_sale'];pin(args.first_sale_dir/'first_sale.json',fm['output_sha256'])
 for path,h in fm['input_files'].items():pin(path,h)
 expected={}
 for index,job in enumerate(plan['jobs']):
  if job['candidate_id'] not in VERSIONS:continue
  for g in snapshots[index]['games']:
   assert g['key'] not in expected
   expected[g['key']]=(job,snapshots[index]['manifest'],g)
 assert len(expected)==24 and len(fs['games'])==24 and {r['game_key'] for r in fs['games']}==set(expected) and len({r['game_key'] for r in fs['games']})==24,'FIRST_SALE_GAME_KEYS_NOT_EXACT24'
 rows=[]
 for f in fs['games']:
  job,rm,game=expected[f['game_key']];audit=Path(f['audit_directory']);verified,fp=modules['first_sale'].audit(audit);assert serialized_evidence(verified)==f,'FIRST_SALE_AUDIT_NOT_REPRODUCIBLE'
  for path,h in fp.items():pin(path,h)
  assert (f['seed'],f['seat'],f['source_sha256'])==(game['seed'],game['candidate_seat'],job['entry_sha256'])
  manifest=read(audit/'audit_manifest.json');assert Path(manifest['source_run_manifest']['path']).resolve()==(Path(job['output'])/'run_manifest.json').resolve()
  a=read(audit/'analysis.json');events=[json.loads(line) for line in gzip.decompress(raw(audit/'events.jsonl.gz')).decode().splitlines()];trace=json.loads(gzip.decompress(raw(game['trace']['path'])));own=a['seats'][game['candidate_seat']]
  assert manifest['candidate_entry_sha256']==job['entry_sha256'] and manifest['engine_composite_sha256']==plan['engine_composite_sha256']
  metrics=modules['G1'].game_metrics(game,rm,Path(job['output']),audit)
  daily=json.loads(gzip.decompress(raw(audit/'daily_states.json.gz')))
  assert rm['configuration'].get('turnsPerDay',24)==24
  rules=[(p,h) for p,h in rm['engine']['files'].items() if p.endswith('/envs/kaggriculture/kaggriculture.py')];assert len(rules)==1 and rules[0][1]=='bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e'
  rows.append({'candidate_id':job['candidate_id'],'opponent':job['opponent_label'],'seed':game['seed'],'seat':game['candidate_seat'],'source_key':game['key'],'first_sale':f,'G1_numeric_companions':metrics,'actual_flow':own['actual_flow'],'denominators':own['denominators'],'overflow':own['overflow'],'terminal_assets':own['terminal_assets'],'early_actual_costs':early_costs(game,events,trace,daily,rm['configuration']),'own_cash':game['candidate_reward'],'opponent_cash':game['opponent_reward'],'margin':game['margin'],'conditional_diagnostics':{'status':'UNINTERPRETED_CANDIDATE_SELF_REPORT_NOT_ACTUAL_INCOME','raw':game.get('strategy_diagnostics')},'official_daily_states':daily})
 report=assess(rows);report.update(schema='r9-early-real-self-produced-sales-v2',per_game=rows,candidate_calls=0,engine_steps=0,new_independent_matches=0,formal_G1_G2_Gold='NOT_ASSESSED',strength_guard_pass=sr['development_strength_guard_pass'],qualification='仅开发预筛主机制；主指标通过不能覆盖强度或G1/G2失败。')
 for path,h in inputs.items():assert sha(path)==h,'SOURCE_CHANGED_BEFORE_OUTPUT:'+path
 assert sha(__file__)==ownsha,'SCRIPT_CHANGED'
 dump(out/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':ownsha,'sources':inputs,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0});dump(out/'assessment.json',report)
 dump(out/'validation.json',{'source_files_unchanged':True,'frozen_full36_integrity_reproduced':True,'first_sale24_reproduced':True,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0})
 print(json.dumps({k:report[k] for k in ['data_integrity_pass','primary_mechanism_numeric_threshold_pass','groups','strength_guard_pass']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except BaseException:
  if OUT_AUTHORIZED and '--output' in sys.argv:
   out=Path(sys.argv[sys.argv.index('--output')+1]);out.mkdir(parents=True,exist_ok=True);(out/'failure.txt').write_text(traceback.format_exc());dump(out/'failure.json',{'data_integrity_pass':False,'primary_mechanism_numeric_threshold_pass':False,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,'reason':'源证据/结构/指纹/工程完整性失败；见failure.txt'})
  raise
