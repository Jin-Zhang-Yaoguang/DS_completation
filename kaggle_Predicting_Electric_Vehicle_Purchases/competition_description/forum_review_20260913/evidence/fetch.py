import json,time,datetime,pathlib,concurrent.futures
from kaggle import api
out=pathlib.Path('/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/strange-gates-ca18fe/kaggle_Predicting_Electric_Vehicle_Purchases/competition_description/forum_review_20260913/evidence')
def ser(x):
 if isinstance(x,datetime.datetime): return x.isoformat()
 if hasattr(x,'__dict__'): return {k.lstrip('_'):v for k,v in x.__dict__.items() if k!='_is_frozen'}
 raise TypeError(type(x))
def save(name,x): (out/name).write_text(json.dumps(x,default=ser,ensure_ascii=False,indent=2))
topics={}
for page in range(1,30):
 r=api.competition_list_topics('playground-series-s6e9',sort_by='new',page=page)
 save(f'list_{page}.json',r)
 print('PAGE',page,'items',len(r.topics),'total',r.total_count,flush=True)
 old=len(topics)
 for t in r.topics: topics[t.id]=t
 if not r.topics or len(topics)==old: break
save('topics.json',list(topics.values()))
def fetch(t):
 for attempt in range(3):
  try:
   topic,comments,token=api.forums_topic_show(t.id)
   save(f'topic_{t.id}.json',{'topic':topic,'comments':comments,'next_page_token':token})
   return (t.id,len(comments),'OK')
  except Exception as e:
   if attempt==2:return(t.id,str(e),'ERROR')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for r in ex.map(fetch,topics.values()): print(r,flush=True)
print('DONE',len(topics),flush=True)
