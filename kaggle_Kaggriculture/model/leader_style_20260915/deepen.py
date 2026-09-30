from pathlib import Path
import json,collections,statistics,concurrent.futures
B=Path(__file__).resolve().parent;S=json.loads((B/'raw/snapshot.json').read_text());meta={e['id']:sid for sid,es in S['episodes'].items() for e in es if 'PUBLIC' in e['type']};rows=[json.loads(p.read_text()) for p in (B/'metrics_v2').glob('*.json')];mean=statistics.mean

def early(r):
 if r['episode_id'] not in meta:return None
 d=json.loads(Path(r['path']).read_text());me=r['seat'];st=d['steps'];prev=st[21][me]['observation'];a=st[22][me]['action'];sid=meta[r['episode_id']]
 firstbuy=collections.Counter()
 for z in r['opening'][:3]:
  for o in z['market']:
   if o[0]=='BUY_ANIMAL':firstbuy[o[1]]+=o[2]
 return {'episode_id':r['episode_id'],'submission_id':sid,'seed21':prev['private']['seeds']['WHEAT'],'plant21':sum(x and x[0]=='PLANT' and x[1]=='WHEAT' for x in [a.get('farmer',[])]+a.get('hands',[])),'shops21':prev['town']['unlocked_shops'],'hand0_step21':a['hands'][0] if a.get('hands') else None,'step1_market':r['opening'][1]['market'],'first3_animal_requests':dict(firstbuy),'farmer_plant_positions':[st[t][me]['observation']['farms'][me]['farmer'] for t in [20,21]],'opening0':r['opening'][0]}
def cashgap(rr):
 c=collections.Counter()
 for r in rr:
  me=r['ledger'];op=r['opponent_ledger']
  for prod in ['WHEAT','CARROT','TOMATO','STRAWBERRY','MELON','EGG','MILK','WOOL','FERTILIZER']:
   c[prod]+=me.get('SELL_cash',{}).get(prod,0)-me.get('BUY_PRODUCT_cash',{}).get(prod,0)-op.get('SELL_cash',{}).get(prod,0)+op.get('BUY_PRODUCT_cash',{}).get(prod,0)
  for k in ['BUY_ANIMAL','BUY_SEED','HIRE','BUY_LAND']:c[k]+=sum(op.get(k+'_cash',{}).values())-sum(me.get(k+'_cash',{}).values())
 return {'n':len(rr),'margin_mean':mean(r['margin'] for r in rr),'components':{k:v/len(rr) for k,v in c.items()},'sum_check':sum(c.values())/len(rr)}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:early_rows=[r for r in ex.map(early,rows) if r]
out={'early_rows':early_rows,'groups':{},'examples':[]}
for sid in ['56156662','56216119']:
 rr=[r for r in rows if meta.get(r['episode_id'])==sid];er=[r for r in early_rows if r['submission_id']==sid];byseed=collections.Counter((r['seed21'],r['plant21'],str(r['hand0_step21'])) for r in er)
 g={'seed21_vs_requests': [{'seed_available':k[0],'plant_requests':k[1],'hand0':k[2],'n':v} for k,v in byseed.most_common()], 'early_animal_variants':[{'requests':json.loads(k),'n':v} for k,v in collections.Counter(json.dumps(r['first3_animal_requests'],sort_keys=True) for r in er).most_common()], 'first_action_unique':len(set(json.dumps(r['opening0']) for r in er)),'games':len(rr),'loss_gap':cashgap([r for r in rr if r['outcome']=='L']),'by_opponent':{o:cashgap([r for r in rr if r['opponent']==o]) for o in ['M & M & P & Q','Artem The Farmer 🍅','Unknown Mother-Goose'] if any(r['opponent']==o for r in rr)},'board_daily':[],'prefix_modes':[]}
 for day in [2,5,8,11,14,20,26,29]:
  for shop in sorted(set((r['first_shop'] or ['NONE'])[0] for r in rr)):
   ss=[r for r in rr if (r['first_shop'] or ['NONE'])[0]==shop];states=[next(d for d in r['daily'] if d['day']==day) for r in ss]
   g['board_daily'].append({'day':day,'first_shop':shop,'n':len(ss),**{a:mean(d['board'].get(a,0) for d in states) for a in ['COW','SHEEP','GOOSE','STRAWBERRY','WHEAT','MELON','CARROT','TOMATO']}})
 for lo,hi in [(0,20),(20,72),(72,144),(144,360),(360,648),(648,719)]:
  modes=[max(collections.Counter(r['unit_frame_hashes'][i] for r in rr).values())/len(rr) for i in range(lo,hi)]
  g['prefix_modes'].append({'start':lo,'end':hi,'mean_unit_mode_share':mean(modes)})
 out['groups'][sid]=g
 for r in sorted(rr,key=lambda r:r['margin'])[:2]:out['examples'].append({'episode_id':r['episode_id'],'submission_id':sid,'opponent':r['opponent'],'cash':r['cash'],'opponent_cash':r['opponent_cash'],'gap':cashgap([r]),'daily':r['daily']})
(B/'deep_analysis.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({sid:{k:v for k,v in g.items() if k not in ['board_daily']} for sid,g in out['groups'].items()},ensure_ascii=False,indent=2))
