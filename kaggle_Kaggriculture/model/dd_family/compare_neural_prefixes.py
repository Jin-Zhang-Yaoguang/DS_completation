"""Same true observations, compare teacher-forced versus generated action prefixes.

This is an offline exposure diagnostic, not an environment rollout or win rate.
"""
from pathlib import Path
import collections,hashlib,importlib.util,json,sys,time
import numpy as np
B=Path(__file__).resolve().parent;DATA=B/'neural_joint_data'
def category(atom):
    domain,order=atom
    if domain=='market':return 'market_stop' if order is None else 'market_'+order[0]
    name=order[0]
    if name in ['NORTH','SOUTH','EAST','WEST']:return 'movement'
    if name in ['WATER','FEED','CARE','FERTILIZE']:return 'maintenance'
    if name in ['HARVEST','COLLECT_FERTILIZER','DROP']:return 'collection'
    if name in ['PLANT','PLACE','BUILD_COOP','BUILD_PASTURE']:return 'production'
    return name
def run(version):
    d=B/version;sys.path.insert(0,str(d));spec=importlib.util.spec_from_file_location('candidate_'+version,d/'main.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);agent=m.Agent()
    raw=np.load(DATA/'validation_x.npy',mmap_mode='r');labels=np.load(DATA/'validation_y.npy',mmap_mode='r');masks=np.load(DATA/'validation_mask.npy',mmap_mode='r');counts=np.load(DATA/'validation_counts.npy',mmap_mode='r');ids=np.random.default_rng(839127).choice(len(raw),512,replace=False)
    local=np.load(B/'neural_local_data/validation_local.npy',mmap_mode='r') if agent.w['gru.weight_ih_l0'].shape[1]>96 else None
    tally={mode:collections.defaultdict(lambda:[0,0]) for mode in ['teacher_prefix','generated_prefix']};joints=collections.Counter()
    for index in ids:
        x=np.clip((raw[index].astype(np.float32)-agent.w['mean'])/agent.w['scale'],-10,10)
        if local is not None:x=np.concatenate([x,local[index].astype(np.float32).ravel()])
        for mode in tally:
            hidden=agent.initial(x);previous=0;allmatch=True;stopped=False
            for slot in range(26):
                hidden,logits=agent.step(x,hidden,previous,slot);code=agent.pass_id if counts[index]<=slot<16 else agent.stop_id if stopped else int(logits.argmax());truth=int(labels[index,slot])
                if masks[index,slot] and truth!=1:
                    equal=code==truth;cat=category(agent.atoms[truth]);tally[mode][cat][0]+=int(equal);tally[mode][cat][1]+=1;tally[mode]['all'][0]+=int(equal);tally[mode]['all'][1]+=1;allmatch&=equal
                previous=truth if mode=='teacher_prefix' else code
                if mode=='generated_prefix' and slot>=16 and code==agent.stop_id:stopped=True
            joints[mode]+=allmatch
    return {'version':version,'weights_sha256':hashlib.sha256((d/'weights.npz').read_bytes()).hexdigest(),'frames':len(ids),'modes':{mode:{'exact_all_known_frames':int(joints[mode]),'categories':{cat:{'correct':v[0],'count':v[1],'accuracy':v[0]/v[1]} for cat,v in cats.items()}} for mode,cats in tally.items()}}
if __name__=='__main__':
    versions=sys.argv[1:] or ['ddbu','ddbv'];rows=[run(v) for v in versions];out={'scope':'512 fixed validation decision-time states; generated prefixes only within a turn, not autonomous environmental trajectories. Unknown targets excluded.','rows':rows};(B/'diagnostics'/('neural_prefix_'+'_'.join(versions)+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
