"""Serial P3 outer training, independent verification, and conditional one-shot CLI submission."""
from __future__ import annotations
import datetime,fcntl,json,os,subprocess,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;TOP=HERE.parent

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def update(phase,next_action,**other):
 p=TOP/'status.json';d=json.loads(p.read_text());d.update({'updated_at_utc':now(),'phase':phase,'current_experiment':'p3_e2e_outer5','next_action':next_action});d.update(other);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,p)
def call(name):
 print(f'{now()} START {name}',flush=True)
 r=subprocess.run([sys.executable,str(HERE/name)],cwd=HERE)
 print(f'{now()} END {name} rc={r.returncode}',flush=True)
 if r.returncode:raise RuntimeError(f'{name} failed rc={r.returncode}')
def main():
 with (HERE/'supervisor.lock').open('a+') as h:
  fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  call('run.py')
  update('P3_E2E_INDEPENDENT_VERIFICATION','Independently audit all models/caches/meta before first outer U score',process={'pid':os.getpid(),'active':True})
  call('verify_score.py')
  e=json.loads((HERE/'e2e_results.json').read_text())
  if not e['gate_passed']:
   update('P3_E2E_VERIFIED_NO_GO','P3 fixed candidate closed; no submission; read-only V100 misrank audit',process={'pid':None,'active':False},p3_e2e={'gate_passed':False,'result':'model/takeover_20260926/p3_e2e_outer5/e2e_results.json'})
   return
  update('P3_E2E_VERIFIED_GO','One-shot official CLI submission of frozen P3 candidate',process={'pid':os.getpid(),'active':True},p3_e2e={'gate_passed':True,'result':'model/takeover_20260926/p3_e2e_outer5/e2e_results.json'})
  call('submit_if_qualified.py')
if __name__=='__main__':
 try:main()
 except BaseException:
  detail=traceback.format_exc();print(detail,flush=True)
  update('P3_PIPELINE_FAILED','Inspect supervisor.log, preserve checkpoints and one-shot receipt',process={'pid':None,'active':False},blocker=detail[-3000:])
  raise
