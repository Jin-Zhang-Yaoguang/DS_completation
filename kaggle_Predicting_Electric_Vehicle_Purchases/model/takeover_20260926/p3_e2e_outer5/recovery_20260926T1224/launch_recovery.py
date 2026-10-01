"""Detached launch of unchanged P3 continue.py under the frozen contract."""
from __future__ import annotations
import datetime,fcntl,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;E2E=HERE.parent;TOP=E2E.parent;ROOT=E2E.parents[2]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def ps(pids):
 r=subprocess.run(['ps','-p',','.join(map(str,pids)),'-o','pid,ppid,pgid,lstart,state,command'],capture_output=True,text=True)
 return {'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
def main():
 audit=json.loads((HERE/'recovery_audit.json').read_text())
 if audit['status']!='READY_TO_RESUME_SAME_CONTRACT' or audit['contract_sha256']!='4d254f2215f566fc8cefb11575645b177dfa8f9f4c4c3e9345ab3cf2f4f52466':raise RuntimeError('recovery audit not ready')
 if (HERE/'launch.json').exists():raise RuntimeError('launch already recorded; refuse duplicate')
 for name in ('run.lock','supervisor.lock'):
  with (E2E/name).open('a+') as f:
   fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
 existing=subprocess.run(['ps','-axo','pid,command'],capture_output=True,text=True).stdout
 if any('p3_e2e_outer5/'+name in line for line in existing.splitlines() for name in ('run.py','continue.py')):raise RuntimeError('P3 trainer/supervisor already alive')
 interpreter=Path(sys.executable).resolve()
 if str(interpreter)!='/opt/anaconda3/bin/python3.13':
  # The historical process used /opt/anaconda3/bin/python, which resolves here.
  if interpreter!=Path('/opt/anaconda3/bin/python').resolve():raise RuntimeError(f'unexpected interpreter {interpreter}')
 log=E2E/'supervisor.log'
 with log.open('ab',buffering=0) as output:
  child=subprocess.Popen([str(interpreter),str(E2E/'continue.py')],cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 supervisor_pid=child.pid;trainer_pid=None
 for _ in range(50):
  time.sleep(.2)
  if child.poll() is not None:raise RuntimeError(f'detached supervisor exited early rc={child.returncode}; inspect {log}')
  q=subprocess.run(['pgrep','-P',str(supervisor_pid)],capture_output=True,text=True)
  candidates=[int(x) for x in q.stdout.split() if x.isdigit()]
  if candidates:
   trainer_pid=candidates[0];break
 if trainer_pid is None:raise RuntimeError('trainer child not observed within 10s')
 detail=ps([supervisor_pid,trainer_pid])
 if detail['returncode'] or str(supervisor_pid) not in detail['stdout'] or str(trainer_pid) not in detail['stdout']:raise RuntimeError('ps cannot confirm both processes')
 report={'status':'DETACHED_SUPERVISOR_AND_TRAINER_ALIVE','launched_at_utc':now(),'interpreter':str(interpreter),'cwd':str(ROOT),'argv':[str(interpreter),str(E2E/'continue.py')],'stdin':'DEVNULL','stdout_stderr':str(log),'start_new_session':True,'close_fds':True,'supervisor_pid':supervisor_pid,'supervisor_ppid_at_observation':os.getpid(),'supervisor_pgid':os.getpgid(supervisor_pid),'trainer_pid':trainer_pid,'trainer_ppid':supervisor_pid,'trainer_pgid':os.getpgid(trainer_pid),'ps':detail,'recovery_audit':str(HERE/'recovery_audit.json'),'contract_sha256':audit['contract_sha256']}
 (HERE/'launch.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:report[k] for k in ('status','supervisor_pid','supervisor_pgid','trainer_pid','trainer_ppid','trainer_pgid','launched_at_utc')}))
if __name__=='__main__':main()
