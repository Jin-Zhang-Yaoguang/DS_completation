"""仅负责低秩拟合；独立进程避免PyTorch与LightGBM原生运行库冲突。"""
import os,json,time,resource
from pathlib import Path
import numpy as np
import torch
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent
CFG=json.loads((HERE/'preregistration.json').read_text())
torch.set_num_threads(CFG['torch_threads'])
def matrix_fit(inc,ctx,y,ni,nc,rank,seed,guard=lambda:None):
    """输入只包含拟合行及其标签。相同收入与条件组合聚合为二项计数。"""
    flat=inc*nc+ctx
    n=np.bincount(flat,minlength=ni*nc).reshape(ni,nc).astype('float32')
    s=np.bincount(flat,weights=y,minlength=ni*nc).reshape(ni,nc).astype('float32')
    mu=float(np.mean(y));g=np.log(mu/(1-mu))
    mass=CFG['prior_mass'];ns=n.sum(1);nt=n.sum(0)
    def logit(p): return np.log(p/(1-p))
    a=logit((s.sum(1)+mass*mu)/(ns+mass))-g
    b=logit((s.sum(0)+mass*mu)/(nt+mass))-g
    rng=np.random.default_rng(seed)
    aa=torch.nn.Parameter(torch.tensor(a));bb=torch.nn.Parameter(torch.tensor(b));gg=torch.nn.Parameter(torch.tensor(g,dtype=torch.float32))
    pars=[aa,bb,gg]
    if rank:
        uu=torch.nn.Parameter(torch.tensor(rng.normal(0,CFG['initial_scale'],(ni,rank)).astype('float32')))
        vv=torch.nn.Parameter(torch.tensor(rng.normal(0,CFG['initial_scale'],(nc,rank)).astype('float32')))
        pars.extend([uu,vv])
    nn=torch.from_numpy(n);ss=torch.from_numpy(s);opt=torch.optim.Adam(pars,lr=CFG['lr'])
    losses=[]
    for step in range(CFG['steps']):
        opt.zero_grad();z=gg+aa[:,None]+bb[None,:]
        if rank: z=z+uu@vv.T
        loss=(nn*torch.nn.functional.softplus(z)-ss*z).sum()/len(y)
        penalty=aa.square().sum()+bb.square().sum()
        if rank: penalty=penalty+uu.square().sum()+vv.square().sum()
        loss=loss+mass*penalty/(2*len(y));loss.backward();opt.step()
        if step%25==0: guard();losses.append(float(loss.detach()))
    with torch.no_grad():
        aa[torch.from_numpy(ns==0)]=0;bb[torch.from_numpy(nt==0)]=0
        z=gg+aa[:,None]+bb[None,:]
        if rank:
            uu[torch.from_numpy(ns==0)]=0;vv[torch.from_numpy(nt==0)]=0;z=z+uu@vv.T
        z=z.clamp(-CFG['score_clip'],CFG['score_clip']).numpy().copy()
    assert np.isfinite(z).all()
    return z,{'loss_start':losses[0],'loss_last':float(loss.detach()),'rank':rank,'rows':len(y)}

if __name__=='__main__':
    import sys
    inp,out=map(Path,sys.argv[1:3]);z=np.load(inp);inc=z['inc'];ctx=z['ctx'];y=z['y'];qi=z['query_inc'];qc=z['query_ctx'];ni=int(z['ni']);nc=int(z['nc']);fold=int(z['fold'])
    start=time.monotonic()
    def guard():
        assert time.monotonic()-start<float(os.environ.get('MF_SECONDS','1500'))
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<float(os.environ.get('MF_MEMORY','8589934592'))
    sf=np.full((len(y),2),np.nan);sv=np.zeros((len(qi),2));logs=[]
    inner=list(StratifiedKFold(CFG['inner_folds'],shuffle=True,random_state=42+fold).split(np.zeros(len(y)),y))
    for arm,rank in enumerate([0,CFG['rank']]):
        for k,(tr,va) in enumerate(inner):
            m,d=matrix_fit(inc[tr],ctx[tr],y[tr],ni,nc,rank,CFG['model_seed']+fold*10+k,guard)
            sf[va,arm]=m[inc[va],ctx[va]];logs.append(d)
        m,d=matrix_fit(inc,ctx,y,ni,nc,rank,CFG['model_seed']+fold*10+9,guard)
        sv[:,arm]=m[qi,qc];logs.append(d);print('MATRIX_ARM_DONE',fold,rank,flush=True)
    assert np.isfinite(sf).all() and np.isfinite(sv).all()
    np.savez_compressed(out,fit_scores=sf,query_scores=sv)
    out.with_suffix('.json').write_text(json.dumps({'logs':logs,'seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},indent=2)+'\n')
