"""One-shot P3 CLI submission after faithful paired outer gate."""
from __future__ import annotations
import csv,datetime,fcntl,hashlib,io,json,os,subprocess,time
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent;TOP=HERE.parent;ROOT=HERE.parents[2];P3=TOP/'p3_internal_v85_family_replace_20260926'
CLI='/Users/a1-6/.local/bin/kaggle';COMP='playground-series-s6e9'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(path,d):
 tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)
def cli(args,timeout=120):
 r=subprocess.run([CLI,*args],capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError(f'Kaggle CLI failed {args}: {r.stderr[-2000:]}')
 return r.stdout
def submissions():return list(csv.DictReader(io.StringIO(cli(['competitions','submissions','-c',COMP,'--csv']))))
def eligibility():
 pre=json.loads((HERE/'preflight.json').read_text());audit=json.loads((HERE/'protocol_audit.json').read_text());d=json.loads((P3/'development_result.json').read_text());v=json.loads((P3/'independent_verification.json').read_text());e=json.loads((HERE/'e2e_results.json').read_text());ev=json.loads((HERE/'verification.json').read_text())
 for name,p in [('preregistration',HERE/'preregistration.json'),('runner',HERE/'run.py'),('verifier',HERE/'verify_score.py'),('submitter',Path(__file__))]:
  if audit[name+'_sha256']!=sha(p):raise ValueError(f'P3 frozen protocol drift: {name}')
 if pre['contract']['submitter_sha256']!=sha(Path(__file__)) or pre['contract']['protocol_audit_sha256']!=sha(HERE/'protocol_audit.json') or pre['contract']['verifier_sha256']!=sha(HERE/'verify_score.py') or pre['contract']['runner_sha256']!=sha(HERE/'run.py'):raise ValueError('P3 preflight code drift')
 if not d['gate_pass'] or d['positive_meta_blocks']!=5 or v['status']!='PASS' or sha(P3/'development_result.json')!=pre['contract']['development_result_sha256'] or sha(P3/'independent_verification.json')!=pre['contract']['development_verification_sha256']:raise ValueError('P3 development gate missing')
 if e['status']!='COMPLETE_E2E_CONFIRMATION_P3' or e['candidate']!='P3_INTERNAL_C' or e['baseline_role']!='FAITHFUL_ONLINE_V100_ALGORITHM' or e['old_new_cpu_A_score_used'] or not e['gate_passed'] or e['positive_folds']!=5 or not e['candidate_auc']>e['baseline_auc'] or sha(HERE/'verification.json')!=e['verification_sha256'] or ev['status']!='PASS_UNSCORED_P3' or ev['checked_cpu_models']!=600 or ev['checked_ct_prediction_caches']!=5 or ev['archived_new_cpu_A_used'] or ev['old_AB_branch_qualification_inherited']:raise ValueError('faithful P3 outer gate missing')
 fpath=P3/'p3_v100_test.npy';pred=np.load(fpath,allow_pickle=False)
 sample=pd.read_csv(ROOT/'data/sample_submission.csv');test=pd.read_csv(ROOT/'data/test.csv',usecols=['id'])
 if sample.columns.tolist()!=['id','Will_Buy_EV'] or len(pred)!=286571 or len(sample)!=len(pred) or not sample.id.equals(test.id) or sample.id.isna().any() or not sample.id.is_unique or not np.isfinite(pred).all() or ((pred<0)|(pred>1)).any():raise ValueError('P3 submission row/column/probability contract failed')
 if sha(fpath)!=v['candidate_test_sha256']:raise ValueError('P3 full-data test prediction changed')
 return d,e,sample,pred

def main():
 with (HERE/'submit.lock').open('a+') as h:
  fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  receipt=HERE/'submit_receipt.json'
  if receipt.exists():raise RuntimeError('P3 submission already attempted; inspect receipt rather than upload again')
  d,e,sample,pred=eligibility();listing=cli(['competitions','list','-s',COMP,'--csv']);comp=list(csv.DictReader(io.StringIO(listing)))
  if len(comp)!=1 or comp[0]['ref'].rsplit('/',1)[-1]!=COMP or comp[0]['userHasEntered']!='True':raise ValueError('competition entry not confirmed')
  deadline=datetime.datetime.fromisoformat(comp[0]['deadline']).replace(tzinfo=datetime.timezone.utc)
  if datetime.datetime.now(datetime.timezone.utc)>=deadline:raise ValueError('competition deadline passed')
  prior=submissions();today=now()[:10];used=sum(x['date'].startswith(today) for x in prior)
  if used>=10:raise ValueError('daily 10-submission limit exhausted')
  complete=[x for x in prior if x['status']=='SubmissionStatus.COMPLETE' and x['publicScore']]
  if not complete:raise ValueError('no confirmed online baseline')
  best=max(complete,key=lambda x:float(x['publicScore']))
  if float(best['publicScore'])<.94635:raise ValueError('unexpected weaker online baseline')
  out=TOP/'p3_submission.csv';tmp=out.with_suffix('.tmp.csv');pd.DataFrame({'id':sample.id,'Will_Buy_EV':pred}).to_csv(tmp,index=False);tmp.replace(out);out_sha=sha(out)
  for old in (ROOT/'model').rglob('submission.csv'):
   if old.is_file() and sha(old)==out_sha:raise ValueError(f'duplicate prediction file: {old}')
  message=f'P3 internal V85 family C in V90/V100; OOF {d["candidate_auc"]:.9f}; outer5 delta {e["delta"]:+.8f}'
  intent={'status':'SUBMITTING','created_at_utc':now(),'competition':COMP,'candidate_csv':str(out),'candidate_sha256':out_sha,'prior_best_ref':best['ref'],'prior_best_public_score':float(best['publicScore']),'daily_used_before':used,'daily_limit':10,'development_result_sha256':sha(P3/'development_result.json'),'e2e_result_sha256':sha(HERE/'e2e_results.json'),'message':message,'attempts':1}
  write(receipt,intent)
  r=subprocess.run([CLI,'competitions','submit','-c',COMP,'-f',str(out),'-m',message],capture_output=True,text=True,timeout=300)
  intent.update({'submit_cli_exit_code':r.returncode,'submit_stdout':r.stdout[-4000:],'submit_stderr':r.stderr[-4000:],'submitted_at_utc':now()});write(receipt,intent)
  ref=None
  for _ in range(30):
   rows=submissions();found=[x for x in rows if x['description']==message]
   if len(found)>1:raise ValueError('duplicate matching submission descriptions; inspect manually')
   if found:
    row=found[0];ref=row['ref'];intent.update({'submission_ref':ref,'submission_status':row['status'],'public_score':float(row['publicScore']) if row['publicScore'] else None,'checked_at_utc':now()});write(receipt,intent)
    if row['status']=='SubmissionStatus.COMPLETE':break
    if row['status'] not in ('SubmissionStatus.PENDING','SubmissionStatus.RUNNING'):break
   time.sleep(30)
  if ref is None:raise RuntimeError('submission receipt not found; do not upload again')
  if intent['submission_status']=='SubmissionStatus.COMPLETE':
   intent['score_improved']=bool(intent['public_score']>float(best['publicScore']));write(receipt,intent)
  status=json.loads((TOP/'status.json').read_text());status.update({'updated_at_utc':now(),'phase':'P3_SUBMISSION_COMPLETE' if intent.get('submission_status')=='SubmissionStatus.COMPLETE' else 'P3_SUBMISSION_UNCONFIRMED','process':{'pid':None,'active':False},'submission':{'ref':ref,'status':intent.get('submission_status'),'public_score':intent.get('public_score'),'improved':intent.get('score_improved'),'receipt':str(receipt)},'goal_achieved':bool(intent.get('score_improved')),'next_action':'Retain frozen candidate and online evidence; no LB weight tuning.'});write(TOP/'status.json',status)
  print(json.dumps({'ref':ref,'status':intent.get('submission_status'),'score':intent.get('public_score'),'improved':intent.get('score_improved')}))
if __name__=='__main__':main()
