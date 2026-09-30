"""Derive local tile features from causal cached states, preserving old datasets."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
B=Path(__file__).resolve().parent;SRC=B/'neural_joint_data';OUT=B/'neural_local_data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def derive(raw):
    board=raw[:,175:2275].reshape(-1,10,10,21);units=raw[:,2275:].reshape(-1,16,16)
    xy=np.rint(units[:,:,2:4].astype(np.float32)*9).astype(int);out=[]
    for dx,dy in [(0,0),(0,-1),(0,1),(1,0),(-1,0)]:
        xx=xy[:,:,0]+dx;yy=xy[:,:,1]+dy;valid=(xx>=0)&(xx<10)&(yy>=0)&(yy<10)
        tile=board[np.arange(len(raw))[:,None],np.clip(yy,0,9),np.clip(xx,0,9)].copy();tile[~valid]=0;tile[:,:,0][~valid]=1;tile*=units[:,:,:1];out.append(tile)
    return np.concatenate(out,-1)
def main():
    OUT.mkdir(exist_ok=False);m=json.loads((SRC/'manifest.json').read_text())
    for split in ['train','validation']:
        p=SRC/f'{split}_x.npy';assert sha(p)==m['hashes'][p.name];raw=np.load(p,mmap_mode='r');out=np.lib.format.open_memmap(OUT/f'{split}_local.npy',mode='w+',dtype=np.float16,shape=(len(raw),16,105))
        for lo in range(0,len(raw),4096):out[lo:lo+4096]=derive(raw[lo:lo+4096])
        out.flush()
    sys.path.insert(0,str(B/'ddam'));import contract
    originals=json.loads((B/'ddam/training_manifest.json').read_text())['all_splits'];lookup={r['path']:r for r in originals};checked=0
    for split in ['train','validation']:
        rows=[r for r in m['rows'] if r['split']==split];local=np.load(OUT/f'{split}_local.npy',mmap_mode='r')
        for j in [0,len(rows)//3,len(rows)//2,len(rows)-1]:
            r=rows[j];p=Path(r['source_path']);assert sha(p)==r['source_sha256'];rep=json.loads(p.read_text());seat=lookup[str(p)]['seat']
            for t in [0,1,72,333,718]:
                obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);obs.update(step=t,player=seat);expected=contract.encode(obs)['units'][:,16:].astype(np.float16);assert np.array_equal(expected,local[j*719+t]);checked+=1
    report={'source_manifest_sha256':sha(SRC/'manifest.json'),'compiler_sha256':sha(Path(__file__)),'replay_encoder_exact_states':checked,'fields':'Current tile and N,S,E,W neighbors, 21 channels each, zero for absent units; static boundary channel0=1. No future information.','hashes':{p.name:sha(p) for p in OUT.glob('*.npy')}}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
