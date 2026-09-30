"""Identical batch/inference feature contract; quantized to match replay cache."""
import numpy as np
def common(global_x,board,units,step):
    g=np.asarray(global_x,dtype=np.float16).astype(np.float32)
    b=np.asarray(board,dtype=np.float16).astype(np.float32).reshape(-1,100,21)
    u=np.asarray(units,dtype=np.float16).astype(np.float32)
    t=np.asarray(step,dtype=np.float32).reshape(-1,1)
    return np.concatenate([g.reshape(len(b),-1),b[:,:,:13].argmax(-1),
        b[:,:,13:19].reshape(len(b),-1),b[:,:,19],u[:,:,2:4].reshape(len(b),-1),t,t//24,t%24],axis=1).astype(np.float32)

def local(common_x,units,i):
    return np.concatenate([common_x,np.asarray(units[:,i],dtype=np.float16).astype(np.float32)],axis=1)

def market(common_x,unit_codes,prefix):
    return np.concatenate([common_x,np.asarray(unit_codes,dtype=np.float32),np.asarray(prefix,dtype=np.float32)],axis=1)
