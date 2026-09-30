"""Strict gate completeness and reproducible cross-seed trajectory agreement."""
from pathlib import Path
import json,gzip,itertools,hashlib,statistics
import numpy as np
G=Path(__file__).resolve().parent

def stats(vals):
 a=np.asarray(vals,float)
 return {'mean':float(a.mean()),'median':float(np.median(a)),'min':float(a.min()),'max':float(a.max()),'p90':float(np.quantile(a,.9))}
def similarity(rows):
 pairs=[(i,j) for i,j in itertools.combinations(range(len(rows)),2) if rows[i]['seed']!=rows[j]['seed'] and rows[i]['seat']==rows[j]['seat']]
 out={'pair_count':len(pairs),'same_seat_cross_seed':True};n=len(rows)
 for key in ['unit_hash','market_hash','full_hash','position_hash']:
  x=np.asarray([[s[key] for s in r['trace']] for r in rows]);eq=np.asarray([x[i]==x[j] for i,j in pairs]);out[key]=stats(eq.mean(axis=1))
  if key=='unit_hash':
   active=np.asarray([[s['active'] for s in r['trace']] for r in rows]);mask=np.asarray([active[i]|active[j] for i,j in pairs]);valid=mask.sum(axis=1)>0
   out['units_excluding_both_idle']=stats((eq&mask).sum(axis=1)[valid]/mask.sum(axis=1)[valid]);out['unit_daily_mean']=[float(eq[:,d*24:min((d+1)*24,719)].mean()) for d in range(30)]
   out['unit_after_day3_mean']=float(eq[:,72:].mean());out['unit_before_day3_mean']=float(eq[:,:72].mean())
 # Per-actor partial agreement: extra/missing workers count as different.
 # This explains how strict whole-team comparison can be low despite a common routine.
 actor=[];farmer=[]
 for i,j in pairs:
  hits=total=0;f=0
  for a,b in zip(rows[i]['trace'],rows[j]['trace']):
   ua,ub=a['units'],b['units'];total+=max(len(ua),len(ub));hits+=sum(x==y for x,y in zip(ua,ub));f+=ua[0]==ub[0]
  actor.append(hits/total);farmer.append(f/719)
 out['per_actor_agreement']=stats(actor);out['farmer_agreement']=stats(farmer)
 pl=np.asarray([[p['tiles'] for p in r['plan_log']] for r in rows]);out['daily_plan_tile_agreement']=stats([float((pl[i]==pl[j]).mean()) for i,j in pairs])
 return out
