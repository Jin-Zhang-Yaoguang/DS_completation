"""One-shot official-CLI submitter, enabled only after formal and E2E gates."""
from __future__ import annotations
import csv,datetime,fcntl,hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[2];TOP=Path(__file__).resolve().parent
FORMAL=TOP/'p1_source_group_constraints_40f';E2E=TOP/'p1_e2e_outer5';CLI='/Users/a1-6/.local/bin/kaggle';COMP='playground-series-s6e9'
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
 f=json.loads((FORMAL/'cv_results.json').read_text());fv=json.loads((FORMAL/'verification.json').read_text());e=json.loads((E2E/'e2e_results.json').read_text());ev=json.loads((E2E/'verification.json').read_text())
 if f['status']!='COMPLETE' or fv['status']!='PASS' or sha(FORMAL/'cv_results.json')!=fv['result_sha256']:raise ValueError('formal verification missing')
 if e['status']!='COMPLETE_E2E_CONFIRMATION_R02' or e['baseline_role']!='FAITHFUL_ONLINE_V100_ALGORITHM' or e['old_new_cpu_A_score_used'] or not e['gate_passed'] or e['positive_folds']!=5 or sha(E2E/'verification.json')!=e['verification_sha256'] or ev['status']!='PASS_UNSCORED_R02' or ev['checked_cpu_models']!=600 or ev['checked_ct_prediction_caches']!=5 or ev['archived_new_cpu_A_used'] or ev['old_AB_branch_qualification_inherited']:raise ValueError('faithful online V100 R02 E2E gate missing')
 route=e['candidate'];key=route.lower()
 if route not in ('C','M') or not f['gates'][key] or f[f'{key}_oof_auc']<=f['v100_oof_auc']:raise ValueError('full-data gate missing')
 fpath=FORMAL/f'{key}_test.npy';pred=np.load(fpath)
 sample=pd.read_csv(ROOT/'data/sample_submission.csv');test=pd.read_csv(ROOT/'data/test.csv',usecols=['id'])
 if sample.columns.tolist()!=['id','Will_Buy_EV'] or len(pred)!=286571 or len(sample)!=len(pred) or not sample.id.equals(test.id) or sample.id.isna().any() or not sample.id.is_unique or not np.isfinite(pred).all() or ((pred<0)|(pred>1)).any():raise ValueError('submission row/column/probability contract failed')
 formal_hash=f['artifact_sha256'][f'{key}_test.npy']
 if sha(fpath)!=formal_hash:raise ValueError('frozen test predictions changed')
 return f,e,sample,pred,route

def leaderboard_after(ref,old_score):
 after_dir=TOP/'leaderboard_after_p1';after_dir.mkdir(exist_ok=True)
 archive=after_dir/f'{COMP}.zip'
 if archive.exists():raise ValueError('after-submission leaderboard snapshot already exists')
 cli(['competitions','leaderboard','-c',COMP,'--download','--path',str(after_dir),'--quiet'],timeout=180)
 downloaded=archive
 if not downloaded.exists():raise ValueError('leaderboard download missing')
 with zipfile.ZipFile(archive) as z:rows=list(csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode('utf-8-sig'))))
 team=[x for x in rows if x['TeamId']=='16810341']
 if len(team)!=1:raise ValueError('known account team absent from leaderboard')
 actual=team[0];other=[float(x['Score']) for x in rows if x['TeamId']!='16810341'];greater=sum(x>old_score for x in other);equal=sum(x==old_score for x in other)
 return {'downloaded_at_utc':now(),'zip_sha256':sha(archive),'teams':len(rows),'team_id':actual['TeamId'],'team_name':actual['TeamName'],'actual_rank':int(actual['Rank']),'actual_score':float(actual['Score']),'old_score_counterfactual_rank_band_same_snapshot':[greater+1,greater+equal+1],'old_submission_ref':56023943,'new_submission_ref':ref,'tie_band_note':'Old score is no longer this team’s current displayed score; equal-score tie ordering is not identified from rounded leaderboard export.'}

