"""Repartition the former version-shift panel for a new explicitly separate experiment."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
B=Path(__file__).resolve().parent;SOURCE=B.parent/'v126_majkel_neural_bc';DEST=B/'dde'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert not DEST.exists()
    DEST.mkdir();(DEST/'data').mkdir()
    for p in (B/'dda').glob('*.py'):shutil.copy2(p,DEST/p.name)
    rows=[r for r in json.loads((SOURCE/'split_manifest.json').read_text())['episodes'] if r['submission_id']=='56216119']
    for r in rows:
        seed=int(np.load(SOURCE/'data/episodes'/f"{r['episode_id']}.npz")['seed'])
        bucket=int(hashlib.sha256(f'dd-recent-20260919:{seed}'.encode()).hexdigest()[:8],16)%100
        r['dd_split']='train' if bucket<70 else 'validation' if bucket<85 else 'test';r['seed']=seed
    train=[r for r in rows if r['dd_split']=='train'];n=len(train)
    assert all(r['submission_id']=='56216119' for r in train)
    arrays={}
    for i,r in enumerate(train):
        source=SOURCE/'data/episodes'/f"{r['episode_id']}.npz"
        with np.load(source) as z:
            for name in ['board','global','units','unit_tokens','unit_quantities','market_tokens','market_quantities']:
                v=z[name]
                if name=='units':v=v[:,:,:16]
                if name not in arrays:arrays[name]=np.lib.format.open_memmap(DEST/'data'/f'{name}.npy',mode='w+',dtype=v.dtype,shape=(719,n,*v.shape[1:]))
                arrays[name][:,i]=v
        if i%20==0:print('built',i,n,flush=True)
    for x in arrays.values():x.flush()
    manifest={'method':'same dda nonparametric architecture, newer teacher only','teacher_submission':'56216119',
              'train_episodes':n,'frames':n*719,'episodes':train,'all_splits':rows,
              'boundary':'Former V126 external-shift panel is now repartitioned for training; it is no longer an external test for dd. New live simulator seeds remain separate.',
              'data_sha256':{p.name:sha(p) for p in (DEST/'data').glob('*.npy')}}
    (DEST/'training_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    cfg=json.loads((B/'dda/config.json').read_text());cfg['version']='dde';(DEST/'config.json').write_text(json.dumps(cfg,indent=2)+'\n')
    (DEST/'README.md').write_text('# dde\n\n与 dda 相同的完整联合动作原型模型，但只使用新版教师 56216119。原 V126 的版本外推面板现重新按 seed 分为训练/验证/测试，不能继续把它称为未见外推测试。真实门控仍使用新 seed。\n')
    reg=json.loads((B/'registry.json').read_text());reg['versions'].append({'version':'dde','index':len(reg['versions']),
        'parent':'dda','status':'BUILDING','method':'New-teacher-only joint-action behavioral cloning',
        'hypothesis':'Separate teacher version effect before further controller changes','teacher':'56216119'})
    reg['next_version']='ddf';(B/'registry.json').write_text(json.dumps(reg,ensure_ascii=False,indent=2)+'\n')
    print('completed train',n,'total',len(rows),flush=True)
if __name__=='__main__':main()
