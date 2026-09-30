"""Replay every synthesized crop program through the independent official engine."""
from pathlib import Path
import contextlib,importlib,io,json,sys
B=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
p=json.loads((B/'ddaj/crop_windows.json').read_text());checked=0
for j,job in enumerate(p['jobs']):
 for plan in job['alternatives']:
  crop=plan['crop'];farm={'tiles':[[None]],'farmer':[0,0],'hands':[]};private={'seeds':{crop:100},'inventories':[{}],'shed':{}}
  acts={};discounted=0.
  for e,token in zip(job['events'],plan['actions']):acts.setdefault(e[0],[]).append(token)
  for t in range(job['events'][0][0],job['events'][-1][0]+1):
   for token in acts.get(t,[]):
    before=private['inventories'][0].get(crop,0)
    engine._apply_unit_action(farm,private,0,token.split(':'),1,t//24,24,100)
    gain=private['inventories'][0].get(crop,0)-before
    discounted+=gain*.97**((t-job['purchase_step'])/24)
   engine._decay_plants(farm,t)
   if t%24==23:engine._daily_refresh_plants(farm,t//24,24)
  assert farm['tiles'][0][0] is None,(j,crop,'end not empty')
  assert private['inventories'][0].get(crop,0)==plan['yield_units'],(j,crop,private,plan)
  assert 100-private['seeds'][crop]==plan['seeds']
  assert abs(discounted-plan['discounted_units'])<1e-7
  checked+=1
result={'official_engine':'1.32.7','programs':checked,'all_yields_and_seed_costs_exact':True,'all_end_sites_empty':True}
(B/'audit_ddaj_crop_windows.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
