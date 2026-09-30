from pathlib import Path
import json,statistics as st
B=Path(__file__).resolve().parent
meta={r['episode_id']:r for r in json.loads((B/'episode_table.json').read_text())}
rows=[json.loads(p.read_text()) for p in (B/'metrics_v2').glob('*.json')]
def stats(xs):
 xs=sorted(xs)
 if not xs:return None
 q=st.quantiles(xs,n=4,method='inclusive') if len(xs)>1 else xs*3
 return {'n':len(xs),'median':st.median(xs),'q25':q[0],'q75':q[2],'min':min(xs),'max':max(xs),'mean':st.mean(xs)}
out={'scope':'Frozen PUBLIC episodes; decision steps are zero based; 24 steps/day. Snapshots at hour23 precede final daily decision and settlement. Cumulative ledger covers all decisions of the stated days. Gross receipts are not profit or investment payback.','groups':{}}
for sid in ['56156662','56216119']:
 rr=[r for r in rows if meta[r['episode_id']]['submission_id']==sid];g={'n':len(rr),'daily':[],'first_sales':{},'gross_milestones':{},'expansion':{},'opening_investment':{}}
 for day in [0,1,2,3,4,5,6,8,9,11]:
  ss=[next(d for d in r['daily'] if d['step']==day*24+23) for r in rr]
  z={'day_zero_based':day,'cash':stats([d['cash'] for d in ss]),'paired_cash_gap':stats([d['cash']-d['opponent_cash'] for d in ss]),'cash_lead_share':sum(d['cash']>d['opponent_cash'] for d in ss)/len(ss)}
  for k in ['hands','quadrants']:z[k]=stats([d[k] for d in ss])
  for k in ['COW','SHEEP','GOOSE','crops','animals']:
   z[k]=stats([d['board'].get(k,0) for d in ss]);z['opponent_'+k]=stats([d['opponent_board'].get(k,0) for d in ss])
  for label,products in [('nonwheat_receipts',['CARROT','TOMATO','STRAWBERRY','MELON','MILK','WOOL','EGG','FERTILIZER']),('animal_receipts',['MILK','WOOL','EGG']),('crop_receipts',['CARROT','TOMATO','STRAWBERRY','MELON'])]:
   z[label]=stats([sum(v for s in r['sales'] if s['step']<(day+1)*24 for k,v in s['cash'].items() if k in products) for r in rr])
  g['daily'].append(z)
 for prod in ['WHEAT','MILK','WOOL','MELON','STRAWBERRY','FERTILIZER','EGG','CARROT','TOMATO']:
  g['first_sales'][prod]=stats([min(s['step'] for s in r['sales'] if s['qty'].get(prod,0)>0) for r in rr if any(s['qty'].get(prod,0)>0 for s in r['sales'])])
 for threshold in [1000,3000,10000]:
  times=[]
  for r in rr:
   total=0
   for s in r['sales']:
    total+=sum(v for k,v in s['cash'].items() if k!='WHEAT')
    if total>=threshold:times.append(s['step']);break
  g['gross_milestones'][threshold]=stats(times)
 for i in [0,1]:g['expansion'][i+1]=stats([r['expansion'][i]['decision_step'] for r in rr if len(r['expansion'])>i])
 for k in ['BUY_ANIMAL_cash','BUY_SEED_cash','HIRE_cash','BUY_PRODUCT_cash','SELL_cash']:
  g['opening_investment'][k]=stats([sum(r['daily_ledger'].get('0',{}).get(k,{}).values()) for r in rr])
 out['groups'][sid]=g
(B/'startup_analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for sid,g in out['groups'].items():
 print('\nVERSION',sid,'n',g['n']);print('first_sales',g['first_sales']);print('milestones',g['gross_milestones']);print('invest',g['opening_investment'])
 for d in g['daily']:print('day',d['day_zero_based']+1,{k:round(d[k]['median'],2) for k in ['cash','paired_cash_gap','hands','quadrants','COW','SHEEP','GOOSE','crops','opponent_animals','opponent_crops','nonwheat_receipts','animal_receipts','crop_receipts']},'lead%',round(d['cash_lead_share']*100,1))
