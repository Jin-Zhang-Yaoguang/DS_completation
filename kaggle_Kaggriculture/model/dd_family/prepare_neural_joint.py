"""Train-only raw-request vocabulary and causal state tensors for ddbu."""
from pathlib import Path
import collections,concurrent.futures,hashlib,json,shutil,sys
import numpy as np
B=Path(__file__).resolve().parent
OUT=B/'neural_joint_data'
sys.path.insert(0,str(B/'ddam'))
import contract,action_space as space
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atom(domain,order):
    return json.dumps([domain,order],separators=(',',':'))
def read_one(task):
    index,row=task;p=Path(row['path']);raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest()
    verified=json.loads((B/'task_policy_data/ddbo/manifest.json').read_text())['rows']
    assert any(r['source_sha256']==h and r['source_exact_719_states'] for r in verified)
    if row.get('sha256'):assert row['sha256']==h
    rep=json.loads(raw);seat=row['seat'];x=[];labels=[];masks=[];counts=[]
    for t in range(719):
        obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);obs.update(step=t,player=seat)
        e=contract.encode(obs);x.append(np.concatenate([e['global'],e['board'],e['units'][:,:16].ravel()]))
        action=rep['steps'][t+1][seat]['action'];n=space.unit_count(obs);assert n<=16
        orders=[action.get('farmer',['PASS'])]+action.get('hands',[])
        u=[atom('unit',orders[i] if i<len(orders) else ['PASS']) if i<n else atom('unit',['PASS']) for i in range(16)]
        market=action.get('market',[])[:10];v=[atom('market',market[i] if i<len(market) else None) for i in range(10)]
        labels.append(u+v);masks.append([i<n for i in range(16)]+[i<=len(market) for i in range(10)]);counts.append(n)
    np.save(OUT/f'{index:03}_x.npy',np.asarray(x,np.float16))
    return {'index':index,'split':row['split'],'source_sha256':h,'source_seed':row['seed'],'source_path':str(p),'labels':labels,'mask':masks,'counts':counts}
def main():
    OUT.mkdir(exist_ok=False)
    source=json.loads((B/'ddam/training_manifest.json').read_text());rows=[r for r in source['all_splits'] if r['split']!='test'];assert collections.Counter(r['split'] for r in rows)=={'train':146,'validation':40}
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:compiled=list(pool.map(read_one,enumerate(rows)))
    vocabulary=sorted({a for r in compiled if r['split']=='train' for frame in r['labels'] for a in frame})
    vocabulary=['BOS','UNK']+vocabulary;lookup={v:i for i,v in enumerate(vocabulary)};assert len(vocabulary)<32768
    manifest=[]
    for split in ['train','validation']:
        subset=[r for r in compiled if r['split']==split];x=np.lib.format.open_memmap(OUT/f'{split}_x.npy',mode='w+',dtype=np.float16,shape=(719*len(subset),2531));ys=[];ms=[];ns=[];unknown=0
        for j,r in enumerate(subset):
            block=np.load(OUT/f'{r["index"]:03}_x.npy');assert block.shape==(719,2531);x[j*719:(j+1)*719]=block
            y=np.asarray([[lookup.get(v,1) for v in frame] for frame in r['labels']],np.int16);mask=np.asarray(r['mask'],bool);unknown+=int(((y==1)&mask).sum());ys.append(y);ms.append(mask);ns.extend(r['counts']);manifest.append({k:v for k,v in r.items() if k not in ['labels','mask','counts']})
        x.flush();np.save(OUT/f'{split}_y.npy',np.concatenate(ys));np.save(OUT/f'{split}_mask.npy',np.concatenate(ms));np.save(OUT/f'{split}_counts.npy',np.asarray(ns,np.int16));print(json.dumps({'split':split,'frames':len(x),'unknown_active_labels':unknown}),flush=True)
    for p in OUT.glob('[0-9][0-9][0-9]_x.npy'):p.unlink()
    (OUT/'vocabulary.json').write_text(json.dumps(vocabulary,indent=2)+'\n')
    report={'teacher':source['teacher'],'rows':manifest,'test_opened':False,'vocabulary_size':len(vocabulary),'label':'Exact public teacher requests, preserving quantities and simultaneous atomic semantics. Not teacher logits or executed-action labels.','features':'175 global + 2100 own-board + 16*16 worker state; decision-time observation only. No seed, source identity or future fields.','source_manifest_sha256':sha(B/'ddam/training_manifest.json'),'compiler_sha256':sha(Path(__file__)),'hashes':{p.name:sha(p) for p in OUT.glob('*.npy')}}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print('compiled',len(rows),'vocab',len(vocabulary),flush=True)
if __name__=='__main__':main()
