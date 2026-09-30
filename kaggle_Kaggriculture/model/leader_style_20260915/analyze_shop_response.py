from pathlib import Path
import json,collections,statistics as st
B=Path(__file__).resolve().parent;meta={r['episode_id']:r['submission_id'] for r in json.loads((B/'episode_table.json').read_text())};rows=[json.loads(p.read_text()) for p in (B/'metrics_v2').glob('*.json')];out={}
for sid in ['56156662','56216119']:
 rr=[r for r in rows if meta[r['episode_id']]==sid];events=[]
 for r in rr:
  for j,shop in enumerate(r['shops']):
   day=3*(j+1);z={'episode_id':r['episode_id'],'reveal':j+1,'new_shop':shop,'previous':r['shops'][:j]}
   for period,days in [('before',range(day-3,day)),('after',range(day,min(day+3,30)))]:
    for op,prods in [('BUY_ANIMAL',['COW','SHEEP','GOOSE']),('BUY_SEED',['WHEAT','MELON','STRAWBERRY','CARROT','TOMATO'])]:
     for prod in prods:z[period+'_'+prod]=sum(r['daily_ledger'].get(str(d),{}).get(op+'_qty',{}).get(prod,0) for d in days)
   events.append(z)
 grouped=[]
 for reveal in range(1,9):
  for shop in sorted(set(e['new_shop'] for e in events)):
   es=[e for e in events if e['reveal']==reveal and e['new_shop']==shop]
   if es:grouped.append({'reveal':reveal,'shop':shop,'n':len(es),**{k:st.mean(e[k] for e in es) for k in es[0] if k.startswith(('before_','after_'))}})
 # Exact prior shop sequence strata for second reveal; contrasts YARN with other new shops.
 contrasts=[]
 for prefix in sorted(set(tuple(e['previous']) for e in events if e['reveal']==2)):
  yes=[e for e in events if e['reveal']==2 and tuple(e['previous'])==prefix and e['new_shop']=='YARN_STORE'];no=[e for e in events if e['reveal']==2 and tuple(e['previous'])==prefix and e['new_shop']!='YARN_STORE']
  if yes and no:contrasts.append({'previous':prefix,'yarn_n':len(yes),'other_n':len(no),'yarn_sheep':st.mean(e['after_SHEEP'] for e in yes),'other_sheep':st.mean(e['after_SHEEP'] for e in no),'yarn_cow':st.mean(e['after_COW'] for e in yes),'other_cow':st.mean(e['after_COW'] for e in no)})
 out[sid]={'events':events,'by_reveal_and_shop':grouped,'second_reveal_prior_matched':contrasts}
(B/'shop_response_analysis.json').write_text(json.dumps(out,indent=2))
for sid,g in out.items():
 print('VERSION',sid)
 for r in g['by_reveal_and_shop']:
  if r['reveal'] in [1,2,3]:print({k:round(v,2) if isinstance(v,float) else v for k,v in r.items() if k in ['reveal','shop','n','after_COW','after_SHEEP','after_GOOSE','after_STRAWBERRY','after_MELON']})
 print('matched',g['second_reveal_prior_matched'])
