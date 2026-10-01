from __future__ import annotations
import concurrent.futures,datetime,json,time
from pathlib import Path
from kaggle import api
OUT=Path(__file__).resolve().parent;COMP='playground-series-s6e9'
def ser(x):
 if isinstance(x,datetime.datetime):return x.isoformat()
 if hasattr(x,'__dict__'):return {k.lstrip('_'):v for k,v in x.__dict__.items() if k!='_is_frozen'}
 raise TypeError(type(x))
def save(name,x):(OUT/name).write_text(json.dumps(x,default=ser,ensure_ascii=False,indent=2)+'\n')
def attempt(fn):
 for k in range(3):
  try:return fn()
  except Exception:
   if k==2:raise
   time.sleep(3*(k+1))
topics={}
for page in range(1,12):
 r=attempt(lambda:api.competition_list_topics(COMP,sort_by='new',page=page));save(f'list_{page}.json',r)
 old=len(topics)
 for t in r.topics:topics[t.id]=t
 print('topics page',page,'items',len(r.topics),'total',r.total_count,flush=True)
 if not r.topics or old==len(topics):break
save('topics.json',list(topics.values()))
oldids={t['id'] for t in json.loads((OUT.parents[1]/'forum_review_20260926/evidence/topics.json').read_text())}
selected=[t for t in topics.values() if t.id not in oldids or str(t.last_comment_post_date)>='2026-09-26' or t.id in (742904,742697,743298,742317)]
def fetch(t):
 try:
  topic,comments,token=attempt(lambda:api.forums_topic_show(t.id));save(f'topic_{t.id}.json',{'topic':topic,'comments':comments,'next_page_token':token});return {'id':t.id,'title':t.title,'comments':len(comments),'next_page_token':token,'status':'OK'}
 except Exception as e:return {'id':t.id,'status':'ERROR','error':str(e)[:700]}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 results=list(pool.map(fetch,selected))
save('fetch_results.json',results)
print('forum results',results,flush=True)
for sort in ('scoreDescending','dateRun'):
 try:
  r=attempt(lambda:api.kernels_list(competition=COMP,sort_by=sort,page_size=100));save('kernels_'+sort+'.json',r);print('kernels',sort,len(r),flush=True)
 except Exception as e:save('kernels_'+sort+'_error.json',{'error':str(e)})
try:save('leaderboard.json',attempt(lambda:api.competition_leaderboard_view(COMP)))
except Exception as e:save('leaderboard_error.json',{'error':str(e)})
save('retrieval.json',{'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'topics_total':len(topics),'selected':len(selected),'new_topic_ids':sorted(set(topics)-oldids),'method':'official Kaggle SDK in CLI; read only'})
