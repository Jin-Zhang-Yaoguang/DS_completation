from pathlib import Path
from collections import Counter,defaultdict
import json,statistics,math,datetime,hashlib
B=Path(__file__).resolve().parent
C=Counter
mean=lambda x:statistics.mean(x) if x else None
med=lambda x:statistics.median(x) if x else None
def freq(x):return dict(C(x).most_common())
def subcount(rows):
 n=len(rows);return {'n':n,'wins':sum(r['outcome']=='W' for r in rows),'losses':sum(r['outcome']=='L' for r in rows),'draws':sum(r['outcome']=='T' for r in rows),'win_rate':mean([r['outcome']=='W' for r in rows]),'cash_median':med([r['cash'] for r in rows]),'margin_median':med([r['margin'] for r in rows]),'margin_mean':mean([r['margin'] for r in rows])}
def aggregate(rows):
 out=subcount(rows);n=len(rows)
 if not n:return out
 led=defaultdict(C);req=C();suc=C();mod=C();mx=C()
 for r in rows:
  for k,v in r['ledger'].items():led[k].update(v)
  req.update(r['unit_requests']);suc.update(r['unit_state_changes']);mod.update(r['sale_mod4'])
 prods=[]
 for p in ['WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER']:
  q=led['SELL_qty'][p];rev=led['SELL_cash'][p];buy=led['BUY_PRODUCT_cash'][p]
  prods.append({'product':p,'sell_qty_mean':q/n,'sell_cash_mean':rev/n,'buy_cash_mean':buy/n,'net_product_cash_mean':(rev-buy)/n,'realized_price':rev/q if q else None})
 out.update({'by_seat':{str(s):subcount([r for r in rows if r['seat']==s]) for s in (0,1)},'opponents':len(set(r['opponent'] for r in rows)),'cash_min_median':med([r['cash_min'] for r in rows]),'cash_zero_n':sum(r['cash_min']==0 for r in rows),'max_hands':freq(r['max_hands'] for r in rows),'max_animals_median':med([r['max_board'].get('animals',0) for r in rows]),'max_crops_median':med([r['max_board'].get('crops',0) for r in rows]),'land_end':freq(1+len(r['expansion']) for r in rows),'expansion_step_1':freq(r['expansion'][0]['decision_step'] if r['expansion'] else None for r in rows),'expansion_step_2':freq(r['expansion'][1]['decision_step'] if len(r['expansion'])>1 else None for r in rows),'hire_total':freq(r['ledger']['HIRE_qty'].get('hands',0) for r in rows),'hire_cash':freq(r['ledger']['HIRE_cash'].get('hands',0) for r in rows),'products':prods,'cash_bridge_mean':{'start':3000,'sell':sum(led['SELL_cash'].values())/n,**{k:sum(v.values())/n for k,v in led.items() if k.endswith('_cash') and k!='SELL_cash'},'end':mean([r['cash'] for r in rows])},'unit_requests':dict(req),'unit_changes':dict(suc),'move_fraction':sum(req[x] for x in ['NORTH','SOUTH','EAST','WEST'])/sum(req.values()),'pass_fraction':req['PASS']/sum(req.values()),'sale_mod4':dict(mod),'sales_turns_mean':mean([r['sale_frames'] for r in rows]),'terminal_inventory_median':med([sum(r['terminal_inventory'].values()) for r in rows]),'terminal_unharvested_median':med([r['terminal_unharvested'] for r in rows]),'last3days_gain_median':med([r['last3days_cash_gain'] for r in rows]),'last3days_fraction_median':med([r['last3days_cash_gain']/r['cash'] for r in rows if r['cash']]),'last_plant_range':[min(r['last_plant_step'] for r in rows if r['last_plant_step'] is not None),max(r['last_plant_step'] for r in rows if r['last_plant_step'] is not None)],'unique_units':len(set(r['unit_sequence_sha'] for r in rows)),'unique_full':len(set(r['full_action_sha'] for r in rows)),'first_shop':freq((r['first_shop'] or ['NONE'])[0] for r in rows)})
 # Exact per-frame mode concentration, independent of result selection.
 out['frame_modes']=[{'step':t,'unit_unique':len(C(r['unit_frame_hashes'][t] for r in rows)),'unit_mode_share':max(C(r['unit_frame_hashes'][t] for r in rows).values())/n,'market_unique':len(C(r['market_frame_hashes'][t] for r in rows)),'market_mode_share':max(C(r['market_frame_hashes'][t] for r in rows).values())/n} for t in range(719)]
 out['by_first_shop']=[]
 for shop in out['first_shop']:
  rr=[r for r in rows if (r['first_shop'] or ['NONE'])[0]==shop];z={'shop':shop,**subcount(rr)}
  for animal in ['COW','SHEEP','GOOSE']:z[animal+'_bought_mean']=mean([r['ledger']['BUY_ANIMAL_qty'].get(animal,0) for r in rr])
  for prod in ['MILK','WOOL','STRAWBERRY']:z[prod+'_cash_mean']=mean([r['ledger']['SELL_cash'].get(prod,0) for r in rr])
  out['by_first_shop'].append(z)
 out['blocks']=[{'day':day,'unique_unit_sequences':len(set(r['daily_unit_hashes'][day] for r in rows)),'unique_market_sequences':len(set(r['daily_market_hashes'][day] for r in rows)),'unit_mode_share':max(C(r['daily_unit_hashes'][day] for r in rows).values())/n} for day in range(30)]
 return out
