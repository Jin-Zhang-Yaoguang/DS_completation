import hashlib
import json
from pathlib import Path

def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

print(json.dumps({
    "agent": 'hybrid_sixday_combined_publicstate_r4',
    "policy_sha256": 'a1ee929e5639cffbbf9c7722af147a674f1a973613c8fd0ac4f74bdad07c9355',
    "main_py_sha256": file_hash("/kaggle/working/main.py"),
    "agent_so_sha256": file_hash("/kaggle/working/agent.so"),
    "submission_archive_sha256": file_hash("/kaggle/working/sixday-publicstate-agent.tar.gz"),
    "runtime_features_exclude": ["opponent identity", "seed", "result", "future shops"],
}, indent=2))
