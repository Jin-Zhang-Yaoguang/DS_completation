"""TabM双臂工作进程；仅数值嵌入不同，不在进程内训练GBDT。"""
import os,sys
os.environ['OMP_NUM_THREADS']='4'
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P/'deps'))
import argparse,hashlib,json,time,resource,gc
import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from tabm import TabM
from rtdl_num_embeddings import LinearReLUEmbeddings
C=json.loads((P/'preregistration.json').read_text());torch.set_num_threads(C['threads'])

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def make(n,arm):
 return TabM.make(n_num_features=n,cat_cardinalities=None,d_out=1,arch_type=C['arch_type'],k=C['k'],n_blocks=C['n_blocks'],d_block=C['d_block'],dropout=C['dropout'],activation='ReLU',start_scaling_init='normal',num_embeddings=LinearReLUEmbeddings(n,C['embedding_dim']) if arm else None)
@torch.inference_mode()
def predict(model,x,guard=lambda:None):
 model.eval();ans=[]
 for start in range(0,len(x),C['eval_batch_size']):
  ans.append(model(x[start:start+C['eval_batch_size']]).squeeze(-1).sigmoid().mean(1).cpu().numpy());guard()
 return np.concatenate(ans)
def smoke():
 assert torch.backends.mps.is_available();torch.manual_seed(7);x=torch.randn(128,148,device='mps');y=(x[:,0]>0).float();rows=[]
 for arm in [0,1]:
  m=make(148,arm).to('mps');m.train();opt=torch.optim.AdamW(m.parameters(),lr=C['learning_rate']);z=m(x).squeeze(-1);assert z.shape==(128,C['k'])
  loss=torch.nn.functional.binary_cross_entropy_with_logits(z,y[:,None].expand_as(z));loss.backward();assert all(torch.isfinite(p.grad).all() for p in m.parameters() if p.grad is not None);opt.step()
  m.eval()
  with torch.no_grad():direct=m(x).squeeze(-1).sigmoid().mean(1).cpu().numpy()
  np.testing.assert_allclose(predict(m,x),direct,atol=1e-6,rtol=0)
  tmp=P/f'smoke_arm{arm}.pt';torch.save(m.state_dict(),tmp);m2=make(148,arm).to('mps');m2.load_state_dict(torch.load(tmp,map_location='cpu',weights_only=True));np.testing.assert_allclose(predict(m2,x),direct,atol=1e-6,rtol=0)
  rows.append({'arm':arm,'parameters':sum(p.numel() for p in m.parameters()),'finite_gradients':True,'checkpoint_reload':True})
 write(P/'smoke.json',{'status':'PASS','synthetic_only':True,'arms':rows,'worker_sha256':sha(__file__),'torch':torch.__version__,'device':'mps'})
def run(fold,arm):
 start=time.monotonic();parent_pid=os.getppid();directory=P/f'fold_{fold}';out=directory/f'arm_{arm}';out.mkdir(exist_ok=True)
 contract=json.loads((P/'contract.json').read_text());assert contract['code']['worker.py']==sha(__file__)
 meta=json.loads((directory/'input.json').read_text());assert meta['contract_sha']==sha(P/'contract.json')
 for name,digest in meta['hashes'].items():assert sha(directory/name)==digest,name
 if (out/'result.json').exists():
  r=json.loads((out/'result.json').read_text());assert r['input_sha']==sha(directory/'input.json') and sha(out/'best.pt')==r['model_sha'] and sha(out/'prediction.npy')==r['prediction_sha'];return
 deadline=float(os.environ['TABM_DEADLINE']);cap=float(os.environ['TABM_MEMORY_BYTES']);peak_gpu=0
 def guard():
  nonlocal peak_gpu
  assert os.getppid()==parent_pid,'parent process exited'
  peak_gpu=max(peak_gpu,torch.mps.driver_allocated_memory());assert time.time()<deadline,'wall budget'
  assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss+torch.mps.driver_allocated_memory()<cap,'worker memory budget'
 torch.manual_seed(C['model_seed_base']+fold);np.random.seed(C['model_seed_base']+fold)
 xf=torch.from_numpy(np.load(directory/'fit.npy')).to('mps');xv=torch.from_numpy(np.load(directory/'valid.npy')).to('mps')
 yf=torch.from_numpy(np.load(directory/'fit_y.npy').astype('float32')).to('mps');yv=np.load(directory/'valid_y.npy')
 model=make(xf.shape[1],arm).to('mps');optimizer=torch.optim.AdamW(model.parameters(),lr=C['learning_rate'],weight_decay=C['weight_decay'],betas=tuple(C['adam_betas']),eps=C['adam_eps'],amsgrad=False)
 best=-np.inf;bad=0;best_epoch=0;history=[];best_pred=None
 for epoch in range(1,C['epochs']+1):
  guard();model.train();rng=np.random.default_rng(C['model_seed_base']+fold*1000+epoch);order=torch.from_numpy(rng.permutation(len(xf))).to('mps');total=0.
  for step in range(0,len(order),C['batch_size']):
   idx=order[step:step+C['batch_size']];optimizer.zero_grad(set_to_none=True);logits=model(xf[idx]).squeeze(-1)
   loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,yf[idx,None].expand_as(logits));loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),C['grad_clip_norm']);optimizer.step();total+=float(loss.detach().cpu())*len(idx)
   if step%(C['batch_size']*20)==0:guard()
  pred=predict(model,xv,guard);auc=float(roc_auc_score(yv,pred));improved=auc>best+C['min_delta']
  if improved:
   best=auc;best_epoch=epoch;bad=0;best_pred=pred.copy();tmp=out/'best.pt.tmp';torch.save({k:v.detach().cpu().clone() for k,v in model.state_dict().items()},tmp);tmp.replace(out/'best.pt')
  else:bad+=1
  row={'epoch':epoch,'loss':total/len(xf),'auc':auc,'best_auc':best,'seconds':time.monotonic()-start};history.append(row);write(out/'progress.json',{'history':history,'best_epoch':best_epoch});print('EPOCH',fold,arm,json.dumps(row),flush=True)
  if bad>=C['patience']:break
 assert best_pred is not None and np.isfinite(best_pred).all();np.save(out/'prediction.npy',best_pred)
 # 结束前由独立实例重载最佳checkpoint，验证保存的预测。
 del model,optimizer;gc.collect();torch.mps.empty_cache();model=make(xf.shape[1],arm).to('mps');model.load_state_dict(torch.load(out/'best.pt',map_location='cpu',weights_only=True));replay=predict(model,xv,guard);error=float(abs(replay-best_pred).max());assert error<=1e-6
 guard();write(out/'result.json',{'status':'COMPLETE_DIAGNOSTIC_ARM','fold':fold,'arm':arm,'auc':best,'best_epoch':best_epoch,'history':history,'elapsed_seconds':time.monotonic()-start,'parameters':sum(p.numel() for p in model.parameters()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'peak_mps_driver_bytes':peak_gpu,'reload_max_abs':error,'input_sha':sha(directory/'input.json'),'model_sha':sha(out/'best.pt'),'prediction_sha':sha(out/'prediction.npy'),'submission_allowed':False})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');ap.add_argument('--fold',type=int);ap.add_argument('--arm',type=int);a=ap.parse_args()
 if a.smoke:smoke()
 else:run(a.fold,a.arm)
