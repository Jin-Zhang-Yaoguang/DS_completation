"""Freeze an auditable private kernel bundle, without pushing or running it."""
import ast
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[3]
HIST=PROJECT/'model/diagnostics/ctboost_remote_probe_20260905'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')

if __name__=='__main__':
    assert not (ROOT/'frozen_config.json').exists() and not (ROOT/'kernel').exists(),'frozen files are immutable'
    check=json.loads((ROOT/'self_test_results.json').read_text());assert check['status']=='SYNTHETIC_CONTRACT_PASS'
    for name,digest in check['code_sha256'].items():assert sha(ROOT/name)==digest,('smoke stale',name)
    notebook=HIST/'kernel/s6e9-ctboost-oof-audit.ipynb'
    assert sha(notebook)=='a78ce26d2f8f6c23bf15edb317f457d3e568823a7a92769f397b270bfb608209'
    nb=json.loads(notebook.read_text());source='\n\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type']=='code')
    bootstrap=source[source.index('import hashlib'):source.index("input_dir = Path('/kaggle/input')")]
    (ROOT/'bootstrap.py').write_text(bootstrap)
    history=json.loads((HIST/'remote_output/run_summary.json').read_text())
    cfg={'experiment_id':'E2E_V100_CT_CACHE_20260905','outer_folds':5,'outer_seed':42437,'inner_folds':5,'inner_seed':42,
         'iterations':1426,'model_seed':20260904,'params':history['params'],'require_gpu':True,'remote_versions':history['versions'],
         'source_sha256':{'train.csv':sha(PROJECT/'data/train.csv'),'original.csv':sha(PROJECT/'data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv'),
                          'historical_ct_notebook':sha(notebook)},
         'code_sha256':{name:sha(ROOT/name) for name in ['cache_runner.py','ct_features.py','supervisor.py','bootstrap.py']},
         'budget_seconds':7200,'memory_bytes':24*1024**3,'threads':4,'submission_budget':0,'outer_scores_not_computed':True,
         'preregistration_sha256':sha(ROOT/'PREREGISTRATION.md'),'synthetic_test_sha256':sha(ROOT/'self_test_results.json')}
    write_json(ROOT/'frozen_config.json',cfg)
    payload_files=['cache_runner.py','ct_features.py','supervisor.py','bootstrap.py','frozen_config.json']
    payload='from pathlib import Path\nimport subprocess,sys\nwork=Path("/kaggle/working")\n'
    for name in payload_files:payload+=f'(work/{name!r}).write_text({(ROOT/name).read_text()!r})\n'
    payload+='subprocess.run([sys.executable,"-u",str(work/"supervisor.py")],cwd=work,check=True)\n'
    ast.parse(payload)
    kernel=ROOT/'kernel';kernel.mkdir()
    outnb={'cells':[{'cell_type':'markdown','metadata':{},'source':['# S6E9 complete V100 CT outer caches\n','Private verification only. No competition submission.']},
        {'cell_type':'code','metadata':{},'source':payload.splitlines(keepends=True),'outputs':[],'execution_count':None}],
        'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.11.13'}},'nbformat':4,'nbformat_minor':5}
    codefile='s6e9-v100-e2e-ct-cache-20260905.ipynb';write_json(kernel/codefile,outnb)
    meta=json.loads((HIST/'kernel/kernel-metadata.json').read_text())
    meta.update(id='yaoguang516/s6e9-v100-e2e-ct-cache-20260905',title='S6E9 V100 E2E CT Cache 20260905',code_file=codefile,is_private=True)
    write_json(kernel/'kernel-metadata.json',meta)
    write_json(ROOT/'bundle_manifest.json',{'status':'FROZEN_NOT_STARTED','kernel':meta['id'],'files':{str(f.relative_to(ROOT)):sha(f) for f in [*[ROOT/n for n in payload_files],kernel/codefile,kernel/'kernel-metadata.json']}})
    print(json.dumps({'status':'FROZEN_NOT_STARTED','kernel':meta['id'],'notebook_sha256':sha(kernel/codefile),'config_sha256':sha(ROOT/'frozen_config.json')},indent=2))
