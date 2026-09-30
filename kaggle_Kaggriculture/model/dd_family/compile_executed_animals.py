"""Extract successful animal transfers from an unmodified official replay run.

Instrumentation only observes official function results and caller slot indices.
Zero-fill market placeholders retain opponent order alignment.
"""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,hashlib,importlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent

def run(k):
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  from kaggle_environments import make
  eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
 sys.path.insert(0,str(B/'dde'));import action_space as a
 row=json.loads((B/'dde/training_manifest.json').read_text())['episodes'][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat'];cfg=dict(rep['configuration']);cfg['seed']=rep['info']['seed']
 env=make('kaggriculture',configuration=cfg);env.reset(2);now=[0]
 ut=np.zeros((719,16),np.int16);uq=np.zeros((719,16),np.int32);mt=np.zeros((719,10),np.int16);mq=np.zeros((719,10),np.int32)
 stock=collections.defaultdict(list);bags=[collections.defaultdict(list) for _ in range(16)];groups=[];parent=[];annotations=[];builds=collections.defaultdict(list);buy_slots={};stats=collections.Counter()
 def root(g):
  while parent[g]!=g:g=parent[g]
  return g
 def unite(ids):
  assert ids
  r=root(ids[0])
  for g in ids:parent[root(g)]=r
  return r
 originals={n:getattr(eng,n) for n in ['_apply_unit_action','_commit_unit','_drop_inventories_to_shed','_do_hire','_do_buy_land']}
 def unit(farm,private,idx,action,*args,**kwargs):
  frame=sys._getframe(1);player=frame.f_locals['i']
  if player!=seat:return originals['_apply_unit_action'](farm,private,idx,action,*args,**kwargs)
  t=now[0];xy=tuple(eng._farmer_position(farm,idx));x,y=xy
  before=(list(xy),copy.deepcopy(farm['tiles'][y][x]),dict(private['inventories'][idx]),dict(private['shed']),dict(private['seeds']))
  result=originals['_apply_unit_action'](farm,private,idx,action,*args,**kwargs)
  after=(list(eng._farmer_position(farm,idx)),farm['tiles'][y][x],private['inventories'][idx],private['shed'],private['seeds'])
  changed=before!=after
  if not changed:
   if action and action[0]!='PASS':stats['ineffective_units']+=1
   return result
  tok,q,known=a.unit_token(action);assert known;ut[t,idx]=tok;uq[t,idx]=int(action[2]) if len(action)>2 else 1;op=action[0]
  if op in ['BUILD_COOP','BUILD_PASTURE']:builds[xy].append((t,idx))
  if op=='PICKUP' and action[1] in a.ANIMALS:
   item=action[1];n=after[2].get(item,0)-before[2].get(item,0);assert n>0 and len(stock[item])>=n
   ids=stock[item][:n];del stock[item][:n];bags[idx][item].extend(ids);annotations.append(('unit',t,idx,unite(ids)));uq[t,idx]=n;stats['successful_pickups']+=1
  elif op=='PLACE' and action[1] in a.ANIMALS:
   item=action[1];n=before[2].get(item,0)-after[2].get(item,0);assert n>0 and len(bags[idx][item])>=n;ids=bags[idx][item][:n];del bags[idx][item][:n];uq[t,idx]=n
   if isinstance(after[1],dict) and after[1].get('animal')==item and not (isinstance(before[1],dict) and before[1].get('animal')):
    assert n==1 and builds[xy],(t,idx,xy,after[1]);g=ids[0];annotations.append(('unit',t,idx,g));bt,bi=builds[xy][-1];annotations.append(('unit',bt,bi,g));stats['animals_placed']+=1
   else:stock[item].extend(ids)
  elif op=='DROP':
   for item in a.ANIMALS:
    n=after[3].get(item,0)-before[3].get(item,0);assert 0<=n<=len(bags[idx][item]);stock[item].extend(bags[idx][item][:n]);bags[idx][item].clear()
  return result
 def commit(op,item,price,farm,private,market,capacity=100):
  frame=sys._getframe(1);slot=frame.f_locals['i'];player=frame.f_locals['player_id'];ok=originals['_commit_unit'](op,item,price,farm,private,market,capacity)
  if ok and player==seat:
   t=now[0];mt[t,slot]=a.MARKET_INDEX[op+':'+item];mq[t,slot]+=1
   if op=='BUY_ANIMAL':
    key=t,slot
    if key not in buy_slots:
     g=len(groups);groups.append({'original':item,'count':0});parent.append(g);buy_slots[key]=g;annotations.append(('market',t,slot,g))
    g=buy_slots[key];groups[g]['count']+=1;stock[item].append(g)
  return ok
 def atomic(name,farm,private,*args,**kwargs):
  raise AssertionError('unused')
 def hire(farm,private,*args,**kwargs):
  frame=sys._getframe(1);player=frame.f_locals['player_id'];slot=frame.f_locals['i'];before=len(farm['hands']);r=originals['_do_hire'](farm,private,*args,**kwargs)
  if player==seat and len(farm['hands'])>before:mt[now[0],slot]=a.MARKET_INDEX['HIRE'];mq[now[0],slot]=1
  return r
 def land(farm,*args,**kwargs):
  frame=sys._getframe(1);player=frame.f_locals['player_id'];slot=frame.f_locals['i'];before=len(farm['unlocked_quadrants']);r=originals['_do_buy_land'](farm,*args,**kwargs)
  if player==seat and len(farm['unlocked_quadrants'])>before:mt[now[0],slot]=a.MARKET_INDEX['BUY_LAND'];mq[now[0],slot]=1
  return r
 def drop(private,capacity):
  frame=sys._getframe(1);player=frame.f_locals['player_id'];before=dict(private['shed']);r=originals['_drop_inventories_to_shed'](private,capacity)
  if player==seat:
   for item in a.ANIMALS:
    take=private['shed'].get(item,0)-before.get(item,0)
    ids=[g for bag in bags for g in bag[item]];assert 0<=take<=len(ids);stock[item].extend(ids[:take])
    for bag in bags:bag[item].clear()
  return r
 hooks={'_apply_unit_action':unit,'_commit_unit':commit,'_do_hire':hire,'_do_buy_land':land,'_drop_inventories_to_shed':drop}
 for name,fn in hooks.items():setattr(eng,name,fn)
 try:
  for t in range(719):
   now[0]=t;actions=[copy.deepcopy(s['action']) for s in rep['steps'][t+1]]
   count=min(10,len(actions[seat].get('market',[])));mt[t,:count]=a.MARKET_INDEX['BUY_SEED:WHEAT']
   env.step(actions)
   private=env.state[seat].observation.private
   for item in a.ANIMALS:
    assert len(stock[item])==private['shed'].get(item,0),(k,t,item,'shed',len(stock[item]),private['shed'].get(item,0))
    for i,inv in enumerate(private['inventories']):assert len(bags[i][item])==inv.get(item,0),(k,t,i,item,'bag')
 finally:
  for name,fn in originals.items():setattr(eng,name,fn)
 rewards=[float(s.reward) for s in env.state];assert rewards==rep['rewards'],(k,rewards,rep['rewards'])
 same=collections.defaultdict(list)
 for typ,t,i,g in annotations:same[typ,t,i].append(g)
 for ids in same.values():unite(ids)
 roots=sorted({root(g) for g in range(len(groups))});mapping={g:i for i,g in enumerate(roots)};outgroups=[]
 for g in roots:
  members=[j for j in range(len(groups)) if root(j)==g];original={groups[j]['original'] for j in members};assert len(original)==1,('mixed-species dependency',k,original)
  outgroups.append({'original':next(iter(original)),'count':sum(groups[j]['count'] for j in members),'first_step':min(t for typ,t,i,gg in annotations if root(gg)==g)})
 program={'groups':outgroups,'events':{typ:{f'{t}:{i}':mapping[root(g)] for typ2,t,i,g in annotations if typ2==typ} for typ in ['unit','market']},'animals_placed':stats['animals_placed'],'reference_prototype':k,'source_sha256':row['sha256'],'stats':dict(stats),'exact_replay_rewards':True}
 out=B/'executed_new_teacher';out.mkdir(exist_ok=True)
 (out/f'{k:03}_program.json').write_text(json.dumps(program,indent=2)+'\n');np.savez_compressed(out/f'{k:03}_effective.npz',unit_tokens=ut,unit_quantities=uq,market_tokens=mt,market_quantities=mq)
 # Canonical requests must independently reproduce both agents' rewards.
 env2=make('kaggriculture',configuration=cfg);env2.reset(2)
 for t in range(719):
  n=1+len(env2.state[seat].observation.farms[seat]['hands']);units=[]
  for i in range(n):
   parts=a.UNIT_TOKENS[int(ut[t,i])].split(':')
   if parts[0] in ['PICKUP','PLACE']:parts.append(int(uq[t,i]))
   units.append(parts)
  market=[]
  for tok,q in zip(mt[t],mq[t]):
   if not tok:break
   parts=a.MARKET_TOKENS[int(tok)].split(':')
   if len(parts)==2:parts.append(int(q))
   market.append(parts)
  acts=[copy.deepcopy(s['action']) for s in rep['steps'][t+1]];acts[seat]={'farmer':units[0],'hands':units[1:],'market':market};env2.step(acts)
  expected=dict(rep['steps'][t+1][0]['observation']);expected.update(rep['steps'][t+1][seat]['observation'])
  for field in ['farms','market','private','town']:assert env2.state[seat].observation[field]==expected[field],('canonical state mismatch',k,t,field)
 result={'prototype':k,'groups':len(outgroups),'animals_placed':stats['animals_placed'],'stats':dict(stats),'exact_canonical_states':True,'rewards':rewards}
 (out/f'{k:03}_audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 indices=list(range(121)) if '--all' in sys.argv else list(map(int,sys.argv[1:])) or [0,35,74,83]
 out=B/'executed_new_teacher';out.mkdir(exist_ok=True);rows=[];errors=[]
 pending=[]
 for k in indices:
  p=out/f'{k:03}_audit.json'
  if p.exists() and json.loads(p.read_text()).get('exact_canonical_states'):rows.append(json.loads(p.read_text()))
  else:pending.append(k)
 print('pending',len(pending),flush=True)
 for start in range(0,len(pending),24):
  with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
   futures={pool.submit(run,k):k for k in pending[start:start+24]}
   for f in concurrent.futures.as_completed(futures):
    try:row=f.result();rows.append(row);print('compiled',row['prototype'],row['groups'],row['animals_placed'],flush=True)
    except Exception as exc:errors.append({'prototype':futures[f],'error':repr(exc)});print(errors[-1],flush=True)
 manifest={'expected':len(indices),'compiled':sorted(r['prototype'] for r in rows),'errors':errors,'exact_canonical_states':all(r['exact_canonical_states'] for r in rows),'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'compile_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest),flush=True)
