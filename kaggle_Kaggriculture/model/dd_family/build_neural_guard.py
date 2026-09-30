"""ddbw: one execution ablation on frozen ddbv weights, not another independent model."""
from pathlib import Path
import hashlib,json,shutil
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source=B/'ddbv';dest=B/'ddbw';dest.mkdir(exist_ok=False)
    prior=json.loads((source/'runs/development01/plan.json').read_text());assert all(sha(source/p)==h for p,h in prior['hashes'].items())
    for p in source.iterdir():
        if p.is_file() and p.suffix in ['.py','.npz','.json']:shutil.copy2(p,dest/p.name)
    shutil.copy2(B/'ddam/rules.py',dest/'rules.py')
    p=dest/'main.py';s=p.read_text().replace('import contract,action_space as space','import contract,action_space as space,rules')
    s=s.replace("self.stats={'calls':0,'unit_requests':0,'market_requests':0};self.last={}","self.stats={'calls':0,'unit_requests':0,'market_requests':0,'constrained_units':0};self.last={}\n        self.unit_token_ids=np.asarray([space.unit_token(a[1])[0] if a and a[0]=='unit' else 0 for a in self.atoms])")
    s=s.replace('assert count<=16','assert count<=16\n        shadow=copy.deepcopy(obs);seat=space.seat(obs);t=int(obs[\'step\'])')
    old='code=self.pass_id if count<=slot<16 else int(np.argmax(logits));previous=code;chosen.append(code)'
    new='''unconstrained=int(np.argmax(logits))
            if slot<count:
                token_mask=np.asarray(space.unit_legal_mask(shadow,slot));allowed=token_mask[self.unit_token_ids]&self.w['domain_mask'][slot]
                for j,a in enumerate(self.atoms):
                    if allowed[j] and a[1][0] in ['PICKUP','PLACE'] and len(a[1])>2 and int(a[1][2])<=0:allowed[j]=False
                scores=np.where(allowed,logits,-1e9);code=int(scores.argmax());assert allowed[code]
                self.stats['constrained_units']+=code!=unconstrained
            else:code=self.pass_id if slot<16 else unconstrained
            previous=code;chosen.append(code)'''
    assert old in s;s=s.replace(old,new)
    s=s.replace('if slot<count:orders.append(copy.deepcopy(order))',"if slot<count:\n                    orders.append(copy.deepcopy(order));rules._apply_unit_action(shadow['farms'][seat],shadow['private'],slot,order,10,t//24,24,100)")
    s=s.replace('neural_local_autoregressive_joint_behavior_cloning','neural_local_resource_constrained_joint_decoding');p.write_text(s)
    config=json.loads((dest/'config.json').read_text());config.update(version='ddbw',parent='ddbv',method='Frozen neural joint policy with resource-constrained unit decoding',weights_retrained=False,decoding='Highest model-probability unit request among currently legal token types with sequential shared-resource shadow; chosen request is fed to the next decoder slot. Original raw market requests retained.',independence='Same ddbv weights. This ablation is not a separate independently qualified model.');(dest/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    (dest/'parent_provenance.json').write_text(json.dumps({'parent':'ddbv','parent_hashes':prior['hashes'],'weights_equal':sha(dest/'weights.npz')==sha(source/'weights.npz'),'rule_primitives_sha256':sha(dest/'rules.py'),'builder_sha256':sha(Path(__file__))},indent=2)+'\n')
    reg=json.loads((B/'registry.json').read_text());assert reg['next_version']=='ddbw';reg['versions'].append({'version':'ddbw','index':74,'parent':'ddbv','status':'BUILT_PENDING_CHECK','method':config['method'],'hypothesis':'Sequential resource-feasible decoding avoids teacher-distribution drift causing mass atomic planting cancellations.','independence':config['independence']});reg['next_version']=None;(B/'registry.json').write_text(json.dumps(reg,indent=2)+'\n');print('built ddbw; frozen weights',sha(dest/'weights.npz'))
if __name__=='__main__':main()
