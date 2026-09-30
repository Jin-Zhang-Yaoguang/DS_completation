"""Listwise production-option distillation; inherited executor and other heads fixed."""
from pathlib import Path
import hashlib,json,shutil,sys,time
import numpy as np
import torch
from torch import nn
from torch.nn import functional as TF
B=Path(__file__).resolve().parent;SRC=B/'task_policy_data/ddbo'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    torch.manual_seed(61071);torch.set_num_threads(4);rng=np.random.default_rng(61071);device='mps' if torch.backends.mps.is_available() else 'cpu'
    parent=B/'ddbo';d=B/'ddbz';d.mkdir(exist_ok=False);plan=json.loads((parent/'runs/development01/plan.json').read_text());assert all(sha(parent/p)==h for p,h in plan['hashes'].items())
    for p in parent.iterdir():
        if p.is_file() and p.suffix in ['.py','.json','.npz'] and p.name not in ['goal_rank.npz','training_report.json']:shutil.copy2(p,d/p.name)
    shutil.copy2(B/'neural_rank_runtime.py',d/'neural_rank_runtime.py')
    p=d/'main.py';s=p.read_text().replace('import action_space as A,rules,task_features as F,tree_runtime,','import action_space as A,rules,task_features as F,tree_runtime,neural_rank_runtime,').replace("self.rank=tree_runtime.Model(B/'goal_rank.npz')","self.rank=neural_rank_runtime.Model(B/'neural_goal_rank.npz')");assert 'self.rank=neural_rank_runtime.Model' in s;p.write_text(s)
    manifest=json.loads((SRC/'manifest.json').read_text());assert len(manifest['rows'])==186 and all(r['source_exact_719_states'] for r in manifest['rows'])
    config=json.loads((d/'config.json').read_text());config.update(version='ddbz',parent='ddbo',method='Listwise neural production-option ranking over verified teacher task labels',rank_iterations=None,rank_architecture='345 -> 128 ReLU -> 64 ReLU -> 1, shared candidate score',rank_loss='Weighted listwise softmax cross entropy among one positive and original sampled negatives per query',rank_training='AdamW lr8e-4 wd1e-4 cosine20 epochs to8e-5, batch1024 queries, gradient clip1, patience5, full-candidate validation CE selects checkpoint',rank_weights='Original inverse-sqrt action-frequency capped8 and day<3 times4, normalized by minibatch total',input_semantics='Current source observations plus teacher-forced previously selected commitments; runtime uses only its own commitments. Future successful tasks are labels, not future environment observations.',torch=torch.__version__,device=device,trainer_sha256=sha(Path(__file__)),source_manifest_sha256=sha(SRC/'manifest.json'))
    (d/'config.json').write_text(json.dumps(config,indent=2)+'\n');(d/'parent_provenance.json').write_text(json.dumps({'parent':'ddbo','parent_hashes':plan['hashes'],'unchanged_heads':['goal_quantity.npz','market_policy.npz','market_quantity.npz'],'execution_unchanged':True,'data_train_episodes':146,'data_validation_episodes':40,'test_opened':False},indent=2)+'\n')
    reg=json.loads((B/'registry.json').read_text());assert reg['next_version']=='ddbz';reg['versions'].append({'version':'ddbz','index':77,'parent':'ddbo','status':'TRAINING','method':config['method'],'hypothesis':'Listwise neural ranking of persistent task options may improve coherent behavior beyond low-level autoregressive cloning and pointwise boosted task ranking.'});reg['next_version']=None;(B/'registry.json').write_text(json.dumps(reg,indent=2)+'\n')
    pieces=[];starts=[];lengths=[];tokens=[];days=[];offset=0;validation=[];source_seeds={'train':[],'validation':[]};token_count=47
    for row in manifest['rows']:
        p=SRC/f"{row['split']}_{row['index']:03}.npz";assert sha(p)==row['sha256'];source_seeds[row['split']].append(row['source_seed'])
        with np.load(p) as z:
            if row['split']=='train':
                x=z['rank_x'];y=z['rank_y'];st=np.flatnonzero(y);assert st[0]==0 and np.all(y[st]==1);ln=np.diff(np.r_[st,len(y)]);assert ln.max()<=9 and ln.min()>=1
                pieces.append(x);starts.append(st+offset);lengths.append(ln);tokens.append(x[st,-(token_count+11):-11].argmax(1));days.append(x[st,0]);offset+=len(x)
            else:validation.append((z['validation_x'],z['validation_offsets'],z['validation_choice']))
    assert len(set(source_seeds['train']))==146 and len(set(source_seeds['validation']))==40 and not set(source_seeds['train'])&set(source_seeds['validation'])
    x=np.concatenate(pieces);del pieces;starts=np.concatenate(starts);lengths=np.concatenate(lengths);tokens=np.concatenate(tokens);days=np.concatenate(days);freq=np.bincount(tokens,minlength=token_count);weights=np.minimum(8,np.sqrt(freq.max()/np.maximum(1,freq[tokens])))*np.where(days<3,4,1)
    sums=np.zeros(345,np.float64);squares=np.zeros(345,np.float64)
    for lo in range(0,len(x),65536):v=x[lo:lo+65536].astype(np.float64);sums+=v.sum(0);squares+=(v*v).sum(0)
    mean=(sums/len(x)).astype(np.float32);scale=np.maximum(.1,np.sqrt(np.maximum(0,squares/len(x)-(sums/len(x))**2))).astype(np.float32);tm=torch.tensor(mean,device=device);ts=torch.tensor(scale,device=device)
    model=nn.Sequential(nn.Linear(345,128),nn.ReLU(),nn.Linear(128,64),nn.ReLU(),nn.Linear(64,1)).to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=8e-4,weight_decay=1e-4);scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,20,eta_min=8e-5)
    print(json.dumps({'rows':len(x),'queries':len(starts),'validation_full_queries':sum(len(v[2]) for v in validation),'device':device}),flush=True)
    def score(raw):
        chunks=[]
        for lo in range(0,len(raw),16384):chunks.append(model(torch.clamp((torch.tensor(raw[lo:lo+16384],device=device)-tm)/ts,-10,10)).detach().cpu().numpy()[:,0])
        return np.concatenate(chunks)
    history=[];best=float('inf');selected=0;begin=time.perf_counter()
    for epoch in range(1,21):
        tick=time.perf_counter();model.train();order=rng.permutation(len(starts));total=0.;correct=0
        for lo in range(0,len(order),1024):
            ids=order[lo:lo+1024];valid=np.arange(9)[None,:]<lengths[ids,None];ix=starts[ids,None]+np.minimum(np.arange(9)[None,:],lengths[ids,None]-1)
            features=torch.tensor(x[ix],device=device);scores=model(torch.clamp((features-tm)/ts,-10,10)).squeeze(-1).masked_fill(~torch.tensor(valid,device=device),-1e9);losses=TF.cross_entropy(scores,torch.zeros(len(ids),dtype=torch.long,device=device),reduction='none');w=torch.tensor(weights[ids],dtype=torch.float32,device=device);loss=(losses*w).sum()/w.sum();optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step();total+=float(loss.detach().cpu())*len(ids);correct+=int((scores.argmax(1)==0).sum().detach().cpu())
        model.eval();n=0;ce=0.;top1=0;top5=0
        with torch.no_grad():
            for raw,offsets,labels in validation:
                values=score(raw)
                for j,label in enumerate(labels):
                    v=values[offsets[j]:offsets[j+1]].astype(np.float64);z=v-v.max();ce+=float(np.log(np.exp(z).sum())-z[label]);top1+=int(v.argmax()==label);top5+=int(label in np.argsort(v)[-5:]);n+=1
        record={'epoch':epoch,'train_sampled_query_ce_weighted':total/len(starts),'train_sampled_query_top1':correct/len(starts),'validation_full_query_ce':ce/n,'validation_full_query_top1':top1/n,'validation_full_query_top5':top5/n,'validation_queries':n,'seconds':time.perf_counter()-tick};history.append(record);print(json.dumps(record),flush=True);scheduler.step()
        if ce/n<best:
            best=ce/n;selected=epoch;state={k:v.detach().cpu().numpy().copy() for k,v in model.state_dict().items()};np.savez_compressed(d/'neural_goal_rank.npz',**state,mean=mean,scale=scale)
        (d/'training_progress.json').write_text(json.dumps({'history':history,'selected_epoch':selected},indent=2)+'\n')
        if epoch-selected>=5:break
    from neural_rank_runtime import Model
    runtime=Model(d/'neural_goal_rank.npz');state={k:torch.tensor(runtime.a[k],device=device) for k in model.state_dict()};model.load_state_dict(state)
    with torch.no_grad():expected=score(validation[0][0][:2048])
    error=float(np.abs(expected-runtime.predict(validation[0][0][:2048])).max());assert error<3e-4,error
    report={'history':history,'selected_epoch':selected,'source_seeds':source_seeds,'training_queries':len(starts),'training_candidate_rows':len(x),'export_max_abs_error':error,'elapsed_seconds':time.perf_counter()-begin,'test_opened':False,'weights_sha256':sha(d/'neural_goal_rank.npz'),'validation_scope':'Previously used source validation task queries, every 32nd compiler query with all candidate options. Not competitive evaluation.'};(d/'training_report.json').write_text(json.dumps(report,indent=2)+'\n');reg=json.loads((B/'registry.json').read_text());next(v for v in reg['versions'] if v['version']=='ddbz')['status']='TRAINED';(B/'registry.json').write_text(json.dumps(reg,indent=2)+'\n');print('complete',selected,'parity',error,flush=True)
if __name__=='__main__':main()
