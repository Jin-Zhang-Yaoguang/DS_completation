"""Validate exported inference against recorded held-out scores and free-running prefixes."""
from pathlib import Path
import json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddj';sys.path.insert(0,str(D));import main,tree_features as F
def batch(tree,x):
    nodes=np.zeros(len(x),np.int32)
    for _ in range(100):
        active=np.flatnonzero(tree['left'][nodes]>=0)
        if not len(active):break
        ids=nodes[active];right=x[active,tree['feature'][ids]]>tree['threshold'][ids]
        nodes[active]=np.where(right,tree['right'][ids],tree['left'][ids])
    assert (tree['left'][nodes]<0).all()
    return tree['label'][nodes]
def main_check():
    policy=main.Agent();source=B.parent/'v126_majkel_neural_bc/data/validation'
    z={p.stem:np.load(p,mmap_mode='r') for p in source.glob('*.npy')}
    c=F.common(z['global'],z['board'],z['units'],z['step']);report=json.loads((D/'training_report.json').read_text());expected={r['head']:r for r in report['heads']}
    unit_codes=np.zeros((len(c),16),np.int32);metrics=[]
    for i in range(16):
        x=F.local(c,z['units'],i);pred=batch(policy.trees[f'unit_{i}'],x);unit_codes[:,i]=pred
        mask=z['unit_mask'][:,i]>0;target=z['unit_tokens'][:,i]*102+z['unit_quantities'][:,i]
        if mask.any():
            accuracy=float((pred[mask]==target[mask]).mean());assert abs(accuracy-expected[f'unit_{i}']['validation_accuracy'])<1e-12
        for row in [0,111,2000]:assert policy.predict(f'unit_{i}',x[row])==int(pred[row])
    teacher_units=z['unit_tokens'].astype(np.int32)*102+z['unit_quantities'];prefix=np.zeros((len(c),20),np.float32)
    target_tokens=z['market_tokens'];target_qty=z['market_quantities']
    joint=np.ones(len(c),bool)
    for i in range(10):
        tf=np.zeros_like(prefix)
        if i:tf[:,:i*2]=np.stack([target_tokens[:,:i],target_qty[:,:i]],axis=-1).reshape(len(c),-1)
        x=F.market(c,teacher_units,tf);teacher_pred=batch(policy.trees[f'market_{i}'],x)
        target=target_tokens[:,i].astype(np.int32)*102+target_qty[:,i]
        assert abs(float((teacher_pred==target).mean())-expected[f'market_{i}']['validation_accuracy'])<1e-12
        free=batch(policy.trees[f'market_{i}'],F.market(c,unit_codes,prefix));tok,qty=free//102,free%102
        prefix[:,i*2]=tok;prefix[:,i*2+1]=qty
        active=target_tokens[:,i]>0
        joint&=(free==target)
        metrics.append({'slot':i,'free_prefix_accuracy':float((free==target).mean()),
                        'active_teacher_orders':int(active.sum()),
                        'free_prefix_active_order_accuracy':float((free[active]==target[active]).mean()) if active.any() else None})
    result={'exported_vs_training_validation_scores':'exact_match','scalar_vs_vector_export':'exact_match',
            'frames':len(c),'free_prefix_all_market_slots_exact':float(joint.mean()),'market_slots':metrics}
    (B/'audit_ddj_export.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main_check()
