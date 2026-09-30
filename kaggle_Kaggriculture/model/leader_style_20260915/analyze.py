"""从真实回放前帧重建确定性成交；逐帧对账。仅观察审计，不运行策略。"""
from pathlib import Path
import json,hashlib,collections,datetime,importlib.util,concurrent.futures,time,sys,traceback
B=Path(__file__).resolve().parent;ROOT=B.parents[2];OUT=B/'metrics_v2';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('prior_audit',ROOT/'kaggle_Kaggriculture/model_data/research_report_20260905/replay/audit_replays.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
C=collections.Counter
D=collections.defaultdict
def H(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
def norm(a):
 a=a or {};return {'farmer':a.get('farmer') or ['PASS'],'hands':a.get('hands') or [],'market':a.get('market') or []}
def inspect(item):
 eid,p=item;dest=OUT/f'{eid}.json'
 if dest.exists():return eid,'cached'
 try:
  raw=Path(p).read_bytes();r=json.loads(raw);steps=r['steps'];names=r['info']['TeamNames'];me=names.index('Majkel1337');opp=1-me
  assert r['info']['EpisodeId']==eid and len(steps)==720 and names.count('Majkel1337')==1
  assert r['module_version']=='1.32.7'
  # Official dataset serialization sorts dictionary keys. Recover carried-item
  # insertion order across observations before DROP, whose capacity rule uses it.
  orders=[[],[]]
  for frame in steps:
   for seat in (0,1):
    inventories=frame[seat]['observation']['private']['inventories'];new=[]
    for i,inv in enumerate(inventories):
     old=orders[seat][i] if i<len(orders[seat]) else []
     added=[k for k in inv if k not in old]
     assert len(added)<=1, (eid,seat,i,'multiple new carried items',added)
     keys=[k for k in old if k in inv]+added;new.append(keys)
     inventories[i]={k:inv[k] for k in keys}
    orders[seat]=new
  base={'episode_id':eid,'path':str(p),'sha256':hashlib.sha256(raw).hexdigest(),'module_version':r['module_version'],'configuration_sha256':H(r['configuration']),'seed':r['info'].get('seed'),'seat':me,'opponent':names[opp],'statuses':r.get('statuses'),'steps':len(steps),'cash':r['rewards'][me],'opponent_cash':r['rewards'][opp]}
  base['margin']=base['cash']-base['opponent_cash'];base['outcome']='W' if base['margin']>0 else 'L' if base['margin']<0 else 'T'
  ledgers=[D(C),D(C)];ops=C();changes=C();requested=D(C);sales_mod4=C();sales_hour=C();sale_frames=0;mincash=3000;maxhands=0;maxboard=C();expansion=[];lastq=1;cash_mismatches=[];last_plant=None
  acts=[norm(z[me].get('action')) for z in steps[1:]];units=[{'farmer':a['farmer'],'hands':a['hands']} for a in acts]
  unit_hash=[H(u)[:16] for u in units];market_hash=[H(a['market'])[:16] for a in acts]
  daily=[];daily_led=D(lambda:D(C));sales=[];opening_op=[]
  for t,st in enumerate(steps):
   ob=st[me]['observation'];f=ob['farms'][me];pr=ob['private'];mincash=min(mincash,f['money']);maxhands=max(maxhands,len(f['hands']));bc,dist,grid=audit.board(f)
   for k,v in bc.items():maxboard[k]=max(maxboard[k],v)
   if len(f['unlocked_quadrants'])>lastq:
    lastq=len(f['unlocked_quadrants']);expansion.append({'decision_step':t-1,'quadrants':lastq,'cash':f['money']})
   if t:
    pred,led,succ=audit.account_transition(steps[t-1],[z.get('action') for z in st],r['configuration'])
    for seat in (0,1):
     if abs(pred[seat]-st[seat]['observation']['farms'][seat]['money'])>1e-8:cash_mismatches.append([t,seat,pred[seat],st[seat]['observation']['farms'][seat]['money']])
     for k,v in led[seat].items():ledgers[seat][k].update(v)
    for k,v in led[me].items():daily_led[(t-1)//24][k].update(v)
    changes.update(succ[me]);a=acts[t-1]
    for ac in [a['farmer']]+a['hands']:
     if ac:ops[ac[0]]+=1
     if ac and ac[0]=='PLANT':last_plant=t-1
    for order in a['market']:
     if order and len(order)>2 and isinstance(order[2],(int,float)):requested[order[0]][str(order[1])]+=order[2]
    if sum(led[me]['SELL_qty'].values()):
     sale_frames+=1;sales_mod4[(t-1)%4]+=1;sales_hour[(t-1)%24]+=1
     sales.append({'step':t-1,'qty':dict(led[me]['SELL_qty']),'cash':dict(led[me]['SELL_cash'])})
   if t%24==23 or t in (0,719):
    daily.append({'step':t,'day':t//24,'cash':f['money'],'opponent_cash':ob['farms'][opp]['money'],'hands':len(f['hands']),'quadrants':lastq,'board':bc,'animal_distance':dist,'inventory':audit.totals(pr),'shops':ob['town']['unlocked_shops'],'prices':ob['market']['prices'],'opponent_board':audit.board(ob['farms'][opp])[0]})
  terminal=steps[-1][me]['observation'];private=terminal['private'];cashbridge=3000+sum(ledgers[me]['SELL_cash'].values())-sum(sum(v.values()) for k,v in ledgers[me].items() if k.endswith('_cash') and not k.startswith('SELL'))
  base.update({'cash_min':mincash,'max_hands':maxhands,'max_board':dict(maxboard),'expansion':expansion,'ledger':dict(ledgers[me]),'opponent_ledger':dict(ledgers[opp]),'cash_bridge':cashbridge,'cash_mismatches':cash_mismatches,'unit_requests':dict(ops),'unit_state_changes':dict(changes),'requested_qty':dict(requested),'sale_frames':sale_frames,'sale_mod4':dict(sales_mod4),'sale_hours':dict(sales_hour),'daily':daily,'daily_ledger':dict(daily_led),'sales':sales,'terminal_inventory':audit.totals(private),'terminal_seeds':private['seeds'],'terminal_unharvested':sum(g[3] for g in audit.board(terminal['farms'][me])[2]),'last_plant_step':last_plant,'last3days_cash_gain':base['cash']-steps[648][me]['observation']['farms'][me]['money'],'shops':terminal['town']['unlocked_shops'],'first_shop':steps[72][me]['observation']['town']['unlocked_shops'],'full_action_sha':H(acts),'unit_sequence_sha':H(units),'unit_frame_hashes':unit_hash,'market_frame_hashes':market_hash,'daily_unit_hashes':[H(units[t:t+24]) for t in range(0,719,24)],'daily_market_hashes':[H([a['market'] for a in acts[t:t+24]]) for t in range(0,719,24)],'opening':acts[:24]})
  dump(dest,base);return eid,'ok' if not cash_mismatches and cashbridge==base['cash'] else 'mismatch'
 except Exception as e:
  dump(OUT/f'{eid}.error.json',{'episode_id':eid,'error':str(e),'traceback':traceback.format_exc()});return eid,'error'
def available():
 rows=json.loads((B/'raw/local_inventory.json').read_text());p={r['episode_id']:r['path'] for r in rows}
 for f in (B/'replays').glob('episode-*-replay.json'):
  # CLI writes downloads via file rename; exclude very recently changing files.
  if time.time()-f.stat().st_mtime>10:p[int(f.name.split('-')[1])]=str(f)
 return p
if __name__=='__main__':
 seen=set();total=0
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
  while True:
   rows=available();todo=[(eid,p) for eid,p in rows.items() if eid not in seen and not (OUT/f'{eid}.json').exists()]
   if todo:
    print('batch',len(todo),flush=True)
    for eid,status in ex.map(inspect,todo,chunksize=1):
     seen.add(eid);total+=1
     if total%10==0 or status not in ('ok','cached'):print('audit',total,eid,status,flush=True)
   if (B/'raw/inventory.json').exists() and not todo:break
   if '--once' in sys.argv:break
   time.sleep(8)
 print('finished',len(list(OUT.glob('[0-9]*.json'))),flush=True)
