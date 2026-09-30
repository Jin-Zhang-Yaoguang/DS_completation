"""Strictly previous, same-day, same-unit request histories; no source IDs as features."""
from pathlib import Path
import hashlib,json
import numpy as np
B=Path(__file__).resolve().parent;SRC=B/'neural_joint_data';OUT=B/'neural_history_data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(exist_ok=False);source=json.loads((SRC/'manifest.json').read_text());checks={}
    for split in ['train','validation']:
        for name in ['y','counts']:
            p=SRC/f'{split}_{name}.npy';assert sha(p)==source['hashes'][p.name]
        y=np.load(SRC/f'{split}_y.npy');count=np.load(SRC/f'{split}_counts.npy');assert len(y)%719==0
        history=np.zeros((len(y),26,4),np.int16);ids=np.arange(len(y));hour=(ids%719)%24
        for lag in range(1,5):
            take=ids[hour>=lag];previous=take-lag;history[take,:,lag-1]=y[previous]
            inactive=np.arange(16)[None,:]>=count[previous,None];v=history[take,:16,lag-1];v[inactive]=0;history[take,:16,lag-1]=v
        # Independent streaming reconstruction, reset on each episode and day.
        checked=0;new_worker_slots=0
        for episode in range(len(y)//719):
            past=[]
            for t in range(719):
                idx=episode*719+t
                if t%24==0:past=[]
                expected=np.zeros((26,4),np.int16)
                for lag,(labels,n) in enumerate(reversed(past[-4:])):
                    expected[:n,lag]=labels[:n];expected[16:,lag]=labels[16:]
                assert np.array_equal(expected,history[idx]),(split,episode,t)
                if t%24 and count[idx]>count[idx-1]:
                    assert not history[idx,int(count[idx-1]):int(count[idx]),:].any();new_worker_slots+=int(count[idx]-count[idx-1])
                past.append((y[idx],int(count[idx])));checked+=1
        np.save(OUT/f'{split}_history.npy',history);checks[split]={'exact_streaming_frames':checked,'new_worker_slots_zeroed':new_worker_slots,'day_zero_history':bool((history[hour==0]==0).all())}
    report={'source_manifest_sha256':sha(SRC/'manifest.json'),'compiler_sha256':sha(Path(__file__)),'shape_per_frame':[26,4],'lag_order':[1,2,3,4],'padding':0,'semantics':'Previous emitted/requested actions, not successful outcomes. Unit slot histories are absent before the worker exists. Reset all history at day start and episode start. Market slots keep previous same-slot requests, including STOP padding. No current/future labels.','checks':checks,'hashes':{p.name:sha(p) for p in OUT.glob('*.npy')}}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
