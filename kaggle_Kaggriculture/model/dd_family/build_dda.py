"""Fit a nonparametric joint-action student from optimization-train replay only."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np

B=Path(__file__).resolve().parent
SOURCE=B.parent/'v126_majkel_neural_bc'
DEST=B/'dda'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    DEST.mkdir(exist_ok=True)
    provenance={}
    for name in ['features.py','action_space.py','rules.py','contract.py']:
        shutil.copy2(SOURCE/name,DEST/name);provenance[name]={'source':str(SOURCE/name),'sha256':sha(DEST/name)}
    manifest=json.loads((SOURCE/'split_manifest.json').read_text())
    rows=[r for r in manifest['episodes'] if r['split']=='train'];n=len(rows)
    assert n==271
    data=DEST/'data';data.mkdir(exist_ok=True)
    # Input floats stored by decision time for locality; episodes are only provenance.
    for name in ['board','global','units','unit_tokens','unit_quantities','market_tokens','market_quantities']:
        src=np.load(SOURCE/'data/train'/f'{name}.npy',mmap_mode='r')
        tail=src.shape[1:];arr=src.reshape(n,719,*tail)
        if name=='units':arr=arr[:,:,:,:16];tail=(16,16)
        target=np.lib.format.open_memmap(data/f'{name}.npy',mode='w+',dtype=arr.dtype,shape=(719,n,*tail))
        for t in range(719):target[t]=arr[:,t]
        target.flush();print('built',name,target.shape,flush=True)
    (DEST/'training_manifest.json').write_text(json.dumps({'method':'nonparametric joint-action behavioral cloning',
        'input':'acting-seat legal visible state; same decision-time support',
        'train_episodes':n,'frames':n*719,'teacher_submission':'56156662',
        'source_manifest_sha256':sha(SOURCE/'split_manifest.json'),
        'episodes':rows,'reuse':provenance,
        'data_sha256':{p.name:sha(p) for p in sorted(data.glob('*.npy'))}},indent=2)+'\n')
    (DEST/'config.json').write_text(json.dumps({'version':'dda','continuity_bonus':0.25,
        'board_scale':1.0,'position_scale':1.0,'market_mode':'teacher'},indent=2)+'\n')
if __name__=='__main__':main()
