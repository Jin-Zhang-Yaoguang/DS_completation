"""Synthetic check of the actual predictor and non-state-dict mask temperature."""
import importlib.util,json,tempfile
from pathlib import Path
import numpy as np
import torch

P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('hpmn_runner_smoke',P/'run.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
m=r.module('hpmn_smoke_public',r.R/'model/diagnostics/hpmn_source_audit_20260910/public_components.py')
torch.manual_seed(43);torch.set_num_threads(4)
m.DEVICE=torch.device('mps')
x=np.random.default_rng(43).normal(size=(256,148)).astype('float32')
model=m.HierarchicalMatcher(148).to(m.DEVICE)
model.initialize_centers(x,seed=8143);model.set_mask_temperature(.55)
opt=torch.optim.AdamW(model.parameters(),lr=m.LR,weight_decay=m.WEIGHT_DECAY)
for _ in range(3):
    opt.zero_grad()
    loss=torch.nn.functional.binary_cross_entropy_with_logits(model(torch.from_numpy(x).to(m.DEVICE)),(torch.arange(len(x))%2).float().to(m.DEVICE))+model.regularization()
    loss.backward()
    assert bool(torch.isfinite(loss))
    assert all(bool(torch.isfinite(v.grad).all()) for v in model.parameters() if v.grad is not None)
    opt.step()
q=r.predict(model,x,m.DEVICE)
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp)/'model.pt'
    torch.save({'state':{k:v.detach().cpu() for k,v in model.state_dict().items()},'temperature':.55,'epoch':3},p)
    state=torch.load(p,map_location='cpu',weights_only=True)
    other=m.HierarchicalMatcher(148).to(m.DEVICE)
    other.load_state_dict(state['state']);other.set_mask_temperature(state['temperature'])
    replay=r.predict(other,x,m.DEVICE)
    np.testing.assert_array_equal(q,replay)
out={'status':'PASS','runner_sha':r.sha(P/'run.py'),'rows':256,'features':148,'device':'mps','nondefault_temperature':.55,'reload_max_abs':float(abs(q-replay).max()),'finite_gradients':True,'real_data_used':False}
r.write(P/'smoke.json',out)
print(json.dumps(out))
