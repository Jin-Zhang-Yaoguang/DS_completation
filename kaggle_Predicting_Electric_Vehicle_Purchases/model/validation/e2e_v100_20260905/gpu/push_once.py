"""Persistent dispatch intent: never retries an uncertain Kaggle push."""
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');os.replace(tmp,path)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True)
    args=p.parse_args();bundle=Path(args.bundle).resolve()
    assert bundle==ROOT/'revision_01','only reviewed implementation revision may be dispatched'
    manifest=json.loads((bundle/'bundle_manifest.json').read_text())
    for name,digest in manifest['files'].items():assert sha(bundle/name)==digest,('bundle drift',name)
    metadata=json.loads((bundle/'kernel/kernel-metadata.json').read_text())
    assert metadata['is_private'] is True and metadata['id']=='yaoguang516/s6e9-v100-e2e-ct-cache-20260905'
    assert json.loads((bundle/'self_test_results.json').read_text())['status']=='SYNTHETIC_CONTRACT_PASS'
    with (ROOT/'local_dispatch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        marker=ROOT/'PUSH_STARTED.json';receipt=ROOT/'PUSH_RECEIPT.json'
        assert not marker.exists() and not receipt.exists(),'dispatch already attempted; query same kernel status, never blindly push again'
        intent={'attempt':str(uuid.uuid4()),'started_unix':time.time(),'kernel':metadata['id'],'status':'PUSH_STARTED',
                'bundle_manifest_sha256':sha(bundle/'bundle_manifest.json'),'config_sha256':sha(bundle/'frozen_config.json')}
        # Written durably before the external mutation. Unknown responses are not authorization to retry.
        with marker.open('x') as f:json.dump(intent,f,indent=2);f.flush();os.fsync(f.fileno())
        try:
            result=subprocess.run(['kaggle','kernels','push','-p',str(bundle/'kernel'),'-t','7200'],text=True,capture_output=True,timeout=120)
            state={**intent,'status':'PUSH_RETURNED','returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'finished_unix':time.time()}
            write_json(receipt,state);print(json.dumps(state,indent=2))
            raise SystemExit(result.returncode)
        except Exception as exc:
            state={**intent,'status':'PUSH_OUTCOME_UNKNOWN','error_type':type(exc).__name__,'error':str(exc),'finished_unix':time.time()}
            write_json(receipt,state);raise
