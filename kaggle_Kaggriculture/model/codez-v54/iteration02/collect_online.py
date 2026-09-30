"""Read-only Kaggle CLI SDK snapshot and reproducible replay admission."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
from kaggle.api.kaggle_api_extended import KaggleApi

ROOT=Path(__file__).resolve().parent
SUBMISSIONS=[56477312,56477321,56461411]

def fetch(row):
    eid=row['id'];dest=ROOT/'replays';target=dest/f'episode-{eid}-replay.json'
    try:
        if not target.exists():
            api=KaggleApi();api.authenticate();api.competition_episode_replay(eid,path=str(dest),quiet=True)
        raw=target.read_bytes();r=json.loads(raw)
        assert r['module_version']=='1.32.7'
        assert len(r['steps'])==720 and r['statuses']==['DONE','DONE']
        assert r['info']['EpisodeId']==eid
        seat=row['seat'];opp=1-seat
        assert r['info']['TeamNames'][seat]=='datatuu'
        assert [float(v) for v in r['rewards']]==[float(a['reward']) for a in sorted(row['agents'],key=lambda a:a.get('index',0))]
        def obs(t):
            o=dict(r['steps'][t][0]['observation']);o.update(r['steps'][t][seat]['observation']);return o
        signatures={}
        for t in [2,144,150,160,216,288,432,648,719]:
            o=obs(t);signatures[str(t)]={'cash':[f['money'] for f in o['farms']],
                'wheat':o['market']['inventory']['WHEAT'],'shops':o['town'].get('unlocked_shops',[]),
                'hands':[len(f['hands']) for f in o['farms']]}
        # Requests and observed rewards are deliberately separate; no fictitious fills.
        tape={'episode_id':eid,'submission_id':row['submission_id'],'seed':r['info']['seed'],
            'seat':seat,'opponent_name':r['info']['TeamNames'][opp],
            'opponent_submission_id':row['opponent_submission_id'],
            'replay_sha256':hashlib.sha256(raw).hexdigest(),'module_version':r['module_version'],
            'rewards':r['rewards'],'live_margin':row['live_margin'],'observations':signatures,
            'actions':[[r['steps'][t+1][p].get('action') or {} for p in [0,1]] for t in range(719)]}
        out=ROOT/'tapes'/f'{eid}.json';out.parent.mkdir(exist_ok=True)
        payload=json.dumps(tape,ensure_ascii=False,separators=(',',':')).encode()
        if out.exists():assert out.read_bytes()==payload
        else:out.write_bytes(payload)
        return {'status':'admitted','episode_id':eid,'tape':str(out.relative_to(ROOT)),
            'tape_sha256':hashlib.sha256(payload).hexdigest(),**{k:v for k,v in tape.items() if k!='actions'}}
    except Exception as e:return {'status':'error','episode_id':eid,'error':repr(e)}

if __name__=='__main__':
    snapshot=ROOT/'online_snapshot.json'
    if snapshot.exists():data=json.loads(snapshot.read_text())
    else:
        api=KaggleApi();api.authenticate();episodes=[]
        for sid in SUBMISSIONS:
            for e in api.competition_list_episodes(sid):
                r=e.to_dict()
                if r.get('type')!='EPISODE_TYPE_PUBLIC' or r.get('state')!='COMPLETED':continue
                me=next((a for a in r['agents'] if a['submissionId']==sid),None)
                if me is None or me.get('reward') is None:continue
                other=next(a for a in r['agents'] if a is not me)
                if other.get('reward') is None:continue
                episodes.append({**r,'submission_id':sid,'seat':me.get('index',0),
                    'opponent_submission_id':other['submissionId'],'opponent_name':other.get('teamName'),
                    'live_margin':me['reward']-other['reward']})
        data={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'episodes':episodes,
            'scope':'Returned completed public episodes; not a claim of all historical episodes.'}
        snapshot.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    selected={}
    for sid in SUBMISSIONS:
        es=[e for e in data['episodes'] if e['submission_id']==sid]
        losses=sorted([e for e in es if e['live_margin']<0],key=lambda e:e['live_margin'])[:12]
        wins=sorted([e for e in es if e['live_margin']>=0],key=lambda e:hashlib.sha256(str(e['id']).encode()).hexdigest())[:8]
        for e in losses+wins:selected.setdefault(e['id'],e)
        print(sid,'public',len(es),'W/L/T',sum(e['live_margin']>0 for e in es),sum(e['live_margin']<0 for e in es),sum(e['live_margin']==0 for e in es),'selected',len(losses+wins),flush=True)
    plan=ROOT/'replay_selection.json'
    if not plan.exists():plan.write_text(json.dumps(list(selected.values()),ensure_ascii=False,indent=2))
    with concurrent.futures.ThreadPoolExecutor(3) as ex:records=list(ex.map(fetch,selected.values()))
    (ROOT/'replay_registry.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    print('admitted',sum(x['status']=='admitted' for x in records),'errors',sum(x['status']=='error' for x in records),flush=True)
    assert all(x['status']=='admitted' for x in records)
