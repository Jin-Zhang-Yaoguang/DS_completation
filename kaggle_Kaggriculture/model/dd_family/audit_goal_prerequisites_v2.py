"""Classify source task starts that were labelled WAIT only for unmet prerequisites."""
from pathlib import Path
import collections,concurrent.futures,copy,hashlib,json,sys
B=Path(__file__).resolve().parent

def run(k):
    sys.path.insert(0,str(B/'ddbi'));import action_space as A,rules
    row=json.loads((B/'ddbd/training_manifest.json').read_text())['episodes'][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat'];events=collections.defaultdict(list);starts={}
    for t in range(719):
        obs=copy.deepcopy(rep['steps'][t][0]['observation']);obs.update(copy.deepcopy(rep['steps'][t][seat]['observation']));farm=obs['farms'][seat];priv=obs['private'];act=rep['steps'][t+1][seat]['action'];actions=[act['farmer'],*act['hands']];demands=collections.Counter(a[1] for a in actions if a[0]=='PLANT');blocked={c for c,n in demands.items() if n>priv['seeds'].get(c,0)}
        for i,a in enumerate(actions[:len(priv['inventories'])]):
            starts.setdefault((t//24,i),t);x,y=rules._farmer_position(farm,i);before=copy.deepcopy((farm['tiles'][y][x],priv['inventories'][i],priv['seeds'],priv['shed']))
            rules._apply_unit_action(farm,priv,i,['PASS'] if a[0]=='PLANT' and a[1] in blocked else a,10,t//24,24,100)
            if a[0] not in ['PASS',*A.MOVES] and before!=(farm['tiles'][y][x],priv['inventories'][i],priv['seeds'],priv['shed']):events[t//24,i].append({'step':t,'xy':(x,y),'action':a})
    queries={}
    for key,es in events.items():
        start=starts[key]
        for e in es:queries[start,key[1]]=e;start=e['step']+1
    waiting={};counts=collections.Counter();examples=[]
    for t in range(719):
        if t%24==0:waiting={}
        obs=copy.deepcopy(rep['steps'][t][0]['observation']);obs.update(copy.deepcopy(rep['steps'][t][seat]['observation']));obs['step']=t;obs['player']=seat;farm=obs['farms'][seat];priv=obs['private'];act=rep['steps'][t+1][seat]['action'];actions=[act['farmer'],*act['hands']];demands=collections.Counter(a[1] for a in actions if a[0]=='PLANT');blocked={c for c,n in demands.items() if n>priv['seeds'].get(c,0)}
        for i,a in enumerate(actions[:len(priv['inventories'])]):
            if (t,i) in queries:waiting[i]=queries[t,i]
            if i in waiting:
                e=waiting[i];old=tuple(rules._farmer_position(farm,i));tok,qty,known=A.unit_token(e['action']);assert known;rules._set_farmer_position(farm,i,e['xy']);legal=A.unit_legal_mask(obs,i)[tok];rules._set_farmer_position(farm,i,old)
                if legal:waiting.pop(i)
                else:
                    op=e['action'][0];reason='structural_or_other'
                    if op=='PICKUP' and priv['shed'].get(e['action'][1],0)==0:reason='missing_shed:'+e['action'][1]
                    elif op=='PLANT' and priv['seeds'].get(e['action'][1],0)==0:reason='missing_seed:'+e['action'][1]
                    elif op=='FEED' and priv['inventories'][i].get('WHEAT',0)==0:reason='missing_carried_wheat'
                    if reason=='structural_or_other':
                        tile=farm['tiles'][e['xy'][1]][e['xy'][0]];kind=tile.get('kind','UNKNOWN') if isinstance(tile,dict) else str(tile);reason='board_or_other:'+op+':'+kind
                    counts[reason]+=1
                    if len(examples)<12:examples.append({'query_step':t,'unit':i,'successful_step':e['step'],'action':e['action'],'reason':reason,'cash':farm['money']})
            rules._apply_unit_action(farm,priv,i,['PASS'] if a[0]=='PLANT' and a[1] in blocked else a,10,t//24,24,100)
    return {'prototype':k,'source_sha256':row['sha256'],'counts':dict(counts),'examples':examples}

if __name__=='__main__':
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,range(21)))
    counts=collections.Counter()
    for r in rows:counts.update(r['counts'])
    out={'source':'Boey train only; no new policy trained','counts':dict(counts),'rows':rows};(B/'diagnostics/task_prerequisites_detailed.json').write_text(json.dumps(out,indent=2)+'\n');print(dict(counts),flush=True)
