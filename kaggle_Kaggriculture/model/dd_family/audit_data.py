"""Check actual replay alignment, cache provenance, seed isolation and visible-input contract."""
from pathlib import Path
import concurrent.futures,copy,hashlib,importlib.util,json,sys
import numpy as np
B=Path(__file__).resolve().parent
def check_hash(row):
    p=Path(row['path']);h=hashlib.sha256(p.read_bytes()).hexdigest()
    assert h==row['sha256'],str(p)
    return p.stat().st_size
def main(version):
    D=B/version;sys.path.insert(0,str(D));import main as policy,contract,action_space
    manifest=json.loads((D/'training_manifest.json').read_text());rows=manifest['episodes']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:sizes=list(pool.map(check_hash,rows))
    arr={p.stem:np.load(p,mmap_mode='r') for p in (D/'data').glob('*.npy')}
    checked=0;seeds=[]
    for k in sorted(set([0,len(rows)//4,len(rows)//2,3*len(rows)//4,len(rows)-1])):
        r=rows[k];replay=json.loads(Path(r['path']).read_text());seat=r['seat']
        assert replay['module_version']=='1.32.7' and len(replay['steps'])==720
        seeds.append(replay['info']['seed'])
        for t in [0,23,24,143,144,358,718]:
            obs=replay['steps'][t][seat]['observation'];obs['step']=t
            encoded=contract.encode(obs)
            for key in ['board','global','units']:
                want=encoded[key][:,:16] if key=='units' else encoded[key]
                assert np.array_equal(arr[key][t,k],want.astype(np.float16)),(version,k,t,key)
            label=action_space.encode_action(obs,replay['steps'][t+1][seat]['action'])
            n=action_space.unit_count(obs)
            for key in ['unit_tokens','unit_quantities','market_tokens','market_quantities']:
                count=n if key.startswith('unit_') else 10
                assert np.array_equal(arr[key][t,k,:count],label[key]),(version,k,t,key)
            polluted=copy.deepcopy(obs);polluted['seed']=91829999;polluted['EpisodeId']=1234;polluted['future_shops']=['YARN_STORE']*8
            test=contract.encode(polluted)
            assert all(np.array_equal(encoded[key],test[key]) for key in encoded)
            checked+=1
    assert len(rows)==len(arr['board'][0])
    protocol=json.loads((B/'protocol.json').read_text())
    if 'all_splits' in manifest:
        groups={s:{r['seed'] for r in manifest['all_splits'] if r['dd_split']==s} for s in ['train','validation','test']}
    else:
        source=json.loads(Path(protocol['source_split_manifest']).read_text())
        groups={}
        for r in source['episodes']:
            if r['submission_id']!='56156662':continue
            p=B.parent/'v126_majkel_neural_bc/data/episodes'/f"{r['episode_id']}.npz"
            with np.load(p) as z:seed=int(z['seed'])
            groups.setdefault(r['split'],set()).add(seed)
    assert not groups['train']&groups['validation'] and not groups['train']&groups['test'] and not groups['validation']&groups['test']
    allseeds=set.union(*groups.values());assert not allseeds&set(protocol['development_seeds'])
    assert not any(919300000<=s<920300000 for s in allseeds),'Reserved candidate seed range collides with replay'
    out={'version':version,'raw_sha_verified':len(rows),'raw_bytes':sum(sizes),'aligned_samples_verified':checked,
         'visible_feature_contract':'pass','seed_split_disjoint':'pass','development_and_reserved_gate_seeds_disjoint':'pass'}
    (B/f'audit_{version}.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
if __name__=='__main__':main(sys.argv[1])
