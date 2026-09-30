#!/usr/bin/env python3
from __future__ import annotations
import gzip,hashlib,json,tarfile
from io import BytesIO
from pathlib import Path
HERE=Path(__file__).resolve().parent;TEMPLATE=HERE/'main_template.py';ARCHIVE=HERE/'submission.tar.gz'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 for mode,name in [('full','main.py'),('ablation','ablation_main.py')]:
  text=TEMPLATE.read_text().replace('__MODE__',mode)
  if any(x in text for x in ('importlib','spec_from_file','parent_agent','load_parent','v76.agent')):raise RuntimeError('complete agent dependency')
  compile(text,f'v98-{mode}','exec');(HERE/name).write_text(text)
 with ARCHIVE.open('wb') as sink:
  with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
    d=(HERE/'main.py').read_bytes();i=tarfile.TarInfo('main.py');i.size=len(d);i.mode=0o644;i.uid=i.gid=i.mtime=0;i.uname=i.gname='';tar.addfile(i,BytesIO(d))
 m={'schema':'kaggriculture-v98-submission-v1','model_id':'v98_stochastic_disturbance_state_graph_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','archive_sha256':sha(ARCHIVE),'main_sha256':sha(HERE/'main.py'),'ablation_main_sha256':sha(HERE/'ablation_main.py'),'replay_action_streams_bundled':False,'source_screen_sha256':sha(HERE/'source_screen_results.json'),'complete_historical_agent_bundled':False,'engine':'1.32.7','remote_submission':'NOT_AUTHORIZED_NOT_SUBMITTED'};(HERE/'submission_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps(m,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

