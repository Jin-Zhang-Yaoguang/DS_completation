"""Compile official successful service/market labels, with causal own-order shadows."""
from pathlib import Path
import argparse,collections,concurrent.futures,contextlib,copy,hashlib,importlib,io,json,sys,time
import numpy as np
B=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def compile_one(task):
    version,row,index=task;start=time.perf_counter();D=B/version;sys.path.insert(0,str(D))
    import action_space as A,rules,task_features as F
    raw=Path(row['path']).read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if row.get('sha256'):assert digest==row['sha256']
    rep=json.loads(raw);seat=int(row['seat']);assert rep['module_version']=='1.32.7'
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    cfg=dict(rep['configuration']);cfg['seed']=rep['info']['seed'];env=make('kaggriculture',configuration=cfg);env.reset(2)
    now=[0];events=collections.defaultdict(list);mt=np.zeros((719,10),np.int16);mq=np.zeros((719,10),np.int16);counts=collections.Counter()
    original={name:getattr(eng,name) for name in ['_apply_unit_action','_commit_unit','_do_hire','_do_buy_land']}
    def unit(farm,private,i,action,*args,**kwargs):
        player=sys._getframe(1).f_locals['i']
        if player!=seat or action[0] in ['PASS',*A.MOVES]:return original['_apply_unit_action'](farm,private,i,action,*args,**kwargs)
        xy=tuple(eng._farmer_position(farm,i));x,y=xy
        before=(copy.deepcopy(farm['tiles'][y][x]),dict(private['inventories'][i]),dict(private['seeds']),dict(private['shed']))
        result=original['_apply_unit_action'](farm,private,i,action,*args,**kwargs)
        after=(farm['tiles'][y][x],private['inventories'][i],private['seeds'],private['shed'])
        if before!=after:
            tok,q,known=A.unit_token(action);assert known
            if action[0]=='PICKUP':q=after[1].get(action[1],0)-before[1].get(action[1],0)
            elif action[0]=='PLACE':q=before[1].get(action[1],0)-after[1].get(action[1],0)
            events[now[0]//24,i].append({'step':now[0],'goal':[*xy,tok],'q':q});counts['successful_services']+=1
        else:counts['ineffective_services']+=1
        return result
    def commit(op,item,price,farm,private,market,capacity=100):
        frame=sys._getframe(1);slot=frame.f_locals['i'];player=frame.f_locals['player_id']
        result=original['_commit_unit'](op,item,price,farm,private,market,capacity)
        if result and player==seat:mt[now[0],slot]=A.MARKET_INDEX[op+':'+item];mq[now[0],slot]+=1
        return result
    def hire(farm,private,*args,**kwargs):
        frame=sys._getframe(1);player=frame.f_locals['player_id'];slot=frame.f_locals['i'];n=len(farm['hands']);r=original['_do_hire'](farm,private,*args,**kwargs)
        if player==seat and len(farm['hands'])>n:mt[now[0],slot]=A.MARKET_INDEX['HIRE'];mq[now[0],slot]=1
        return r
    def land(farm,*args,**kwargs):
        frame=sys._getframe(1);player=frame.f_locals['player_id'];slot=frame.f_locals['i'];n=len(farm['unlocked_quadrants']);r=original['_do_buy_land'](farm,*args,**kwargs)
        if player==seat and len(farm['unlocked_quadrants'])>n:mt[now[0],slot]=A.MARKET_INDEX['BUY_LAND'];mq[now[0],slot]=1
        return r
    for name,fn in {'_apply_unit_action':unit,'_commit_unit':commit,'_do_hire':hire,'_do_buy_land':land}.items():setattr(eng,name,fn)
    try:
        for t in range(719):
            now[0]=t;env.step([copy.deepcopy(s['action']) for s in rep['steps'][t+1]])
            expected=dict(rep['steps'][t+1][0]['observation']);expected.update(rep['steps'][t+1][seat]['observation'])
            for field in ['farms','private','market','town']:assert env.state[seat].observation[field]==expected[field],(index,t,field)
    finally:
        for name,fn in original.items():setattr(eng,name,fn)
    assert [float(s.reward) for s in env.state]==rep['rewards']
    rng=np.random.default_rng(61071+index);rx=[];ry=[];gx=[];gq=[];mx=[];my=[];mqy=[];vx=[];vy=[];vo=[0]
    committed={};ends={};previous={};pointers=collections.Counter();query_number=0
    for t in range(719):
        if t%24==0:committed={};ends={};previous={}
        obs=copy.deepcopy(rep['steps'][t][0]['observation']);obs.update(copy.deepcopy(rep['steps'][t][seat]['observation']));obs['player']=seat;obs['step']=t
        act=rep['steps'][t+1][seat]['action'];actions=[act['farmer'],*act.get('hands',[])];demands=collections.Counter(a[1] for a in actions if a[0]=='PLANT');blocked={c for c,n in demands.items() if n>obs['private']['seeds'].get(c,0)}
        for i,a in enumerate(actions[:len(obs['private']['inventories'])]):
            key=t//24,i;es=events[key];pointer=pointers[key]
            while pointer<len(es) and es[pointer]['step']<t:pointer+=1
            pointers[key]=pointer
            if i not in committed:
                goals=F.candidates(obs,i);chosen=0;q=0;e=es[pointer] if pointer<len(es) else None
                if e:
                    match=np.flatnonzero(np.all(goals==e['goal'],axis=1))
                    if len(match):chosen=int(match[0]);q=e['q'];counts['feasible_task_queries']+=1
                    else:counts['wait_for_infeasible_next_task']+=1
                else:counts['no_remaining_service_queries']+=1
                x=F.goal_features(obs,i,goals,committed,previous);query_number+=1
                # Hard negatives distinguish action at this tile and another tile for this action.
                others=np.flatnonzero(np.arange(len(goals))!=chosen);selected=[0] if chosen else []
                for mask in [goals[:,2]==goals[chosen,2],np.all(goals[:,:2]==goals[chosen,:2],axis=1)]:
                    pool=np.asarray([j for j in others[mask[others]] if j not in selected],int)
                    if len(pool):selected.extend(rng.choice(pool,min(3,8-len(selected),len(pool)),replace=False).tolist())
                pool=np.asarray([j for j in others if j not in selected],int)
                if len(pool):selected.extend(rng.choice(pool,min(8-len(selected),len(pool)),replace=False).tolist())
                ids=[chosen,*selected];rx.append(x[ids]);ry.extend([1]+[0]*len(selected))
                if q>0:gx.append(x[chosen]);gq.append(q)
                if row['split']=='validation' and query_number%32==0:
                    vx.append(x);vy.append(chosen);vo.append(vo[-1]+len(x))
                if chosen:
                    committed[i]=tuple(goals[chosen]);ends[i]=e['step']
            rules._apply_unit_action(obs['farms'][seat],obs['private'],i,['PASS'] if a[0]=='PLANT' and a[1] in blocked else a,10,t//24,24,100)
            if i in ends and ends[i]==t:previous[i]=committed.pop(i);ends.pop(i)
        prefix=[];requested=list(act.get('market',[]))[:10]
        for slot in range(min(10,len(requested)+1)):
            if slot==len(requested):tok,q=0,0
            else:
                tok,q,known=A.market_token(requested[slot]);assert known
                if A.MARKET_TOKENS[tok] in ['HIRE','BUY_LAND']:q=1
            mx.append(F.market_features(obs,slot,prefix,committed));my.append(tok);mqy.append(q)
            if tok==0:break
            applied=F.apply_market(obs,tok,q)
            counts['own_shadow_unfilled_request']+=applied is None
            prefix.append((tok,q))
    out=B/'task_policy_data'/version;out.mkdir(parents=True,exist_ok=True)
    arrays={'rank_x':np.concatenate(rx),'rank_y':np.asarray(ry,np.int8),'quantity_x':np.asarray(gx,np.float32),'quantity_y':np.asarray(gq,np.float32),'market_x':np.asarray(mx,np.float32),'market_y':np.asarray(my,np.int16),'market_quantity':np.asarray(mqy,np.float32)}
    if vx:arrays.update(validation_x=np.concatenate(vx),validation_choice=np.asarray(vy,np.int32),validation_offsets=np.asarray(vo,np.int32))
    target=out/f'{row["split"]}_{index:03}.npz';np.savez_compressed(target,**arrays)
    result={'index':index,'source_sha256':digest,'source_path':row['path'],'source_seed':row['seed'],'split':row['split'],'source_exact_719_states':True,'queries':query_number,'counts':dict(counts),'arrays':{k:list(v.shape) for k,v in arrays.items()},'sha256':sha(target),'seconds':time.perf_counter()-start}
    (out/f'{row["split"]}_{index:03}.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');ap.add_argument('--workers',type=int,default=4);ap.add_argument('--limit',type=int);a=ap.parse_args()
    manifest=json.loads((B/'ddbd/training_manifest.json').read_text());rows=[r for r in manifest['all_splits'] if r['split'] in ['train','validation']]
    if a.limit:rows=rows[:a.limit]
    # all_splits is source data only; no evaluation opponents or generated y68 action labels.
    tasks=[(a.version,r,i) for i,r in enumerate(rows)];out=B/'task_policy_data'/a.version;out.mkdir(parents=True,exist_ok=True)
    hashes={str(p.relative_to(B)):sha(p) for p in [Path(__file__),*(B/a.version).glob('*.py'),B/a.version/'config.json']}
    plan={'version':a.version,'rows':rows,'hashes':hashes,'test_opened':False,'selection':'Existing Boey seed-separated train/validation; full-candidate validation sampled every 32nd query.'}
    p=out/'plan.json'
    if p.exists():assert json.loads(p.read_text())==plan
    else:p.write_text(json.dumps(plan,indent=2)+'\n')
    results=[];pending=[]
    for task in tasks:
        row=task[1];p=out/f'{row["split"]}_{task[2]:03}.json'
        if p.exists():
            r=json.loads(p.read_text());assert sha(p.with_suffix('.npz'))==r['sha256'];results.append(r)
        else:pending.append(task)
    for start in range(0,len(pending),24):
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
            for r in pool.map(compile_one,pending[start:start+24]):results.append(r);print(json.dumps({k:r[k] for k in ['index','split','queries','counts','seconds']}),flush=True)
    assert hashes=={p:sha(B/p) for p in hashes}
    (out/'manifest.json').write_text(json.dumps({'expected':len(tasks),'completed':len(results),'rows':results,'source_exact_states':all(r['source_exact_719_states'] for r in results)},indent=2)+'\n')
if __name__=='__main__':main()
