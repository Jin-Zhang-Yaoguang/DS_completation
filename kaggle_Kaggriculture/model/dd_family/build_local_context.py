from pathlib import Path
import sys,json
import numpy as np
B=Path(__file__).resolve().parent
def main(version):
    D=B/version;rows=json.loads((D/'training_manifest.json').read_text())['episodes'];n=len(rows)
    target=np.lib.format.open_memmap(D/'data/unit_context.npy',mode='w+',dtype=np.float16,shape=(719,n,16,121))
    source=B.parent/'v126_majkel_neural_bc/data/episodes'
    for k,r in enumerate(rows):
        with np.load(source/f"{r['episode_id']}.npz") as z:target[:,k]=z['units']
    target.flush();print('built',version,target.shape,flush=True)
if __name__=='__main__':main(sys.argv[1])
