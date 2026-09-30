#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,tarfile,zlib
from io import BytesIO
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];REP=PROJECT/'model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays';TEMPLATE=HERE/'main_template.py';ARCHIVE=HERE/'submission.tar.gz';EPISODES={'robust':100458412,'upside':100414724}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def actions(e):
 p=REP/f'episode-{e}-replay.json';r=json.loads(p.read_text());s=r['info']['TeamNames'].index('lucaskna');return [x[s].get('action') or {} for x in r['steps'][1:720]],p
def main():
 data={};paths={}
 for k,e in EPISODES.items():data[k],paths[k]=actions(e)
 packed=base64.b85encode(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9)).decode()
 for mode,name in [('full','main.py'),('ablation','ablation_main.py')]:
  text=TEMPLATE.read_text().replace('__PAYLOAD__',packed).replace('__MODE__',mode)
  if any(x in text for x in ('importlib','spec_from_file','parent_agent','load_parent','v76.agent')):raise RuntimeError('complete agent dependency')
  compile(text,f'v96-{mode}','exec');(HERE/name).write_text(text)
 with ARCHIVE.open('wb') as sink:
  with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
    d=(HERE/'main.py').read_bytes();i=tarfile.TarInfo('main.py');i.size=len(d);i.mode=0o644;i.uid=i.gid=i.mtime=0;i.uname=i.gname='';tar.addfile(i,BytesIO(d))
 m={'schema':'kaggriculture-v96-submission-v1','model_id':'v96_seat_priority_robust_route_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','archive_sha256':sha(ARCHIVE),'main_sha256':sha(HERE/'main.py'),'ablation_main_sha256':sha(HERE/'ablation_main.py'),'expert_episodes':EPISODES,'expert_replay_sha256':{k:sha(p) for k,p in paths.items()},'source_qualification_sha256':sha(HERE.parent/'source_route_robustness_audit.json'),'complete_historical_agent_bundled':False,'engine':'1.32.7','remote_submission':'NOT_AUTHORIZED_NOT_SUBMITTED'};(HERE/'submission_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps(m,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

