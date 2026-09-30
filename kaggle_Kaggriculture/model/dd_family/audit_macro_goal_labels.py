"""Check whether replay-derived next successful service goals are observable/feasible."""
from pathlib import Path
import collections,contextlib,copy,hashlib,io,json,sys
B=Path(__file__).resolve().parent
sys.path.insert(0,str(B/'ddam'));import rules,action_space as space

def run(source,k):
    row=json.loads((B/source/'training_manifest.json').read_text())['episodes'][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat'];events=collections.defaultdict(list);starts={}
    for t in range(719):
        obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);farm=copy.deepcopy(obs['farms'][seat]);priv=copy.deepcopy(obs['private']);act=rep['steps'][t+1][seat]['action'];actions=[act['farmer'],*act.get('hands',[])];demands=collections.Counter(a[1] for a in actions if a[0]=='PLANT');blocked={c for c,n in demands.items() if n>priv['seeds'].get(c,0)}
        for i,a in enumerate(actions[:len(priv['inventories'])]):
            starts.setdefault((t//24,i),t);xy=rules._farmer_position(farm,i);x,y=xy
            before=(copy.deepcopy(farm['tiles'][y][x]),dict(priv['inventories'][i]),dict(priv['seeds']),dict(priv['shed']))
            rules._apply_unit_action(farm,priv,i,['PASS'] if a[0]=='PLANT' and a[1] in blocked else a,10,t//24,24,100)
            after=(farm['tiles'][y][x],priv['inventories'][i],priv['seeds'],priv['shed'])
            if a[0] not in ['PASS',*space.MOVES] and before!=after:events[t//24,i].append({'step':t,'unit':i,'xy':list(xy),'action':a})
    queries={}
    for key,es in events.items():
        start=starts[key]
        for e in es:
            assert start<=e['step'];queries[start,e['unit']]=e;start=e['step']+1
    counts=collections.Counter();blocked_examples=[];latencies=[]
    for t in range(719):
        obs=copy.deepcopy(rep['steps'][t][0]['observation']);obs.update(copy.deepcopy(rep['steps'][t][seat]['observation']));obs['step']=t;obs['player']=seat;farm=obs['farms'][seat];priv=obs['private'];act=rep['steps'][t+1][seat]['action'];actions=[act['farmer'],*act.get('hands',[])];demands=collections.Counter(a[1] for a in actions if a[0]=='PLANT');blocked={c for c,n in demands.items() if n>priv['seeds'].get(c,0)}
        for i,a in enumerate(actions[:len(priv['inventories'])]):
            e=queries.get((t,i))
            if e:
                pos=rules._farmer_position(farm,i);rules._set_farmer_position(farm,i,tuple(e['xy']));tok,q,known=space.unit_token(e['action']);assert known
                legal=bool(space.unit_legal_mask(obs,i)[tok]);rules._set_farmer_position(farm,i,pos)
                counts['goals']+=1;counts['feasible_from_current_visible_state']+=legal;counts[e['action'][0]]+=1;latencies.append(e['step']-t)
                if not legal and len(blocked_examples)<25:blocked_examples.append({'start':t,'unit':i,'target':e,'inventory':dict(priv['inventories'][i]),'seeds':dict(priv['seeds']),'target_current_tile':copy.deepcopy(farm['tiles'][e['xy'][1]][e['xy'][0]])})
            rules._apply_unit_action(farm,priv,i,['PASS'] if a[0]=='PLANT' and a[1] in blocked else a,10,t//24,24,100)
    return {'source':source,'prototype':k,'source_sha256':row['sha256'],'counts':dict(counts),'mean_travel_or_wait_turns':sum(latencies)/len(latencies),'max_travel_or_wait_turns':max(latencies),'blocked_examples':blocked_examples,'scope':'Feasibility diagnostic only. Goal location/action are supervision targets, not model inputs. No model fitted or competitive claim.'}

if __name__=='__main__':
    rows=[run(s,k) for s,k in [('ddm',35),('ddm',0),('dde',0),('ddbc',0)]]
    (B/'audit_macro_goal_labels.json').write_text(json.dumps(rows,indent=2)+'\n')
    for r in rows:print(r['source'],r['prototype'],r['counts'],r['mean_travel_or_wait_turns'],flush=True)
