"""严格折内特征、固定两epoch的RealMLP配对诊断。"""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='4'
import argparse,fcntl,gc,hashlib,json,sys,time,subprocess,traceback
from pathlib import Path
import numpy as np,pandas as pd,torch,psutil
from sklearn.preprocessing import TargetEncoder
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
import public_components as M
P=Path(__file__).resolve().parent;R=P.parents[2];C=json.loads((P/'preregistration.json').read_text());torch.set_num_threads(C['threads'])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False));t.replace(p)
def params():
 return dict(M.CONFIG,device=C['device'],epochs=C['epochs'],train_bs=C['train_bs'],eval_bs=C['eval_bs'])
def make(n,catdims,arm):
 m=M.RealMLP(1,catdims,n,params());m.num_embed.periodic=bool(arm);return m
@torch.inference_mode()
def predict(m,xn,xc):
 m.eval();out=[]
 for s in range(0,len(xn),C['eval_bs']):out.append(m(xn[s:s+C['eval_bs']],xc[s:s+C['eval_bs']]).sigmoid().mean(1).squeeze(-1).cpu().numpy())
 return np.concatenate(out)
def smoke():
 rows=[]
 for arm in [0,1]:
  M.seed_everything(42);m=make(12,[3,30,100],arm).to(C['device']);x=torch.randn(256,12,device=C['device']);xc=torch.zeros((256,3),dtype=torch.long,device=C['device']);y=torch.arange(256,device=C['device'])%2
  opt=torch.optim.AdamW(M.get_parameter_groups(m,params()),betas=(.9,.99));t=time.monotonic()
  for _ in range(10):
   opt.zero_grad();z=m(x,xc);loss=M.binary_bce_loss(y.repeat_interleave(C['n_ens']),z.reshape(-1));loss.backward();assert all(torch.isfinite(a.grad).all() for a in m.parameters() if a.grad is not None);opt.step()
  p=predict(m,x,xc);torch.save(m.state_dict(),P/f'smoke_{arm}.pt');n=make(12,[3,30,100],arm).to(C['device']);n.load_state_dict(torch.load(P/f'smoke_{arm}.pt',weights_only=True));err=float(abs(p-predict(n,x,xc)).max());assert err<1e-6;rows.append({'arm':arm,'seconds_10_steps':time.monotonic()-t,'reload_error':err})
 write(P/'smoke.json',{'status':'PASS','synthetic_only':True,'arms':rows,'runner_sha':sha(__file__),'components_sha':sha(P/'public_components.py')});print(rows,flush=True)
def features(fold,fit,valid,raw,y):
 d=P/f'fold_{fold}';d.mkdir(exist_ok=True)
 if (d/'input.json').exists():
  meta=json.loads((d/'input.json').read_text())
  for name,h in meta['hashes'].items():assert sha(d/name)==h
  return
 M.TARGET='Will_Buy_EV';M.cat_cols=raw.drop(columns=['id','Will_Buy_EV']).select_dtypes(include='object').columns.tolist();M.num_cols=[x for x in raw if x not in M.cat_cols+['id','Will_Buy_EV']];M.category_map={};M.important_combos=[('Annual_Income_USD','Range_Anxiety_Level'),('Age','Range_Anxiety_Level')]
 origpaths=list((R/'data').rglob('*Range*csv'));assert len(origpaths)==1,origpaths
 M.orig=pd.read_csv(origpaths[0]);M.orig['Will_Buy_EV']=M.orig['Will_Buy_EV'].map({'No':0,'Yes':1})
 xf,newcats,_,combos=M.feature_engineering(raw.iloc[fit].drop(columns=['id','Will_Buy_EV']).copy(),fit=True)
 xv,_,_,_=M.feature_engineering(raw.iloc[valid].drop(columns=['id','Will_Buy_EV']).copy(),fit=False)
 cats=list(dict.fromkeys(M.cat_cols+newcats))
 enc=TargetEncoder(cv=5,smooth='auto',shuffle=True,random_state=42,target_type='binary');a=enc.fit_transform(xf[combos],y[fit]);b=enc.transform(xv[combos])
 for j,c in enumerate(combos):xf[c+'_TE']=a[:,j];xv[c+'_TE']=b[:,j]
 nums=[x for x in xf if x not in cats];pre=M.NumericalPreprocessor(params()['tfms']);fn=pre.fit_transform(xf[nums].to_numpy('float32'));vn=pre.transform(xv[nums].to_numpy('float32'))
 fc=np.empty((len(xf),len(cats)),np.int64);vc=np.empty((len(xv),len(cats)),np.int64);dims=[]
 for j,c in enumerate(cats):
  keys=xf[c].astype(object);unique=pd.unique(keys);mapping={k:i+1 for i,k in enumerate(unique)};fc[:,j]=keys.map(mapping).to_numpy();vc[:,j]=xv[c].astype(object).map(mapping).fillna(0).to_numpy();dims.append(len(unique)+1)
 arrays={'fit_num.npy':fn,'valid_num.npy':vn,'fit_cat.npy':fc,'valid_cat.npy':vc,'fit_y.npy':y[fit],'valid_y.npy':y[valid],'valid_rows.npy':valid,'fit_rows.npy':fit,'valid_ids.npy':raw.id.to_numpy()[valid]}
 assert np.isfinite(fn).all() and np.isfinite(vn).all();assert len(np.intersect1d(fit,valid))==0
 for name,a in arrays.items():np.save(d/name,a)
 write(d/'input.json',{'fold':fold,'num_cols':nums,'cat_cols':cats,'cat_dims':dims,'fit_only_preprocessing':True,'original_sha':sha(origpaths[0]),'hashes':{name:sha(d/name) for name in arrays}})
 print('FEATURES',fold,fn.shape,fc.shape,flush=True)
