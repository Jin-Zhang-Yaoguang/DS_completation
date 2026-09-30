"""Index verified training demonstrations by their exact endogenous own state."""
from pathlib import Path
import collections,concurrent.futures,hashlib,json
import numpy as np
from exact_support import key
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(task):
    index,row=task;p=Path(row['path']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat'];keys=[];actions=[]
    for t in range(719):
        obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);obs.update(step=t,player=seat);keys.append(key(obs))
        actions.append(hashlib.blake2b(json.dumps(rep['steps'][t+1][seat]['action'],sort_keys=True,separators=(',',':')).encode(),digest_size=16).hexdigest())
    return index,np.asarray(keys,'S32'),np.asarray(actions,'S32')
def main():
    source=B/'ddam/training_manifest.json';rows=json.loads(source.read_text())['episodes'];assert len(rows)==146 and all(r['split']=='train' for r in rows)
    verified={r['source_sha256'] for r in json.loads((B/'task_policy_data/ddbo/manifest.json').read_text())['rows'] if r['source_exact_719_states']};assert all(r['sha256'] in verified for r in rows)
    out=B/'prefix_policy_data';out.mkdir(exist_ok=True);assert not (out/'physical_keys.npy').exists();keys=np.empty((719,len(rows)),dtype='S32');actions=np.empty_like(keys)
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:
        for index,k,a in pool.map(run,enumerate(rows)):keys[:,index]=k;actions[:,index]=a
    np.save(out/'physical_keys.npy',keys);np.save(out/'action_keys.npy',actions);daily=[]
    for day in range(30):
        ambiguous_states=0;multi_states=0;groups_total=0;nodes_in_ambiguous=0
        for t in range(day*24,min((day+1)*24,719)):
            groups=collections.defaultdict(list)
            for j,k in enumerate(keys[t]):groups[k].append(j)
            for ids in groups.values():
                groups_total+=1;multi_states+=len(ids)>1
                if len(set(actions[t,ids]))>1:ambiguous_states+=1;nodes_in_ambiguous+=len(ids)
        daily.append({'day':day,'physical_groups':groups_total,'multi_source_groups':multi_states,'groups_with_different_joint_actions':ambiguous_states,'source_nodes_at_real_branches':nodes_in_ambiguous})
    report={'source_manifest_sha256':sha(source),'sources':len(rows),'teacher':'M & M & P & Q; program identity unknown','test_used':False,'key_fields':'Step, complete own public farm except money, own private shed/seeds/bags; zero counts normalized. No future fields.','source_states_already_verified_by':'task_policy_data/ddbo/manifest.json','source_rows':rows,'daily':daily,'hashes':{p.name:sha(p) for p in out.glob('*.npy')},'encoder_sha256':sha(B/'exact_support.py')};(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'sources':len(rows),'shape':list(keys.shape),'daily':daily},indent=2))
if __name__=='__main__':main()
