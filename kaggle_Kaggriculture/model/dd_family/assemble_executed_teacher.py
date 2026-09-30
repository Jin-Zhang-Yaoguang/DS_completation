"""Install verified canonical arrays without modifying parent hardlinked data."""
from pathlib import Path
import hashlib,json,os,shutil
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddaq';S=B/'executed_new_teacher'
man=json.loads((S/'compile_manifest.json').read_text());good=man['compiled'];assert man['expected']==121 and good
for name,shape in [('unit_tokens',(719,121,16)),('unit_quantities',(719,121,16)),('market_tokens',(719,121,10)),('market_quantities',(719,121,10))]:
 temporary=D/'data'/f'{name}.canonical.npy';arr=np.lib.format.open_memmap(temporary,mode='w+',dtype=np.int32,shape=shape);arr[:]=0
 for k in good:
  audit=json.loads((S/f'{k:03}_audit.json').read_text());assert audit['exact_canonical_states']
  with np.load(S/f'{k:03}_effective.npz') as z:arr[:,k]=z[name]
 arr.flush();del arr;os.replace(temporary,D/'data'/f'{name}.npy')
for k in good:shutil.copy2(S/f'{k:03}_program.json',D/'plans'/f'{k:03}.json')
(D/'compiled_plans.json').write_text(json.dumps({'compiled':good,'unsupported':man['errors'],'source':'official successful-transition telemetry','canonical_state_validation':True},indent=2)+'\n')
manifest=json.loads((D/'training_manifest.json').read_text());manifest['method']='executed-event hierarchical distillation';manifest['raw_source_data_sha256']=manifest.pop('data_sha256',{});manifest['effective_arrays_sha256']={name:hashlib.sha256((D/'data'/f'{name}.npy').read_bytes()).hexdigest() for name in ['unit_tokens','unit_quantities','market_tokens','market_quantities']};manifest['executed_compiler_sha256']=man['compiler_sha256'];(D/'training_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('assembled',len(good))