snap=json.loads((B/'raw/snapshot.json').read_text());meta={}
for sid,rs in snap['episodes'].items():
 for e in rs:
  if 'PUBLIC' in e['type']:meta[e['id']]={**e,'submission_id':sid}
rows=[];issues=[]
for p in sorted((B/'metrics_v2').glob('*.json')):
 if '.error.' in p.name:issues.append(json.loads(p.read_text()));continue
 r=json.loads(p.read_text());r.update(meta.get(r['episode_id'],{'submission_id':'historical','endTime':None}));r['partition_date']=next((v[5:] for v in Path(r['path']).parts if v.startswith('date=')),None);rows.append(r)
summary={'asof':snap['at'],'n':len(rows),'errors':issues,'cash_mismatch_n':sum(len(r['cash_mismatches']) for r in rows),'cash_checks':len(rows)*719*2,'bad_status':sum(r['statuses']!=['DONE','DONE'] for r in rows),'configuration_hashes':freq(r['configuration_sha256'] for r in rows),'groups':{},'rank_snapshot':snap['leaderboard'][:5]}
for sid in ['56156662','56216119','historical']:
 rr=sorted([r for r in rows if r['submission_id']==sid],key=lambda r:r['endTime'] or str(r['episode_id']));s=aggregate(rr)
 if rr:
  s['first40']=subcount(rr[:40]);s['games41to80']=subcount(rr[40:80]);s['latest40']=subcount(rr[-40:]);s['opponent_results']=[{'opponent':o,**subcount([r for r in rr if r['opponent']==o])} for o,c in C(r['opponent'] for r in rr).most_common()]
  s['by_date']=[{'date':day,**subcount([r for r in rr if str(r['endTime'])[:10]==day])} for day in sorted(set(str(r['endTime'])[:10] for r in rr))]
  s['worst']=[{k:r[k] for k in ['episode_id','seat','opponent','cash','opponent_cash','margin','first_shop','shops','cash_min','max_hands','ledger','terminal_inventory','last3days_cash_gain']} for r in sorted(rr,key=lambda r:r['margin'])[:6]]
 if sid=='historical':
  for k in ['first40','games41to80','latest40','by_date']:s.pop(k,None)
  s['partition_dates']=freq(r['partition_date'] for r in rr)
 summary['groups'][sid]=s
(B/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
(B/'episode_table.json').write_text(json.dumps([{k:r[k] for k in ['episode_id','submission_id','endTime','seat','opponent','cash','opponent_cash','margin','outcome','path','sha256']} for r in rows],ensure_ascii=False,indent=2))
print(json.dumps({'n':len(rows),'errors':len(issues),'mismatches':summary['cash_mismatch_n'],'groups':{sid:{k:s.get(k) for k in ['n','wins','losses','cash_median','max_hands','hire_total','hire_cash','unique_units','cash_zero_n','max_animals_median','max_crops_median']} for sid,s in summary['groups'].items()}},ensure_ascii=False,indent=2))