def worker(fold,arm):
 d=P/f'fold_{fold}';out=d/f'arm_{arm}';out.mkdir(exist_ok=True);meta=json.loads((d/'input.json').read_text())
 if (out/'result.json').exists():return
 for name,h in meta['hashes'].items():assert sha(d/name)==h
 contract=json.loads((P/'contract.json').read_text());assert contract['runner']==sha(__file__) and contract['components']==sha(P/'public_components.py')
 parent=os.getppid();deadline=float(os.environ['DIAG_DEADLINE']);start=time.monotonic();peak=0
 def guard():
  nonlocal peak
  peak=max(peak,psutil.Process().memory_info().rss+torch.mps.driver_allocated_memory());assert peak<C['memory_gib']*1024**3,'memory';assert time.time()<deadline,'deadline';assert os.getppid()==parent,'parent exited'
 dev=C['device'];M.seed_everything(C['model_seed']);cfg=params();xn=torch.from_numpy(np.load(d/'fit_num.npy')).to(dev);xc=torch.from_numpy(np.load(d/'fit_cat.npy')).to(dev);yn=torch.from_numpy(np.load(d/'fit_y.npy').astype('float32')).to(dev)
 vn=torch.from_numpy(np.load(d/'valid_num.npy')).to(dev);vc=torch.from_numpy(np.load(d/'valid_cat.npy')).to(dev)
 model=make(xn.shape[1],meta['cat_dims'],arm).to(dev);groups=M.get_parameter_groups(model,cfg)
 for g in groups:g['lr_base']=g['lr']
 opt=torch.optim.AdamW(groups,betas=(cfg['mom'],cfg['sq_mom']));ema={k:v.detach().clone() for k,v in model.state_dict().items()};order=np.arange(len(xn));history=[]
 for epoch in range(C['epochs']):
  model.train()
  for s in range(0,len(xn),C['train_bs']):
   progress=(epoch*len(xn)+s)/(C['epochs']*len(xn));idx=order[s:s+C['train_bs']]
   for g in opt.param_groups:g['lr']=M.apply_schedule(g['lr_base'],progress,cfg['lr_sched'],cfg['flat_ratio'])
   for dm in model._dropout_modules:dm.p=M.apply_schedule(cfg['dropout'],progress,cfg['p_drop_sched'],cfg['flat_ratio'])
   opt.zero_grad(set_to_none=True);z=model(xn[idx],xc[idx]);ls=M.apply_schedule(cfg['ls_eps'],progress,cfg['ls_eps_sched'],cfg['flat_ratio']);loss=M.binary_bce_loss(yn[idx].repeat_interleave(C['n_ens']),z.reshape(-1),ls=ls);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['grad_clip']);opt.step()
   with torch.no_grad():
    for k,v in model.state_dict().items():
     if torch.is_floating_point(v):ema[k].mul_(cfg['ema_decay']).add_(v.detach(),alpha=1-cfg['ema_decay'])
     else:ema[k].copy_(v)
   if s%(C['train_bs']*100)==0:
    guard();write(out/'progress.json',{'epoch':epoch+1,'rows':s,'seconds':time.monotonic()-start});print('STEP',fold,arm,epoch+1,s,round(time.monotonic()-start,1),flush=True)
  np.random.shuffle(order);history.append({'epoch':epoch+1,'seconds':time.monotonic()-start})
 model.load_state_dict(ema);guard();p=predict(model,vn,vc);assert np.isfinite(p).all();torch.save({k:v.cpu().clone() for k,v in model.state_dict().items()},out/'model.pt');np.save(out/'prediction.npy',p)
 # 只在固定训练终点评分；不读取中间epoch验证成绩。
 auc=float(roc_auc_score(np.load(d/'valid_y.npy'),p));del model,opt,ema;gc.collect();torch.mps.empty_cache();reload=make(xn.shape[1],meta['cat_dims'],arm).to(dev);reload.load_state_dict(torch.load(out/'model.pt',map_location='cpu',weights_only=True));err=float(abs(predict(reload,vn,vc)-p).max());assert err<=1e-6;guard()
 write(out/'result.json',{'auc':auc,'arm':arm,'fold':fold,'history':history,'seconds':time.monotonic()-start,'peak_memory_bytes':peak,'reload_max_abs':err,'prediction_sha':sha(out/'prediction.npy'),'model_sha':sha(out/'model.pt'),'input_sha':sha(d/'input.json')});print('ARM_COMPLETE',fold,arm,auc,flush=True)
