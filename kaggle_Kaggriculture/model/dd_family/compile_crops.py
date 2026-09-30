from pathlib import Path
import collections,json,sys
import numpy as np
B=Path(__file__).resolve().parent

def compile(version):
 d=B/version;sys.path.insert(0,str(d));import action_space as a
 k=json.loads((d/'config.json').read_text())['fixed_prototype'];ar={n:np.load(d/'data'/f'{n}.npy',mmap_mode='r')[:,k] for n in ['unit_tokens','unit_quantities','market_tokens','market_quantities','units']}
 events=collections.defaultdict(list)
 for t in range(719):
  for i,tok in enumerate(ar['unit_tokens'][t]):
   name=a.UNIT_TOKENS[int(tok)]
   if name in ['WATER','FERTILIZE','HARVEST'] or name.startswith('PLANT:'):
    xy=tuple(np.rint(ar['units'][t,i,2:4]*9).astype(int));events[xy].append((t,i,name))
 stock=[];jobs=[];purchases={};plants={}
 for t in range(719):
  for i,tok in enumerate(ar['unit_tokens'][t]):
   if a.UNIT_TOKENS[int(tok)]!='PLANT:CARROT':continue
   assert stock,(t,i);job=stock.pop(0);xy=tuple(np.rint(ar['units'][t,i,2:4]*9).astype(int));sequence=[]
   for tt,ii,name in events[xy]:
    if (tt,ii)<=(t,i):continue
    sequence.append((tt,ii,name))
    if name=='HARVEST':break
   if not sequence or sequence[-1][2]!='HARVEST' or any(n.startswith('PLANT:') for _,_,n in sequence):
    jobs[job].update(plant_step=t,plant_unit=i,eligible=False);plants[f'{t}:{i}']=job;continue
   harvest=sequence[-1][0];yields={}
   for crop,maxday,cap in [('CARROT',3,4),('WHEAT',4,6)]:
    yield_units=1;fert_until=-1;watered=set()
    for tt,ii,name in sequence:
     day=tt//24;age=day-t//24
     if name=='FERTILIZE':fert_until=day+2
     elif name=='WATER' and day not in watered:
      watered.add(day)
      if 2<=age<=maxday:yield_units=min(cap,yield_units+(2 if fert_until>=day else 1))
    yields[crop]=yield_units
   jobs[job].update(plant_step=t,plant_unit=i,harvest_step=harvest,yield_units=yields,eligible=True)
   plants[f'{t}:{i}']=job
  for slot,(tok,q) in enumerate(zip(ar['market_tokens'][t],ar['market_quantities'][t])):
   if a.MARKET_TOKENS[int(tok)]!='BUY_SEED:CARROT':continue
   ids=[]
   for _ in range(int(q)):
    job=len(jobs);jobs.append({'purchase_step':t,'purchase_slot':slot});stock.append(job);ids.append(job)
   purchases[f'{t}:{slot}']=ids
 out={'jobs':jobs,'purchases':purchases,'plants':plants,'unplanted':stock,'reference_prototype':k}
 (d/'crop_program.json').write_text(json.dumps(out,indent=2)+'\n');print('jobs',len(jobs),'plants',len(plants),'unused',len(stock),'yield pairs',dict(collections.Counter(tuple(j.get('yield_units',{}).values()) for j in jobs)))
if __name__=='__main__':compile(sys.argv[1])
