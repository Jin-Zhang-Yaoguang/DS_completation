"""Optimize annual crop actions within fixed replay labor windows, without movement edits."""
from pathlib import Path
import collections,json,sys
import numpy as np
B=Path(__file__).resolve().parent
EMPTY=(-1,0,-1,0);WEED=(-2,0,-1,0)

def advance(state,t,nt,crop):
 born,yld,water,unwatered=state
 if born<0:return state
 maxday=3 if crop=='CARROT' else 4
 for step in range(t,nt):
  expiry=(born+maxday+1)*24
  if step>=expiry and (step-expiry)%2==0:
   yld-=1
   if yld<=0:return WEED
  if step%24==23:
   unwatered=0 if water==step//24 else unwatered+1
   if unwatered>=2:return WEED
 return born,yld,water,unwatered

def optimize(events,crop,purchase):
 cost=20 if crop=='CARROT' else 10;budget=80//cost;cap=4 if crop=='CARROT' else 6;maxday=3 if crop=='CARROT' else 4
 # key=(biological state,seed count), value=(discounted harvest,raw harvest,action list)
 dp={(EMPTY,0):(0.,0,[])}
 for index,(t,i,name) in enumerate(events):
  nxt=events[index+1][0] if index+1<len(events) else t;new={}
  for (state,seeds),(value,total,actions) in dp.items():
   born,yld,water,unwatered=state;day=t//24;choices=[('PASS',state,seeds,0)]
   if born==-2:choices.append(('DIG',EMPTY,seeds,0))
   elif born==-1 and seeds<budget:choices.append(('PLANT:'+crop,(day,1,-1,1),seeds+1,0))
   elif born>=0:
    if water!=day:
     gain=int(2<=day-born<=maxday);choices.append(('WATER',(born,min(cap,yld+gain),day,unwatered),seeds,0))
    if day-born>=2 and yld>0:choices.append(('HARVEST',EMPTY,seeds,yld))
   for token,after,used,gain in choices:
    after=advance(after,t,nxt,crop);key=after,used
    score=value+gain*.97**((t-purchase)/24)
    if key not in new or score>new[key][0]+1e-9:new[key]=(score,total+gain,actions+[token])
  dp=new
 out=[]
 for (state,seeds),(value,total,actions) in dp.items():
  if state==EMPTY and seeds and total:
   out.append({'crop':crop,'seeds':seeds,'discounted_units':value,'yield_units':total,'actions':actions})
 return out

def compile(version):
 d=B/version;sys.path.insert(0,str(d));import action_space as a
 k=json.loads((d/'config.json').read_text())['fixed_prototype'];ar={n:np.load(d/'data'/f'{n}.npy',mmap_mode='r')[:,k] for n in ['unit_tokens','market_tokens','market_quantities','units','board']}
 byxy=collections.defaultdict(list)
 for t in range(719):
  for i,tok in enumerate(ar['unit_tokens'][t]):
   name=a.UNIT_TOKENS[int(tok)]
   if name.startswith('PLANT:') or name in ['WATER','FERTILIZE','HARVEST','DIG']:
    xy=tuple(map(int,np.rint(ar['units'][t,i,2:4]*9)));byxy[xy].append([t,i,name])
 jobs=[];stock=[];purchases={};units={}
 for t in range(719):
  for i,tok in enumerate(ar['unit_tokens'][t]):
   if a.UNIT_TOKENS[int(tok)]!='PLANT:MELON':continue
   assert stock,(t,i);j=stock.pop(0);job=jobs[j];xy=tuple(map(int,np.rint(ar['units'][t,i,2:4]*9)));events=[[t,i,'PLANT:MELON']]
   for tt,ii,name in byxy[xy]:
    if (tt,ii)<=(t,i):continue
    events.append([tt,ii,name])
    if name=='HARVEST' or name.startswith('PLANT:'):break
   job.update(plant_step=t,events=events,xy=list(xy),alternatives=[])
   if events[-1][2]!='HARVEST' or any(e[2].startswith('PLANT:') for e in events[1:]):continue
   h=events[-1][0];x,y=xy;job['original_yield']=round(float(ar['board'][h].reshape(100,21)[y*10+x,13])*10)
   job['original_discounted_units']=job['original_yield']*.97**((h-job['purchase_step'])/24)
   for crop in ['CARROT','WHEAT']:job['alternatives']+=optimize(events,crop,job['purchase_step'])
   for tt,ii,name in events:
    key=f'{tt}:{ii}';assert key not in units;units[key]=[j,len([e for e in events if (e[0],e[1])<(tt,ii)])]
  for slot,(tok,q) in enumerate(zip(ar['market_tokens'][t],ar['market_quantities'][t])):
   if a.MARKET_TOKENS[int(tok)]!='BUY_SEED:MELON':continue
   ids=[]
   for _ in range(int(q)):
    j=len(jobs);jobs.append({'purchase_step':t,'purchase_slot':slot,'alternatives':[]});stock.append(j);ids.append(j)
   purchases[f'{t}:{slot}']=ids
 out={'reference_prototype':k,'jobs':jobs,'purchases':purchases,'units':units,'unused_seeds':stock,'assumptions':['Existing original plant site is empty','No fertilizer used in alternative','Final site must be empty at original harvest time','Harvest prices estimated from purchase-time public quotes']}
 (d/'crop_windows.json').write_text(json.dumps(out,indent=2)+'\n')
 print({'jobs':len(jobs),'eligible':sum(bool(j['alternatives']) for j in jobs),'programs':sum(len(j['alternatives']) for j in jobs)})
if __name__=='__main__':compile(sys.argv[1])