def run():
 lock=(P/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not (P/'result.json').exists(),'already complete'
 sm=json.loads((P/'smoke.json').read_text());assert sm['runner_sha']==sha(__file__) and sm['components_sha']==sha(P/'public_components.py')
 assert sha(R/C['source_notebook'])==C['source_sha256']
 contract={'runner':sha(__file__),'components':sha(P/'public_components.py'),'preregistration':sha(P/'preregistration.json'),'train':sha(R/'data/train.csv'),'torch':torch.__version__}
 if (P/'contract.json').exists():assert contract==json.loads((P/'contract.json').read_text())
 else:write(P/'contract.json',contract)
 if (P/'RUN_STARTED.json').exists():start=json.loads((P/'RUN_STARTED.json').read_text())['start']
 else:start=time.time();write(P/'RUN_STARTED.json',{'pid':os.getpid(),'start':start})
 deadline=start+C['wall_seconds'];raw=pd.read_csv(R/'data/train.csv');y=raw.Will_Buy_EV.eq('Yes').to_numpy('int8');oof=np.full((len(y),2),np.nan);folds=np.zeros(len(y),int)
 for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(raw,y),1):
  assert time.time()<deadline;features(fold,fit,valid,raw,y);gc.collect()
  for arm in [0,1]:
   proc=subprocess.Popen([sys.executable,__file__,'--fold',str(fold),'--arm',str(arm)],env=dict(os.environ,DIAG_DEADLINE=str(deadline)))
   try:proc.wait(timeout=max(1,deadline-time.time()));assert proc.returncode==0,f'worker exit {proc.returncode}'
   except BaseException:proc.terminate();proc.wait(timeout=10);raise
   d=P/f'fold_{fold}'/f'arm_{arm}';r=json.loads((d/'result.json').read_text());assert sha(d/'prediction.npy')==r['prediction_sha'];oof[valid,arm]=np.load(d/'prediction.npy')
  folds[valid]=fold;np.savez_compressed(P/'checkpoint_oof.npz',ids=raw.id.to_numpy(),pred=oof,fold=folds);write(P/'progress.json',{'completed_folds':fold,'seconds':time.time()-start})
 sys.path.insert(0,str(R/'model/research_runtime'));from paired_auc import paired_auc
 report=paired_auc(y,oof[:,0],oof[:,1],folds);report.update({'status':'COMPLETE_DIAGNOSTIC','seconds':time.time()-start,'gate_passed':report['delta']>=.0001 and report['positive_folds']==5 and report['candidate_auc']>=.9452,'counts_toward_cycle':False,'submission_allowed':False,'test_generated':False})
 np.savez_compressed(P/'diagnostic_oof.npz',ids=raw.id.to_numpy(),pred=oof,fold=folds);write(P/'result.json',report);print('RESULT',json.dumps(report),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');ap.add_argument('--fold',type=int);ap.add_argument('--arm',type=int);a=ap.parse_args()
 try:
  if a.smoke:smoke()
  elif a.fold:worker(a.fold,a.arm)
  else:run()
 except BaseException:
  write(P/f'failure_{a.fold}_{a.arm}.json',{'time':time.time(),'traceback':traceback.format_exc()});raise
