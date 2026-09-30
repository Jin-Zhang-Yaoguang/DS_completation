"""Compile replay care/harvest/deposit events; verify original yields against replay."""
from pathlib import Path
import json,sys
import numpy as np
B=Path(__file__).resolve().parent

def compile(version):
 d=B/version;sys.path.insert(0,str(d));import action_space as a,rules
 p=json.loads((d/'animal_program.json').read_text());k=p['reference_prototype']
 ar={n:np.load(d/'data'/f'{n}.npy',mmap_mode='r')[:,k] for n in ['unit_tokens','units','board']}
 jobs=[]
 for key,g in p['events']['unit'].items():
  t,i=map(int,key.split(':'));name=a.UNIT_TOKENS[int(ar['unit_tokens'][t,i])]
  if not name.startswith('PLACE:'):continue
  x,y=map(int,np.rint(ar['units'][t,i,2:4]*9));events=[]
  end=next((tt for tt in range(t+1,719) if not ar['board'][tt].reshape(100,21)[y*10+x,10:13].sum()),719)
  for tt in range(t+1,end):
   for ii,tok in enumerate(ar['unit_tokens'][tt]):
    n=a.UNIT_TOKENS[int(tok)];xx,yy=map(int,np.rint(ar['units'][tt,ii,2:4]*9))
    if (xx,yy)!=(x,y) or n not in ['FEED','CARE','HARVEST']:continue
    sale=tt
    if n=='HARVEST':
     sale=(tt//24+1)*24
     for future in range(tt+1,min(719,(tt//24+1)*24)):
      nt=a.UNIT_TOKENS[int(ar['unit_tokens'][future,ii])]
      pos=tuple(map(int,np.rint(ar['units'][future,ii,2:4]*9)))
      if nt=='DROP' and rules._is_shed_adjacent(pos,10):sale=future;break
    events.append([tt,n,sale])
  jobs.append({'group':g,'place':t,'end':end,'xy':[x,y],'events':events})
 # Independent official refresh validates the original species model.
 import contextlib,io,importlib
 with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
  engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
 checked=0;mismatches=[]
 for j in jobs:
  species=p['groups'][j['group']]['original'];tile=rules._new_animal(species,j['place']//24);farm={'tiles':[[tile]]};by={}
  for t,n,sale in j['events']:by.setdefault(t,[]).append(n)
  for t in range(j['place']+1,j['end']):
   tile=farm['tiles'][0][0]
   for n in by.get(t,[]):
    if n=='FEED' and 'animal' in tile:tile['fed_today']=True
    elif n=='CARE' and 'animal' in tile:tile['cared_today']=True
    elif n=='HARVEST':
     x,y=j['xy'];actual=round(float(ar['board'][t].reshape(100,21)[y*10+x,13])*10)
     if tile.get('yield_units',0)!=actual:mismatches.append({'place':j['place'],'step':t,'predicted':tile.get('yield_units',0),'reference':actual})
     checked+=1;tile['yield_units']=0
   if t%24==23:engine._daily_refresh_animals(farm,t//24)
 out={'reference_prototype':k,'jobs':jobs,'assumptions':['Future planned feed and care requests succeed','Harvest sold at next scheduled shed drop or next-day opening; capacity spill not forecast']}
 (d/'animal_schedules.json').write_text(json.dumps(out,indent=2)+'\n')
 audit={'version':version,'animals':len(jobs),'harvest_checks':checked,'mismatches':mismatches}
 (B/f'audit_{version}_schedules.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit))
 assert not mismatches,'Do not use an unverified schedule model'
if __name__=='__main__':compile(sys.argv[1])
