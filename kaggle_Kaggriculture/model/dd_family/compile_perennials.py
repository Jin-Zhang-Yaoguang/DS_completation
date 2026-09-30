"""Compile route-preserving perennial programs using official biological transitions."""
from pathlib import Path
import collections,contextlib,copy,hashlib,importlib,io,json
B=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')

def key(tile):return json.dumps(tile,sort_keys=True,separators=(',',':'))

def transition(state,action,t,nt):
    farm={'tiles':[[json.loads(state)]],'farmer':[0,0],'hands':[]}
    private={'inventories':[{'FERTILIZER':1}],'seeds':{'TOMATO':1,'STRAWBERRY':1},'shed':{}}
    engine._apply_unit_action(farm,private,0,action.split(':'),1,t//24,24,100)
    amount=sum(private['inventories'][0].get(c,0) for c in ['TOMATO','STRAWBERRY'])
    for tt in range(t,nt):
        engine._decay_plants(farm,tt)
        if tt%24==23:engine._daily_refresh_plants(farm,tt//24,24)
    return key(farm['tiles'][0][0]),amount

def run_fixed(job,crop=None,actions=None):
    state=key(None);total=0;value=0.;harvests=[]
    for i,event in enumerate(job['events']):
        t,u,op=event['step'],event['unit'],event['op']
        if actions is not None:op=actions[i]
        if i==0 and crop:op='PLANT:'+crop
        nt=job['events'][i+1]['step'] if i+1<len(job['events']) else job['end_step']
        state,n=transition(state,op,t,nt)
        if n:harvests.append([t,u,n])
        total+=n;value+=n*.985**((t-job['purchase_step'])/24) if event['deliverable'] else 0
    return {'yield_units':total,'discounted_units':value,'terminal':json.loads(state),'harvests':harvests}

def optimize(job,crop):
    # Biology is a complete finite state; retain the best reward for each state.
    dp={key(None):(0.,0,[])};peak=0
    for i,event in enumerate(job['events']):
        t,op=event['step'],event['op'];nt=job['events'][i+1]['step'] if i+1<len(job['events']) else job['end_step'];new={}
        for state,(value,total,actions) in dp.items():
            tile=json.loads(state)
            if i==0:choices=['PLANT:'+crop]
            elif op=='DIG':choices=['DIG']
            elif not isinstance(tile,dict):choices=['PASS']
            elif tile.get('kind')=='WEED':choices=['DIG','PASS']
            else:
                choices=['PASS','WATER']
                if tile.get('yield_units',0)>0 and t//24-tile['planted_day']>=engine.CROPS[crop]['first_yield_day']:choices.append('HARVEST')
                if op=='FERTILIZE' and event['fert_available']:choices.append('FERTILIZE')
            for action in choices:
                after,n=transition(state,action,t,nt)
                score=value+(n*.985**((t-job['purchase_step'])/24) if event['deliverable'] else 0)
                candidate=score,total+n,actions+[action]
                if after not in new or candidate[:2]>new[after][:2]:new[after]=candidate
        dp=new;peak=max(peak,len(dp))
    feasible=[v for state,v in dp.items() if job['end_step']==719 or json.loads(state) is None]
    if not feasible:return None
    value,total,actions=max(feasible,key=lambda v:v[:2])
    if value<=0:return None
    replay=run_fixed(job,crop,actions)
    assert total==replay['yield_units'] and abs(value-replay['discounted_units'])<1e-8
    return {'crop':crop,'yield_units':total,'discounted_units':value,'actions':actions,'harvests':replay['harvests'],'peak_states':peak}

def main():
    row=json.loads((B/'ddm/training_manifest.json').read_text())['episodes'][35]
    raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat']
    queues={c:[] for c in ['TOMATO','STRAWBERRY']};jobs=[];visits=collections.defaultdict(list);actions={}
    for t in range(719):
        obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);farm=copy.deepcopy(obs['farms'][seat]);private=copy.deepcopy(obs['private']);act=rep['steps'][t+1][seat]['action']
        ua=[act['farmer'],*act.get('hands',[])];need=collections.Counter(a[1] for a in ua if a[0]=='PLANT');blocked={c for c,n in need.items() if n>private['seeds'].get(c,0)}
        for i,a in enumerate(ua):
            xy=tuple(engine._farmer_position(farm,i));x,y=xy;before=copy.deepcopy(farm['tiles'][y][x]);bag=copy.deepcopy(private['inventories'][i]);op=':'.join(a[:2]) if a[0]=='PLANT' else a[0]
            actions[t,i]=(list(a),xy)
            engine._apply_unit_action(farm,private,i,['PASS'] if a[0]=='PLANT' and a[1] in blocked else a,10,t//24,24,100)
            after=farm['tiles'][y][x]
            if op.startswith('PLANT:') or op.startswith('BUILD_') or op in ['WATER','FERTILIZE','HARVEST','DIG']:
                gain=sum(private['inventories'][i].get(c,0)-bag.get(c,0) for c in queues)
                visits[xy].append({'step':t,'unit':i,'op':op,'fert_available':bag.get('FERTILIZER',0)>0,'source_yield':gain})
            if a[0]=='PLANT' and a[1] in queues and before is None and isinstance(after,dict) and after.get('crop')==a[1]:
                assert queues[a[1]],(t,i,a);purchase,slot=queues[a[1]].pop(0)
                jobs.append({'crop':a[1],'purchase_step':purchase,'purchase_slot':slot,'plant_step':t,'plant_unit':i,'xy':list(xy)})
        nxt=dict(rep['steps'][t+1][0]['observation']);nxt.update(rep['steps'][t+1][seat]['observation'])
        for c in queues:
            n=nxt['private']['seeds'].get(c,0)-private['seeds'].get(c,0);assert n>=0
            slots=[s for s,a in enumerate(act.get('market',[])) if a[:2]==['BUY_SEED',c]]
            if n:assert len(slots)==1;queues[c].extend([(t,slots[0])]*n)
    units={};purchases=collections.defaultdict(list)
    for j,job in enumerate(jobs):
        es=[];end=719
        for e in visits[tuple(job['xy'])]:
            if (e['step'],e['unit'])<(job['plant_step'],job['plant_unit']):continue
            if es and (e['op'].startswith('PLANT:') or e['op'].startswith('BUILD_')):end=e['step'];break
            e=copy.deepcopy(e);e['deliverable']=e['step']//24<29 or any(actions.get((tt,e['unit']),(None,None))[0]==['DROP'] and actions[tt,e['unit']][1] in {(4,4),(4,5),(5,4),(5,5)} for tt in range(e['step']+1,719))
            es.append(e)
        job.update(events=es,end_step=end);original=run_fixed(job)
        assert original['yield_units']==sum(e['source_yield'] for e in es),(j,original,sum(e['source_yield'] for e in es))
        job['original']=original;job['alternatives']=[p for c in queues if (p:=optimize(job,c))]
        for ix,e in enumerate(es):
            k=f"{e['step']}:{e['unit']}";assert k not in units;units[k]=[j,ix]
        purchases[f"{job['purchase_step']}:{job['purchase_slot']}"].append(j)
        print(j,job['crop'],len(es),original['yield_units'],[(p['crop'],p['yield_units'],p['peak_states']) for p in job['alternatives']],flush=True)
    out={'source_sha256':row['sha256'],'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'jobs':jobs,'units':units,'purchases':purchases,'scope':'Official biology and original-yield parity only; whole-agent seed, sales and dynamic competition require separate validation.'}
    (B/'dday/perennial_programs.json').write_text(json.dumps(out,indent=2)+'\n')
    print('compiled',len(jobs),'programs',sum(len(j['alternatives']) for j in jobs),flush=True)

if __name__=='__main__':main()
