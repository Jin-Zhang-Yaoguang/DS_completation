from pathlib import Path
import json,hashlib,collections,statistics,concurrent.futures
B=Path(__file__).resolve().parent
OUT=B/'trajectory_rows';OUT.mkdir(exist_ok=True)
def h(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),sort_keys=True).encode()).hexdigest()[:24]
def one(r):
 p=OUT/(str(r['episode_id'])+'.json')
 if p.exists():return r['episode_id']
 d=json.loads(Path(r['path']).read_text());s=r['seat'];steps=d['steps'];obs=[z[s]['observation'] for z in steps];times=[o.get('remainingOverageTime') for o in obs];drops=[{'decision_step':i,'excess_seconds':times[i]-times[i+1]} for i in range(len(times)-1) if times[i] is not None and times[i+1] is not None and times[i]-times[i+1]>1e-8];days=[]
 for day in range(30):
  indexes=range(day*24,min((day+1)*24,len(steps)-1));pos=[];act=[];fa=[];fp=[];tokens=[]
  for i in indexes:
   a=steps[i+1][s]['action'] or {};farm=obs[i]['farms'][s];f=farm['farmer'];hands=farm['hands'];pos.append(h([f,hands]));fp.append(h(f));act.append(h([a.get('farmer'),a.get('hands')]));fa.append(h(a.get('farmer')));tokens.append([h(x) for x in [a.get('farmer')]+a.get('hands',[])])
  days.append({'day':day,'shops':obs[day*24]['town']['unlocked_shops'],'positions':pos,'farmer_positions':fp,'actions':act,'farmer_actions':fa,'unit_actions':tokens,'day_position_hash':h(pos),'day_action_hash':h(act)})
 events=[]
 for i in range(1,len(obs)):
  old=obs[i-1]['town']['unlocked_shops'];new=obs[i]['town']['unlocked_shops']
  if len(new)>len(old):events.append({'state_step':i,'new_shop':new[-1],'history':new})
 result={'episode_id':r['episode_id'],'submission_id':r['submission_id'],'opponent':r['opponent'],'initial_overage':times[0],'first_excess_seconds':times[0]-times[1],'first_accounted_seconds':d['configuration']['actTimeout']+times[0]-times[1] if times[0]>times[1] else None,'total_excess_seconds':times[0]-times[-1],'later_excess_seconds':times[1]-times[-1],'drops':drops,'days':days,'events':events}
 p.write_text(json.dumps(result,separators=(',',':')));return r['episode_id']
def pair_same(values):
 n=len(values)
 return sum(c*(c-1) for c in collections.Counter(values).values())/(n*(n-1)) if n>1 else None
def stats(x):
 return {'n':len(x),'median':statistics.median(x),'mean':statistics.mean(x),'min':min(x),'max':max(x),'q25':statistics.quantiles(x,n=4,method='inclusive')[0],'q75':statistics.quantiles(x,n=4,method='inclusive')[2]} if x else None
if __name__=='__main__':
 meta=json.loads((B/'episode_table.json').read_text())
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
  for i,_ in enumerate(ex.map(one,meta,chunksize=1),1):
   if i%100==0:print('parsed',i,flush=True)
 rows=[json.loads(p.read_text()) for p in OUT.glob('*.json')];out={}
 for sid in ['56156662','56216119','historical']:
  rr=[r for r in rows if r['submission_id']==sid];g={'n':len(rr),'first_accounted_seconds':stats([r['first_accounted_seconds'] for r in rr if r['first_accounted_seconds'] is not None]),'first_no_excess_n':sum(r['first_accounted_seconds'] is None for r in rr),'later_excess_seconds':stats([r['later_excess_seconds'] for r in rr]),'later_excess_n':sum(r['later_excess_seconds']>1e-8 for r in rr),'later_drop_steps':collections.Counter(str(x['decision_step']) for r in rr for x in r['drops'] if x['decision_step']>0),'daily':[]}
  for day in range(30):
   ds=[r['days'][day] for r in rr];z={'day':day,'n':len(ds)}
   for k in ['day_position_hash','day_action_hash']:z[k+'_unique']=len(set(d[k] for d in ds));z[k+'_pair_equal']=pair_same([d[k] for d in ds])
   for k in ['positions','farmer_positions','actions','farmer_actions']:
    z[k+'_pair_equal']=statistics.mean(pair_same([d[k][t] for d in ds]) for t in range(len(ds[0][k])))
   unit_matches=unit_pairs=0
   for t in range(len(ds[0]['unit_actions'])):
    for u in range(max(len(d['unit_actions'][t]) for d in ds)):
     vals=[d['unit_actions'][t][u] for d in ds if len(d['unit_actions'][t])>u];n=len(vals)
     if n>1:unit_matches+=sum(c*(c-1) for c in collections.Counter(vals).values());unit_pairs+=n*(n-1)
   z['unit_action_pair_equal_given_present']=unit_matches/unit_pairs
   grouped=collections.defaultdict(list)
   for d in ds:grouped[tuple(d['shops'])].append(d)
   groups=[v for v in grouped.values() if len(v)>1];den=sum(len(v)*(len(v)-1) for v in groups)
   z['shop_history_pair_count']=den//2
   z['actions_pair_equal_same_shop_history']=sum(len(v)*(len(v)-1)*statistics.mean(pair_same([d['actions'][t] for d in v]) for t in range(len(v[0]['actions']))) for v in groups)/den if den else None
   worker_matches=worker_pairs=0
   for t in range(len(ds[0]['unit_actions'])):
    for u in range(1,max(len(d['unit_actions'][t]) for d in ds)):
     vals=[d['unit_actions'][t][u] for d in ds if len(d['unit_actions'][t])>u];n=len(vals)
     if n>1:worker_matches+=sum(c*(c-1) for c in collections.Counter(vals).values());worker_pairs+=n*(n-1)
   z['worker_action_pair_equal_given_present']=worker_matches/worker_pairs if worker_pairs else None
   if day>0:
    for key in ['positions','actions','farmer_positions','farmer_actions']:
     z['within_previous_day_'+key]=statistics.mean(sum(a==b for a,b in zip(r['days'][day-1][key],r['days'][day][key]))/min(len(r['days'][day-1][key]),len(r['days'][day][key])) for r in rr)
   g['daily'].append(z)
  out[sid]=g
 (B/'trajectory_analysis.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:{a:v for a,v in g.items() if a!='daily'} for k,g in out.items()},indent=2))
