"""Numpy-only prediction from explicitly exported sklearn trees."""
import numpy as np

class Model:
    def __init__(self,path):
        with np.load(path) as z:self.a={k:z[k] for k in z.files}
    def predict(self,x):
        a=self.a;x=np.asarray(x,np.float32).reshape(-1,int(a['dimensions']))
        if len(x)>=64:
            n=len(x);nodes=np.repeat(a['roots'],n);active=np.arange(len(nodes),dtype=np.int32)
            for _ in range(int(a['depth'])):
                current=nodes[active];mask=a['left'][current]!=current;active=active[mask];current=current[mask]
                if not len(active):break
                f=a['feature'][current];values=x[active%n,f]
                nodes[active]=np.where(values<=a['threshold'][current],a['left'][current],a['right'][current])
            values=a['value'][nodes.reshape(len(a['roots']),n)]
            if int(a['kind'])==0:return values.sum(0)+a['baseline']
            return values.mean(0)
        nodes=np.broadcast_to(a['roots'][:,None],(len(a['roots']),len(x))).copy()
        for _ in range(int(a['depth'])):
            f=a['feature'][nodes];v=x[np.arange(len(x))[None,:],f]
            nodes=np.where(v<=a['threshold'][nodes],a['left'][nodes],a['right'][nodes])
        values=a['value'][nodes]
        if int(a['kind'])==0:return values.sum(0)+a['baseline']
        return values.mean(0)
