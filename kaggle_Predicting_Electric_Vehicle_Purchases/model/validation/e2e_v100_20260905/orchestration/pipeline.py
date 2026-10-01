"""Continue one existing training run into verified E2E scores."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
import psutil

ROOT=Path(__file__).resolve().parent
E2E=ROOT.parent
KERNEL='yaoguang516/s6e9-v100-e2e-ct-cache-20260905'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def js(path):return json.loads(Path(path).read_text())

def save(path,value):
    path=Path(path);tmp=path.with_name(path.name+f'.{os.getpid()}.tmp')
    with tmp.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def parse_gpu(stdout):
    matches=re.findall(r'KernelWorkerStatus\.(RUNNING|QUEUED|COMPLETE|ERROR|CANCELLED|CANCELED)',stdout)
    if len(matches)!=1:raise ValueError('Unrecognized GPU status; observation unknown')
    return matches[0]

def verified_process(pid,created,expected_cwd):
    try:
        p=psutil.Process(pid)
        if abs(p.create_time()-created)>0.01:raise ValueError('CPU PID was reused')
        if Path(p.cwd()).resolve()!=Path(expected_cwd).resolve():raise ValueError('CPU cwd mismatch')
        if p.cmdline()[-2:]!=['cpu_runner.py','cpu-all']:raise ValueError('CPU command mismatch')
        return p.is_running() and p.status()!=psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess,psutil.ZombieProcess):return False

def terminal_cpu(state,config):
    if state['config_sha256']!=config['cpu_config_sha256'] or state['pid']!=config['cpu_pid']:
        raise ValueError('CPU process or config state drift')
    if state['status']=='CPU_CACHE_COMPLETE':
        if state['completed_atoms']!=400:raise ValueError('CPU incomplete terminal state')
        return True
    return False

def cpu_state(config):
    state=js(E2E/'supervisor_state.json')
    if terminal_cpu(state,config):return 'COMPLETE'
    if verified_process(config['cpu_pid'],config['cpu_created'],E2E):return 'RUNNING'
    # The runner may have atomically published COMPLETE between the two reads.
    if terminal_cpu(js(E2E/'supervisor_state.json'),config):return 'COMPLETE'
    raise RuntimeError('CPU process missing before verified completion; recovery review required')

def freeze():
    dest=ROOT/'config.json';assert not dest.exists(),'pipeline already frozen'
    assert not (ROOT/'STARTED.json').exists()
    p=psutil.Process(24797)
    assert verified_process(p.pid,p.create_time(),E2E)
    receipt=js(E2E/'gpu/PUSH_RECEIPT.json')
    assert receipt['returncode']==0 and 'Kernel version 1 successfully pushed' in receipt['stdout']
    test=js(ROOT/'test_results.json')
    assert test['status']=='PASS' and test['tests_run']>=10
    for name,digest in test['code_sha256'].items():assert sha(ROOT/name)==digest,('test source drift',name)
    paths=[Path(__file__),ROOT/'test_pipeline.py',ROOT/'test_results.json',ROOT/'PREREGISTRATION.md',E2E/'gpu/archive_remote.py',E2E/'assembly_config.json',E2E/'frozen_config.json',
           E2E/'gpu/PUSH_RECEIPT.json',E2E/'gpu/revision_01/bundle_manifest.json']
    config={'cpu_pid':p.pid,'cpu_created':p.create_time(),'cpu_config_sha256':sha(E2E/'frozen_config.json'),'kernel':KERNEL,'version':1,
            'pipeline_seconds':15*3600,'gpu_query_seconds':60,'gpu_query_interval_seconds':120,
            'download_seconds':900,'stage_seconds':1800,'stage_memory_bytes':16*1024**3,'stage_threads':2,
            'sources':{str(f.relative_to(E2E)):sha(f) for f in paths},'submission_budget':0,'training_restarts':False}
    save(dest,config);print(json.dumps({'status':'FROZEN','sha256':sha(dest)}))

def check_sources(config):
    for name,digest in config['sources'].items():
        if sha(E2E/name)!=digest:raise ValueError('Source drift: '+name)

def stop_child(process):
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:pass
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    process.wait()

def remaining(started,total,requested):
    value=min(requested,total-(time.monotonic()-started))
    if value<=0:raise TimeoutError('pipeline wall budget exceeded')
    return value

def stage(config,name,args,limit):
    check_sources(config)
    marker=ROOT/f'{name}_COMPLETE.json'
    if marker.exists():raise RuntimeError('Stage already completed; do not duplicate execution')
    env=os.environ.copy()
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS']:env[key]='2'
    started=time.monotonic();peak=0
    with (ROOT/f'{name}.log').open('x') as output:
        process=subprocess.Popen(args,cwd=E2E,env=env,start_new_session=True,stdout=output,stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                elapsed=time.monotonic()-started
                try:
                    child_root=psutil.Process(process.pid)
                    descendants=[child_root,*child_root.children(recursive=True)]
                except (psutil.NoSuchProcess,psutil.ZombieProcess):
                    if process.poll() is not None:break
                    raise RuntimeError('stage process vanished before a terminal return code')
                rss=0
                for child in descendants:
                    try:rss+=child.memory_info().rss
                    except (psutil.NoSuchProcess,psutil.ZombieProcess):pass
                peak=max(peak,rss)
                if elapsed>=limit:raise TimeoutError(f'{name} wall budget exceeded')
                if peak>config['stage_memory_bytes']:raise MemoryError(f'{name} memory budget exceeded')
                time.sleep(.5)
            elapsed=time.monotonic()-started
            if elapsed>=limit:raise TimeoutError(f'{name} finished outside wall budget')
            if process.returncode:raise RuntimeError(f'{name} returned {process.returncode}; see preserved log')
        finally:stop_child(process)
    elapsed=time.monotonic()-started
    if elapsed>=limit:raise TimeoutError(f'{name} cleanup exceeded wall budget')
    check_sources(config)
    save(marker,{'status':'COMPLETE','elapsed':elapsed,'peak_rss_bytes':peak,'log_sha256':sha(ROOT/f'{name}.log')})

def run():
    config=js(ROOT/'config.json');check_sources(config)
    with (ROOT/'pipeline.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with (ROOT/'STARTED.json').open('x') as f:json.dump({'pid':os.getpid(),'started_unix':time.time(),'config_sha256':sha(ROOT/'config.json')},f)
        started=time.monotonic();next_gpu=0.;gpu='UNKNOWN';archived=False;observations=0
        try:
            while True:
                elapsed=time.monotonic()-started
                if elapsed>=config['pipeline_seconds']:raise TimeoutError('pipeline wall budget exceeded')
                check_sources(config);cpu=cpu_state(config)
                if not archived and time.monotonic()>=next_gpu:
                    next_gpu=time.monotonic()+config['gpu_query_interval_seconds']
                    result=None
                    try:
                        result=subprocess.run(['kaggle','kernels','status',KERNEL],capture_output=True,text=True,timeout=remaining(started,config['pipeline_seconds'],config['gpu_query_seconds']))
                        if result.returncode:raise RuntimeError('GPU status query failed')
                        gpu=parse_gpu(result.stdout)
                        observed={'status':gpu,'checked_unix':time.time(),'stdout':result.stdout,'stderr':result.stderr}
                    except (subprocess.TimeoutExpired,ValueError,RuntimeError) as exc:
                        observed={'status':'OBSERVATION_UNKNOWN','checked_unix':time.time(),'error':str(exc),
                                  'stdout':result.stdout if result else None,'stderr':result.stderr if result else None}
                        gpu='UNKNOWN'
                    observations+=1;save(ROOT/f'gpu_observation_{observations:04d}.json',observed)
                    if gpu in ['ERROR','CANCELLED','CANCELED']:raise RuntimeError('Existing GPU run terminal failure: '+gpu)
                    if gpu=='COMPLETE':
                        stage(config,'archive',[sys.executable,str(E2E/'gpu/archive_remote.py'),'download'],remaining(started,config['pipeline_seconds'],config['download_seconds']))
                        archived=True
                state={'status':'WAITING_EXISTING_TRAINING','pid':os.getpid(),'cpu':cpu,'gpu':gpu,'gpu_archived':archived,
                       'updated_unix':time.time(),'seconds':time.monotonic()-started,'partial_scores_computed':False}
                save(ROOT/'state.json',state)
                if cpu=='COMPLETE' and archived:break
                time.sleep(remaining(started,config['pipeline_seconds'],30))
            for mode in ['audit','assemble','score']:
                if time.monotonic()-started>=config['pipeline_seconds']:raise TimeoutError('pipeline wall budget exceeded')
                save(ROOT/'state.json',{'status':'POSTPROCESSING','stage':mode,'pid':os.getpid(),'updated_unix':time.time()})
                stage(config,mode,[sys.executable,str(E2E/'assemble_e2e.py'),mode],remaining(started,config['pipeline_seconds'],config['stage_seconds']))
            remaining(started,config['pipeline_seconds'],1)
            save(ROOT/'state.json',{'status':'SCORE_READY_FOR_REVIEW','pid':os.getpid(),'seconds':time.monotonic()-started,'updated_unix':time.time(),'actual_test_predictions':False,'competition_submission':False})
        except BaseException as exc:
            save(ROOT/'state.json',{'status':'STOPPED_REVIEW_REQUIRED','pid':os.getpid(),'error_type':type(exc).__name__,'error':str(exc),'seconds':time.monotonic()-started,'updated_unix':time.time(),'training_restarted':False,'competition_submission':False})
            raise
        finally:fcntl.flock(lock,fcntl.LOCK_UN)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['freeze','run']);a=p.parse_args()
    {'freeze':freeze,'run':run}[a.mode]()