def main():
 with (TOP/'submit_p1.lock').open('a+') as h:
  try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('submission check already running')
  if (TOP/'p1_submit_receipt.json').exists():raise RuntimeError('P1 submission already attempted; inspect receipt rather than upload again')
  f,e,sample,pred,route=eligibility();today=now()[:10];listing=cli(['competitions','list','-s',COMP,'--csv']);comp=list(csv.DictReader(io.StringIO(listing)))
  if len(comp)!=1 or comp[0]['ref'].rsplit('/',1)[-1]!=COMP or comp[0]['userHasEntered']!='True':raise ValueError('competition entry not confirmed')
  deadline=datetime.datetime.fromisoformat(comp[0]['deadline']).replace(tzinfo=datetime.timezone.utc)
  if datetime.datetime.now(datetime.timezone.utc)>=deadline:raise ValueError('competition deadline passed')
  prior=submissions();used=sum(x['date'].startswith(today) for x in prior)
  if used>=10:raise ValueError('daily 10-submission limit exhausted')
  complete=[x for x in prior if x['status']=='SubmissionStatus.COMPLETE' and x['publicScore']];best=max(complete,key=lambda x:float(x['publicScore']))
  baseline=float(best['publicScore']);out=TOP/'p1_submission.csv';tmp=out.with_suffix('.tmp.csv');frame=pd.DataFrame({'id':sample.id,'Will_Buy_EV':pred});frame.to_csv(tmp,index=False);tmp.replace(out)
  out_sha=sha(out)
  for old in (ROOT/'model').rglob('submission.csv'):
   if old.is_file() and sha(old)==out_sha:raise ValueError(f'duplicate prediction file: {old}')
  recipe='V85/grouped-V85 fixed blend' if route=='C' else 'V100/V85/grouped-V85 fixed blend'
  message=f'P1 R02 {recipe} {route}; formal OOF {f[route.lower()+"_oof_auc"]:.9f}; outer5 delta {e["delta"]:+.8f}'
  intent={'status':'SUBMITTING','created_at_utc':now(),'competition':COMP,'route':route,'candidate_csv':str(out),'candidate_sha256':out_sha,'prior_best_ref':best['ref'],'prior_best_public_score':baseline,'daily_used_before':used,'daily_limit':10,'formal_result_sha256':sha(FORMAL/'cv_results.json'),'e2e_result_sha256':sha(E2E/'e2e_results.json'),'message':message,'attempts':1}
  write(TOP/'p1_submit_receipt.json',intent)
  r=subprocess.run([CLI,'competitions','submit','-c',COMP,'-f',str(out),'-m',message],capture_output=True,text=True,timeout=300)
  intent.update({'submit_cli_exit_code':r.returncode,'submit_stdout':r.stdout[-4000:],'submit_stderr':r.stderr[-4000:],'submitted_at_utc':now()})
  write(TOP/'p1_submit_receipt.json',intent)
  # Unknown receipt: query the original record, never repeat the upload.
  ref=None
  for _ in range(30):
   rows=submissions();found=[x for x in rows if x['description']==message]
   if len(found)>1:raise ValueError('duplicate matching submission descriptions; manual audit required')
   if found:
    row=found[0];ref=row['ref'];intent.update({'submission_ref':ref,'submission_status':row['status'],'public_score':float(row['publicScore']) if row['publicScore'] else None,'checked_at_utc':now()});write(TOP/'p1_submit_receipt.json',intent)
    if row['status']=='SubmissionStatus.COMPLETE':break
    if row['status'] not in ('SubmissionStatus.PENDING','SubmissionStatus.RUNNING'):break
   time.sleep(30)
  if ref is None:raise RuntimeError('submission receipt not found; do not upload again')
  if intent['submission_status']=='SubmissionStatus.COMPLETE':
   intent['score_improved']=bool(intent['public_score']>baseline)
   intent['leaderboard_snapshot']=leaderboard_after(ref,baseline)
   write(TOP/'p1_submit_receipt.json',intent)
  status=json.loads((TOP/'status.json').read_text());status.update({'updated_at_utc':now(),'phase':'P1_SUBMISSION_COMPLETE' if intent.get('submission_status')=='SubmissionStatus.COMPLETE' else 'P1_SUBMISSION_UNCONFIRMED','submission':{'ref':ref,'status':intent.get('submission_status'),'public_score':intent.get('public_score'),'improved':intent.get('score_improved'),'receipt':str(TOP/'p1_submit_receipt.json')},'next_action':'Keep V100 if Public did not improve; otherwise record new best and rank. No LB weight tuning.'});write(TOP/'status.json',status)
  print(json.dumps({'ref':ref,'status':intent.get('submission_status'),'score':intent.get('public_score'),'improved':intent.get('score_improved')}))
if __name__=='__main__':main()
