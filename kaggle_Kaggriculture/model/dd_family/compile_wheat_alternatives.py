"""Audit replay wheat cycles for route-preserving carrot substitution.

This only compiles validated modules; it does not alter or evaluate an agent.
Source wheat yield is reproduced with official lifecycle rules before a carrot
alternative is considered. Direct same-day animal feed/PLACE dependencies block
substitution rather than assuming all wheat is freely saleable.
"""
from pathlib import Path
import collections,contextlib,copy,hashlib,importlib,io,json
B=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')

def simulate(job,crop):
    x,y=job['xy'];farm={'tiles':[[None for _ in range(10)] for _ in range(10)],'farmer':[x,y],'hands':[]}
    private={'inventories':[{'FERTILIZER':100}],'seeds':{crop:1},'shed':{}}
    grouped=collections.defaultdict(list)
    grouped[job['plant_step']].append(['PLANT',crop])
    for t,i,op in job['events']:grouped[t].append([op])
    for t in range(job['plant_step'],job['harvest_step']+1):
        for action in grouped[t]:engine._apply_unit_action(farm,private,0,action,10,t//24,24,100)
        engine._decay_plants(farm,t)
        if (t+1)%24==0:engine._daily_refresh_plants(farm,t//24,24)
    return private['inventories'][0].get(crop,0)

def main():
    row=json.loads((B/'ddm/training_manifest.json').read_text())['episodes'][35];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat']
    jobs=[];active={};seed_queue=[];unit_actions={};purchase_slots={};initial=rep['steps'][0][seat]['observation'].get('private',rep['steps'][0][0]['observation'].get('private'))['seeds'].get('WHEAT',0)
    seed_queue=[(-1,-1)]*initial
    for t in range(719):
        obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);farm=copy.deepcopy(obs['farms'][seat]);private=copy.deepcopy(obs['private']);action=rep['steps'][t+1][seat]['action'];actions=[action['farmer'],*action.get('hands',[])]
        demand=collections.Counter(a[1] for a in actions if a[0]=='PLANT');blocked={crop for crop,n in demand.items() if n>private['seeds'].get(crop,0)}
        for i,act in enumerate(actions):
            xy=tuple(engine._farmer_position(farm,i));x,y=xy;before=copy.deepcopy(farm['tiles'][y][x]);grain=private['inventories'][i].get('WHEAT',0);allowed=['PASS'] if act[0]=='PLANT' and act[1] in blocked else act
            unit_actions[t,i]={'action':act,'xy':list(xy)}
            engine._apply_unit_action(farm,private,i,allowed,10,t//24,24,100);after=farm['tiles'][y][x]
            if act==['PLANT','WHEAT'] and before is None and isinstance(after,dict) and after.get('crop')=='WHEAT':
                assert seed_queue,(t,i);purchase,slot=seed_queue.pop(0);j=len(jobs);jobs.append({'purchase_step':purchase,'purchase_slot':slot,'plant_step':t,'plant_unit':i,'xy':list(xy),'events':[]});active[xy]=j
            elif xy in active:
                j=active[xy]
                if act[0] in ['WATER','FERTILIZE'] and before!=after:jobs[j]['events'].append([t,i,act[0]])
                elif act[0]=='HARVEST' and isinstance(before,dict) and before.get('crop')=='WHEAT' and after is None:
                    jobs[j]['events'].append([t,i,'HARVEST']);jobs[j].update(harvest_step=t,harvest_unit=i,source_yield=private['inventories'][i].get('WHEAT',0)-grain);del active[xy]
        nxt=dict(rep['steps'][t+1][0]['observation']);nxt.update(rep['steps'][t+1][seat]['observation']);purchased=nxt['private']['seeds'].get('WHEAT',0)-private['seeds'].get('WHEAT',0);assert purchased>=0
        slots=[i for i,a in enumerate(action.get('market',[])) if a[0]=='BUY_SEED' and a[1]=='WHEAT'];purchase_slots[t]=slots
        if purchased:assert slots
        seed_queue.extend([(t,slots[0] if len(slots)==1 else -2)]*purchased)
        for xy,j in list(active.items()):
            x,y=xy;tile=nxt['farms'][seat]['tiles'][y][x]
            if not isinstance(tile,dict) or tile.get('crop')!='WHEAT':jobs[j]['terminated_step']=t;del active[xy]
    counts=collections.Counter()
    for job in jobs:
        if 'harvest_step' not in job:job['eligible']=False;job['reason']='no_complete_harvest';counts[job['reason']]+=1;continue
        source=simulate(job,'WHEAT');assert source==job['source_yield'],(job,source)
        carrot=simulate(job,'CARROT');job['yields']={'WHEAT':source,'CARROT':carrot};t=job['harvest_step'];i=job['harvest_unit'];dependent=[]
        for tt in range(t+1,min(719,(t//24+1)*24)):
            record=unit_actions.get((tt,i))
            if record is None:continue
            act=record['action']
            if act[0]=='DROP' and tuple(record['xy']) in {(4,4),(4,5),(5,4),(5,5)}:break
            if act[0]=='FEED' or act[:2]==['PLACE','WHEAT']:dependent.append({'step':tt,'action':act})
        job['direct_grain_dependencies']=dependent
        job['eligible']=carrot>0 and not dependent and job['purchase_step']>=0 and job['purchase_slot']>=0
        job['reason']='eligible' if job['eligible'] else ('carrot_expired_or_no_yield' if not carrot else 'direct_feed_or_transfer' if dependent else 'ambiguous_seed_purchase')
        counts[job['reason']]+=1
    eligible=[j for j in jobs if j.get('eligible') and j['purchase_step']//24>=12]
    result={'source_sha256':row['sha256'],'source_prototype':35,'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_yield_parity':True,'counts':dict(counts),'late_eligible_cycles':len(eligible),'late_source_wheat_units':sum(j['yields']['WHEAT'] for j in eligible),'late_alternative_carrot_units':sum(j['yields']['CARROT'] for j in eligible),'jobs':jobs,'boundary':'Compiled opportunity only. No crop policy trained/evaluated. Replacing a grain crop still requires restoring warehouse feed stocks, seed funding and market-slot/capacity consistency.'}
    (B/'wheat_alternative_modules.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='jobs'}),flush=True)
if __name__=='__main__':main()
