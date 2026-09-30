"""已知高分对手提交 → 所属队伍与最近 5 天全部完成对局(SDK)。输出 team_subs.json。"""
import json, time, datetime
from kaggle.api.kaggle_api_extended import KaggleApi
api=KaggleApi(); api.authenticate()
SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
L=json.load(open("roff_list.json")); out={}
for sub in L:
    try:
        E=api.competition_list_episodes(int(sub))
    except Exception as ex:
        time.sleep(5); continue
    team=None; eps=[]
    for e in E:
        if "PUBLIC" not in str(e.type) or not str(e.state).endswith("COMPLETED"): continue
        me=[a for a in e.agents if a.submission_id==int(sub)]
        if me: team=team or me[0].team_name
        if str(e.end_time)>=SINCE.replace("T"," "): eps.append(e.id)
    out[sub]={"team":team,"eps":eps}
    time.sleep(0.5)
json.dump(out,open("team_subs.json","w"),ensure_ascii=False)
print("提交",len(out))
