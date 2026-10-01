"""Bounded synthetic MPS compatibility/throughput check; no competition data."""
from pathlib import Path
import importlib.util,json,time,resource,signal
import numpy as np
import torch

P=Path(__file__).resolve().parent
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('120 second synthetic budget')))
signal.alarm(120)
spec=importlib.util.spec_from_file_location('hpmn_public',P/'public_components.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
torch.set_num_threads(4);torch.manual_seed(21)
m.DEVICE=torch.device('mps')
assert torch.backends.mps.is_available()
model=m.HierarchicalMatcher(204).to(m.DEVICE)
x=np.random.default_rng(21).normal(size=(2048,204)).astype('float32')
model.initialize_centers(x,seed=8121)
xb=torch.from_numpy(x).to(m.DEVICE)
yb=(torch.arange(len(x))%2).float().to(m.DEVICE)
opt=torch.optim.AdamW(model.parameters(),lr=m.LR,weight_decay=m.WEIGHT_DECAY)
timings=[]
for step in range(6):
    torch.mps.synchronize();start=time.monotonic()
    opt.zero_grad(set_to_none=True)
    loss=torch.nn.functional.binary_cross_entropy_with_logits(model(xb),yb)+model.regularization()
    loss.backward()
    assert bool(torch.isfinite(loss))
    assert all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None)
    torch.nn.utils.clip_grad_norm_(model.parameters(),m.GRAD_CLIP)
    opt.step();torch.mps.synchronize()
    timings.append(time.monotonic()-start)
with torch.no_grad():
    p=model(xb)
    other=m.HierarchicalMatcher(204).to(m.DEVICE)
    other.load_state_dict(model.state_dict())
    err=float((p-other(xb)).abs().max())
    assert err==0
out={'status':'PASS','device':'mps','batch_size':2048,'features':204,
     'steps':6,'seconds_per_step':timings,'median_warm_step':float(np.median(timings[1:])),
     'reload_max_abs':err,'peak_memory_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
     'real_data_used':False,'competition_score_computed':False,
     'scope':'Synthetic throughput only; real training, validation and feature engineering add cost.'}
(P/'synthetic_mps.json').write_text(json.dumps(out,indent=2))
signal.alarm(0)
print(json.dumps(out))
