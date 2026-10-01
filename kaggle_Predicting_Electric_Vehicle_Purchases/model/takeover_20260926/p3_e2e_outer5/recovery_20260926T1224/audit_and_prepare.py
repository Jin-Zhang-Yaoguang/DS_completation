"""One-time P3 lifecycle recovery audit; never mutates completed atoms or frozen code."""
from __future__ import annotations
import datetime,fcntl,hashlib,json,os,shutil,subprocess
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent
E2E=HERE.parent;TOP=E2E.parent;ROOT=E2E.parents[2]
CONTRACT='4d254f2215f566fc8cefb11575645b177dfa8f9f4c4c3e9345ab3cf2f4f52466'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def arrsha(a):return hashlib.sha256(np.asarray(a,dtype='<i8').tobytes()).hexdigest()
def run(args):
 p=subprocess.run(args,capture_output=True,text=True)
 return {'argv':args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def save(name,d):
 p=HERE/name
 if p.exists():raise RuntimeError(f'recovery evidence already exists: {p}')
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 sources={'status.json':TOP/'status.json','progress.json':E2E/'progress.json','budget.json':E2E/'budget.json','RUN_STARTED.json':E2E/'RUN_STARTED.json','preflight.json':E2E/'preflight.json','protocol_audit.json':E2E/'protocol_audit.json'}
 for name,p in sources.items():
  target=HERE/('before_'+name)
  if target.exists():raise RuntimeError(f'snapshot already exists: {target}')
  shutil.copy2(p,target)
 status=json.loads(sources['status.json'].read_text());progress=json.loads(sources['progress.json'].read_text());budget=json.loads(sources['budget.json'].read_text());started=json.loads(sources['RUN_STARTED.json'].read_text());pre=json.loads(sources['preflight.json'].read_text());protocol=json.loads(sources['protocol_audit.json'].read_text())
 if status['phase']!='P3_E2E_RUNNING' or progress['completed_atoms']!=10 or progress['contract_sha256']!=CONTRACT or started['contract_sha256']!=CONTRACT or pre['contract_sha256']!=CONTRACT:raise RuntimeError('stale recovery assumptions')
 locks={}
 for name in ('run.lock','supervisor.lock'):
  p=E2E/name
  with p.open('a+') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   locks[name]='UNHELD_ACQUIRED_AND_RELEASED'
   fcntl.flock(f,fcntl.LOCK_UN)
 ps=run(['ps','-axo','pid,ppid,pgid,lstart,state,command'])
 matching=[row for row in ps['stdout'].splitlines() if 'p3_e2e_outer5/continue.py' in row or 'p3_e2e_outer5/run.py' in row]
 # The audit command itself is not a trainer.
 matching=[row for row in matching if 'audit_and_prepare.py' not in row]
 if matching:raise RuntimeError(f'live P3 process found: {matching}')
 lsof=run(['lsof',str(E2E/'run.lock'),str(E2E/'supervisor.lock')])
 if lsof['stdout'].strip():raise RuntimeError('lock file still opened')
 for name,file in [('preregistration',E2E/'preregistration.json'),('runner',E2E/'run.py'),('verifier',E2E/'verify_score.py'),('submitter',E2E/'submit_if_qualified.py')]:
  if protocol[name+'_sha256']!=sha(file):raise RuntimeError(f'frozen {name} hash drift')
 if pre['contract']['runner_sha256']!=sha(E2E/'run.py') or pre['contract']['verifier_sha256']!=sha(E2E/'verify_score.py') or pre['contract']['submitter_sha256']!=sha(E2E/'submit_if_qualified.py'):raise RuntimeError('preflight code hash drift')
 frame=pd.read_csv(ROOT/'data/train.csv',usecols=['id','Will_Buy_EV']);ids=frame.id.to_numpy(np.int64);y=frame.Will_Buy_EV.eq('Yes').to_numpy(np.int8)
 with np.load(ROOT/'model/validation/e2e_v100_20260905/splits.npz',allow_pickle=False) as z:
  train=z['outer_01_train_idx'];hold=z['outer_01_valid_idx'];fold=z['outer_01_v80_fold']
 if not np.array_equal(np.unique(fold),np.arange(40)):raise RuntimeError('fold drift')
 atoms=[]
 for atom in range(1,11):
  part=E2E/f'outer_01/v80/atom_{atom:02d}';files={name:part/name for name in ('manifest.json','model.txt','predictions.npz')}
  if any(not p.is_file() for p in files.values()):raise RuntimeError(f'atom {atom} incomplete')
  m=json.loads(files['manifest.json'].read_text());h=train[fold==atom-1];fit=train[fold!=atom-1]
  checks={'fit_idx_sha256':arrsha(fit),'early_stop_hold_idx_sha256':arrsha(h),'outer_valid_idx_sha256':arrsha(hold),'fit_y_sha256':arrsha(y[fit]),'early_stop_hold_y_sha256':arrsha(y[h])}
  if m['status']!='COMPLETE_UNSCORED' or m['contract_sha256']!=CONTRACT or m['outer']!=1 or m['family']!='v80' or m['atom']!=atom or m['refit_performed'] or m['outer_hold_labels_used'] or m['training_fit_count']!=1 or any(m[k]!=v for k,v in checks.items()):raise RuntimeError(f'atom {atom} manifest scope/identity drift')
  hashes={name:sha(p) for name,p in files.items()}
  if hashes['model.txt']!=m['model_sha256'] or hashes['predictions.npz']!=m['prediction_sha256']:raise RuntimeError(f'atom {atom} file hash drift')
  with np.load(files['predictions.npz'],allow_pickle=False) as z:
   for k,expected in [('oof_idx',h),('valid_idx',hold),('oof_id',ids[h]),('valid_id',ids[hold])]:
    if not np.array_equal(z[k],expected):raise RuntimeError(f'atom {atom} prediction row drift {k}')
   for k,rows in [('oof_proba',len(h)),('valid_proba',len(hold))]:
    a=z[k]
    if a.shape!=(rows,) or not np.isfinite(a).all() or ((a<0)|(a>1)).any():raise RuntimeError(f'atom {atom} prediction invalid {k}')
  atoms.append({'atom':atom,'files_sha256':hashes,'contract_sha256':CONTRACT,'selected_iteration':m['selected_iteration'],'complete':True})
 next_dir=E2E/'outer_01/v80/atom_11'
 partial={'source':str(next_dir),'exists':next_dir.exists(),'files':[]}
 if next_dir.exists():
  partial['files']=[{'relative':str(x.relative_to(next_dir)),'sha256':sha(x),'bytes':x.stat().st_size} for x in next_dir.rglob('*') if x.is_file()]
  if (next_dir/'manifest.json').exists():raise RuntimeError('atom11 unexpectedly completed; stop for review')
  target=HERE/'interrupted_outer_01_v80_atom_11'
  if target.exists():raise RuntimeError('interrupted atom evidence target already exists')
  shutil.move(str(next_dir),str(target));partial['moved_to']=str(target)
 extra=120.0
 budget_after={**budget,'spent_seconds':float(budget['spent_seconds'])+extra,'pid':None,'updated_at_utc':now(),'recovery_adjustment_seconds':extra,'recovery_reason':'Conservative upper allowance for interrupted, uncheckpointed atom11 after atom10; downtime after process death excluded; old budget preserved in recovery snapshot.'}
 tmp=(E2E/'budget.json').with_name('.budget.json.recovery.tmp');tmp.write_text(json.dumps(budget_after,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,E2E/'budget.json')
 report={'status':'READY_TO_RESUME_SAME_CONTRACT','audited_at_utc':now(),'contract_sha256':CONTRACT,'process':{'old_pid':99918,'old_supervisor_pid':99916,'ps_matching_training':matching,'ps_old_pids':run(['ps','-p','99918,99916,97320','-o','pid,ppid,pgid,lstart,state,command']),'lsof':lsof,'locks':locks},'snapshots':{k:{'source':str(v),'snapshot':str(HERE/('before_'+k)),'sha256':sha(HERE/('before_'+k))} for k,v in sources.items()},'frozen_code_sha256':{name:sha(E2E/file) for name,file in [('run.py','run.py'),('verify_score.py','verify_score.py'),('submit_if_qualified.py','submit_if_qualified.py'),('preregistration.json','preregistration.json'),('protocol_audit.json','protocol_audit.json')]},'completed_atoms':atoms,'interrupted_atom':partial,'budget_before_seconds':budget['spent_seconds'],'budget_after_seconds':budget_after['spent_seconds'],'budget_adjustment_seconds':extra,'budget_adjustment_method':budget_after['recovery_reason'],'models_retrained':0,'outer_U_scores_computed':0}
 save('recovery_audit.json',report)
 print(json.dumps({'status':report['status'],'complete_atoms':len(atoms),'atom11_moved':partial.get('moved_to'),'budget_after_seconds':budget_after['spent_seconds'],'contract_sha256':CONTRACT},ensure_ascii=False))
if __name__=='__main__':main()
