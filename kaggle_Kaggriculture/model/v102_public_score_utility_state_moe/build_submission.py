#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,tarfile,zlib
from io import BytesIO
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];R=PROJECT/'model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100439801-replay.json';T=HERE/'main_template.py';A=HERE/'submission.tar.gz'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def main():
 r=json.loads(R.read_text());s=r['info']['TeamNames'].index('lucaskna');data={'actions':[x[s].get('action') or {} for x in r['steps'][1:720]]};p=base64.b85encode(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9)).decode()
 for mode,name in [('full','main.py'),('ablation','ablation_main.py')]:text=T.read_text().replace('__PAYLOAD__',p).replace('__MODE__',mode);compile(text,f'v102-{mode}','exec');(HERE/name).write_text(text)
 with A.open('wb') as sink:
  with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
    d=(HERE/'main.py').read_bytes();i=tarfile.TarInfo('main.py');i.size=len(d);i.mode=0o644;i.uid=i.gid=i.mtime=0;i.uname=i.gname='';tar.addfile(i,BytesIO(d))
 m={'schema':'kaggriculture-v102-submission-v1','model_id':'v102_public_score_utility_state_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','archive_sha256':sha(A),'main_sha256':sha(HERE/'main.py'),'ablation_main_sha256':sha(HERE/'ablation_main.py'),'growth_expert_episode':100439801,'growth_expert_replay_sha256':sha(R),'complete_historical_agent_bundled':False,'engine':'1.32.7','remote_submission':'NOT_AUTHORIZED_NOT_SUBMITTED'};(HERE/'submission_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
if __name__=='__main__':main()

