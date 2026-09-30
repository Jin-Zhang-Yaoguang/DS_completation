#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,tarfile,zlib
from io import BytesIO
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[1];REP=PROJECT/'model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays';T=HERE/'main_template.py';A=HERE/'submission.tar.gz';EP=(100439801,100398798,100414724,100410172)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def feat(o,seat):
 f=o['farms'][seat];tiles=[t for row in f['tiles'] for t in row];kinds={'EMPTY':sum(t is None for t in tiles),'WEED':sum(isinstance(t,dict) and t.get('kind')=='WEED' for t in tiles),'PLANT':sum(isinstance(t,dict) and t.get('kind')=='PLANT' for t in tiles)}
 crops={c:sum(isinstance(t,dict) and t.get('crop')==c for t in tiles) for c in ('WHEAT','CARROT','TOMATO','STRAWBERRY','MELON')};p=o['private'];shop=(o['town']['unlocked_shops'] or ['NONE'])[0]
 return {'shop':shop,'quads':len(f['unlocked_quadrants']),'money':int(f['money']),'kinds':kinds,'crops':crops,'shed':{k:int(v) for k,v in p['shed'].items()},'seeds':{k:int(v) for k,v in p['seeds'].items()}}
def main():
 data={'routes':{},'refs':{},'base':str(EP[0])};paths={}
 for e in EP:
  p=REP/f'episode-{e}-replay.json';r=json.loads(p.read_text());s=r['info']['TeamNames'].index('lucaskna');data['routes'][str(e)]=[x[s].get('action') or {} for x in r['steps'][1:720]];data['refs'][str(e)]=[feat(r['steps'][d*24][s]['observation'],s) for d in range(30)];paths[str(e)]=sha(p)
 packed=base64.b85encode(zlib.compress(json.dumps(data,separators=(',',':')).encode(),9)).decode()
 for mode,name in [('full','main.py'),('ablation','ablation_main.py')]:
  text=T.read_text().replace('__PAYLOAD__',packed).replace('__MODE__',mode);compile(text,f'v100-{mode}','exec');(HERE/name).write_text(text)
 with A.open('wb') as sink:
  with gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0) as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT) as tar:
    d=(HERE/'main.py').read_bytes();i=tarfile.TarInfo('main.py');i.size=len(d);i.mode=0o644;i.uid=i.gid=i.mtime=0;i.uname=i.gname='';tar.addfile(i,BytesIO(d))
 m={'schema':'kaggriculture-v100-submission-v1','model_id':'v100_factorized_viability_kernel_moe','strategy_parent':None,'strength_comparator':'v76_adjacent_safe_buy_lead','archive_sha256':sha(A),'main_sha256':sha(HERE/'main.py'),'ablation_main_sha256':sha(HERE/'ablation_main.py'),'expert_episodes':list(EP),'expert_replay_sha256':paths,'complete_historical_agent_bundled':False,'engine':'1.32.7','remote_submission':'NOT_AUTHORIZED_NOT_SUBMITTED'};(HERE/'submission_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
if __name__=='__main__':main()

