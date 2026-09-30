"""Train ddbu on demonstration requests; validation CE selects within a fixed budget."""
from pathlib import Path
import argparse,copy,hashlib,json,shutil,time
import numpy as np
import torch
from torch.nn import functional as F
from neural_joint_torch import JointPolicy
B=Path(__file__).resolve().parent;DATA=B/'neural_joint_data'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--epochs',type=int,default=20);ap.add_argument('--batch',type=int,default=256);a=ap.parse_args()
    torch.manual_seed(21092026);torch.set_num_threads(4);rng=np.random.default_rng(21092026)
    device='mps' if torch.backends.mps.is_available() else 'cpu';d=B/'ddbu';d.mkdir(exist_ok=False)
    vocab=json.loads((DATA/'vocabulary.json').read_text());domains=np.zeros((26,len(vocab)),bool)
    for j,v in enumerate(vocab[2:],2):domains[:16,j]=json.loads(v)[0]=='unit';domains[16:,j]=json.loads(v)[0]=='market'
    manifest=json.loads((DATA/'manifest.json').read_text());assert all(sha(DATA/n)==h for n,h in manifest['hashes'].items())
    tr=np.load(DATA/'train_x.npy',mmap_mode='r');sums=np.zeros(2531,np.float64);squares=np.zeros_like(sums)
    for start in range(0,len(tr),4096):
        v=tr[start:start+4096].astype(np.float64);sums+=v.sum(0);squares+=(v*v).sum(0)
    mean=(sums/len(tr)).astype(np.float32);scale=np.maximum(.1,np.sqrt(np.maximum(0,squares/len(tr)-(sums/len(tr))**2))).astype(np.float32)
    datasets={}
    for split in ['train','validation']:
        x=np.load(DATA/f'{split}_x.npy').astype(np.float32);x=np.clip((x-mean)/scale,-10,10)
        y=np.load(DATA/f'{split}_y.npy').astype(np.int64);mask=np.load(DATA/f'{split}_mask.npy')&(y!=1)
        datasets[split]=(torch.tensor(x,device=device),torch.tensor(y,device=device),torch.tensor(mask,device=device))
    model=JointPolicy(len(vocab),domains).to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=8e-4,weight_decay=1e-4)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=a.epochs,eta_min=8e-5)
    for name in ['contract.py','features.py','action_space.py']:shutil.copy2(B/'ddam'/name,d/name)
    shutil.copy2(B/'neural_joint_runtime.py',d/'main.py');shutil.copy2(DATA/'vocabulary.json',d/'vocabulary.json');shutil.copy2(DATA/'manifest.json',d/'training_manifest.json')
    config={'version':'ddbu','method':'Neural autoregressive joint behavior cloning','architecture':'2531->384 ReLU->192 tanh encoder; 192-hidden GRU over 26 slots, previous joint-request embedding64, slot embedding16, local unit16; shared 725-class raw request vocabulary','loss':'Masked cross entropy over active units and market requests through first STOP. Unknown validation requests excluded from CE and reported. No execution correction.','optimizer':'AdamW lr8e-4 wd1e-4 cosine to8e-5, gradient clip1','epochs_max':a.epochs,'batch':a.batch,'patience':5,'selection':'Lowest validation teacher-forced cross entropy, no competitive results used. Validation is research holdout, not untouched competition test.','seed':21092026,'device':device,'torch':torch.__version__,'parameters':sum(p.numel() for p in model.parameters()),'training_data_manifest_sha256':sha(DATA/'manifest.json'),'trainer_sha256':sha(Path(__file__)),'architecture_sha256':sha(B/'neural_joint_torch.py'),'runtime_sha256':sha(B/'neural_joint_runtime.py')}
    (d/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    registry=json.loads((B/'registry.json').read_text());assert registry['next_version']=='ddbu';registry['versions'].append({'version':'ddbu','index':72,'status':'TRAINING','method':config['method'],'hypothesis':'A shared neural encoder and within-turn autoregressive decoder may retain joint coordination better than separate trees or nearest replay selection.','independence':'New learned weights and full policy architecture; qualification still requires formal gates.'});registry['next_version']=None;(B/'registry.json').write_text(json.dumps(registry,indent=2)+'\n')
    history=[];best=float('inf');best_epoch=0;best_state=None;begin=time.perf_counter()
    for epoch in range(1,a.epochs+1):
        metrics={};tick=time.perf_counter()
        for split in ['train','validation']:
            model.train(split=='train');x,y,mask=datasets[split];indices=rng.permutation(len(x)) if split=='train' else np.arange(len(x));loss_sum=0.;correct=0.;count=0.;joint=0.;frames=0
            with torch.set_grad_enabled(split=='train'):
                for start in range(0,len(x),a.batch):
                    ids=torch.tensor(indices[start:start+a.batch],device=device);xx=x[ids];yy=y[ids];mm=mask[ids];prev=torch.cat([torch.zeros((len(ids),1),dtype=torch.long,device=device),yy[:,:-1]],1)
                    logits=model(xx,prev);losses=F.cross_entropy(logits.reshape(-1,len(vocab)),yy.reshape(-1),reduction='none').reshape_as(yy);loss=(losses*mm).sum()/mm.sum()
                    if split=='train':optimizer.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.);optimizer.step()
                    matched=(logits.argmax(-1)==yy);loss_sum+=float((losses*mm).sum().detach().cpu());correct+=int((matched&mm).sum().detach().cpu());count+=int(mm.sum().detach().cpu());joint+=int((matched|~mm).all(1).sum().detach().cpu());frames+=len(ids)
            metrics[split]={'cross_entropy':loss_sum/count,'active_request_accuracy':correct/count,'all_known_requests_teacher_forced_exact':joint/frames,'scored_requests':count,'frames':frames}
        scheduler.step();record={'epoch':epoch,'seconds':time.perf_counter()-tick,**metrics};history.append(record);print(json.dumps(record),flush=True)
        if metrics['validation']['cross_entropy']<best:
            best=metrics['validation']['cross_entropy'];best_epoch=epoch;best_state={k:v.detach().cpu().numpy().copy() for k,v in model.state_dict().items()}
            np.savez_compressed(d/'weights.npz',**best_state,mean=mean,scale=scale)
        (d/'training_progress.json').write_text(json.dumps({'history':history,'selected_epoch':best_epoch},indent=2)+'\n')
        if epoch-best_epoch>=5:break
    report={'history':history,'selected_epoch':best_epoch,'validation_unknown_active_requests':int(((np.load(DATA/'validation_y.npy')==1)&np.load(DATA/'validation_mask.npy')).sum()),'elapsed_seconds':time.perf_counter()-begin,'runtime':'NumPy only, weights from selected supervised checkpoint','competitive_result':None,'test_replays_opened':False,'weights_sha256':sha(d/'weights.npz')}
    (d/'training_report.json').write_text(json.dumps(report,indent=2)+'\n');registry=json.loads((B/'registry.json').read_text());next(v for v in registry['versions'] if v['version']=='ddbu')['status']='TRAINED_PENDING_PARITY';(B/'registry.json').write_text(json.dumps(registry,indent=2)+'\n');print('training complete',best_epoch,'seconds',report['elapsed_seconds'],flush=True)
if __name__=='__main__':main()
