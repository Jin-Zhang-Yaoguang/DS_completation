"""Fit a separate single-team prototype student from official daily replay files."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,sys,shutil
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'dda'));import contract,action_space
def encode(task):
    row,out=task;path=Path(row['path']);raw=path.read_bytes();d=json.loads(raw);seat=row['seat'];arrays={}
    assert d['module_version']=='1.32.7' and len(d['steps'])==720 and d['statuses']==['DONE','DONE']
    for t in range(719):
        obs=d['steps'][t][seat]['observation'];obs['step']=t;x=contract.encode(obs);label=action_space.encode_action(obs,d['steps'][t+1][seat]['action']);n=action_space.unit_count(obs)
        assert n<=16 and all(label['unit_known']) and all(label['market_known'])
        values={'board':x['board'],'global':x['global'],'units':x['units'][:,:16],
                'unit_tokens':np.pad(label['unit_tokens'],(0,16-n)),
                'unit_quantities':np.pad(label['unit_quantities'],(0,16-n)),
                'market_tokens':label['market_tokens'],'market_quantities':label['market_quantities']}
        for k,v in values.items():arrays.setdefault(k,[]).append(v)
    arrays={k:np.asarray(v,dtype=np.float16 if k in ['board','global','units'] else np.int16) for k,v in arrays.items()}
    np.savez_compressed(Path(out)/f"{row['episode_id']}.npz",**arrays)
    return {**row,'sha256':hashlib.sha256(raw).hexdigest()}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');ap.add_argument('teacher');ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    D=B/a.version;assert not D.exists();D.mkdir();(D/'data').mkdir();cache=D/'training_cache';cache.mkdir()
    for p in (B/'dda').glob('*.py'):shutil.copy2(p,D/p.name)
    p=D/'main.py';s=p.read_text().replace("price=rules.market_price(item,ms['inventory'][item],ms['params'])","price=rules.market_price(item,ms['inventory'][item]-(op=='BUY_PRODUCT'),ms['params'])");p.write_text(s)
    inventory=json.loads((B/'teacher_inventory_20260917_18.json').read_text());rows=[]
    for r in inventory['rows']:
        if a.teacher not in r['teams']:continue
        seat=r['teams'].index(a.teacher);bucket=int(hashlib.sha256(f"dd-team-20260920:{r['seed']}".encode()).hexdigest()[:8],16)%100
        rows.append({**r,'seat':seat,'cash':r['rewards'][seat],'margin':r['rewards'][seat]-r['rewards'][1-seat],
                     'split':'train' if bucket<70 else 'validation' if bucket<85 else 'test'})
    train=[r for r in rows if r['split']=='train'];assert len(train)>20
    results=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
        for i,r in enumerate(pool.map(encode,[(r,str(cache)) for r in train])):
            results.append(r)
            if i%10==0:print('encoded',a.version,i,len(train),flush=True)
    arrays={};n=len(results)
    for i,r in enumerate(results):
        with np.load(cache/f"{r['episode_id']}.npz") as z:
            for name in z.files:
                v=z[name]
                if name not in arrays:arrays[name]=np.lib.format.open_memmap(D/'data'/f'{name}.npy',mode='w+',dtype=v.dtype,shape=(719,n,*v.shape[1:]))
                arrays[name][:,i]=v
    for x in arrays.values():x.flush()
    (D/'training_manifest.json').write_text(json.dumps({'method':'single-team joint-action nonparametric behavioral cloning','teacher':a.teacher,
        'submission_version':'unknown in daily dataset; no claim of one executable version','train_episodes':n,'frames':n*719,
        'episodes':results,'all_splits':rows,'source':'official daily replay archive 2026-09-17 through 2026-09-18'},ensure_ascii=False,indent=2)+'\n')
    cfg=json.loads((B/'dda/config.json').read_text());cfg['version']=a.version;(D/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    reg=json.loads((B/'registry.json').read_text());reg['versions'].append({'version':a.version,'index':len(reg['versions']),
        'status':'BUILT','method':'Single-team joint-action distillation: '+a.teacher,'hypothesis':'Test whether a different strong teacher is easier to distill than Majkel','teacher':a.teacher})
    (B/'registry.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n')
    (D/'README.md').write_text(f'# {a.version}\n\n教师：{a.teacher}。来自官方三日公开回放，按 seed 分组切分。日数据不含可靠提交版本归属，可能包含版本变化；当前只作为独立教师人群实验。编码逐帧从原始 JSON 构建并保存 SHA，运行模型不读队名或 seed。\n')
    print('built',a.version,n,'train',len(rows),'total',flush=True)
if __name__=='__main__':main()
