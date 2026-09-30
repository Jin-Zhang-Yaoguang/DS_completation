"""Small NumPy candidate scorer; normalization is fitted on source train rows only."""
import numpy as np
class Model:
    def __init__(self,path):
        with np.load(path) as z:self.a={k:z[k] for k in z.files}
    def predict(self,x):
        w=self.a;x=np.clip((np.asarray(x,np.float32)-w['mean'])/w['scale'],-10,10)
        x=np.maximum(0,x@w['0.weight'].T+w['0.bias'])
        x=np.maximum(0,x@w['2.weight'].T+w['2.bias'])
        return (x@w['4.weight'].T+w['4.bias'])[:,0]
