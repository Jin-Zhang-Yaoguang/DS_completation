"""Inventory official daily replays without loading all trajectory frames."""
from pathlib import Path
import collections,concurrent.futures,json,re,hashlib
B=Path(__file__).resolve().parent;INDEX=B.parent.parent/'model_data/kaggriculture_episodes_index'
def header(p):
    try:
        with p.open('r') as f:s=f.read(131072)
        values={}
        for key in ['info','rewards','statuses','module_version']:
            m=re.search(r'"'+key+r'"\s*:\s*',s)
            values[key]=json.JSONDecoder().raw_decode(s[m.end():])[0]
        if values['module_version']!='1.32.7' or values['statuses']!=['DONE','DONE']:return None
        return {'path':str(p.resolve()),'episode_id':values['info']['EpisodeId'],
                'seed':values['info']['seed'],'teams':values['info']['TeamNames'],'rewards':values['rewards'],
                'source':'official_daily_dataset','date':p.parents[1].name.removeprefix('date=')}
    except Exception as e:return {'path':str(p),'error':repr(e)}
def main():
    paths=[p for day in ['2026-09-14','2026-09-15','2026-09-16'] for p in (INDEX/f'date={day}/data').glob('*.json')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(header,paths))
    errors=[r for r in rows if r and 'error' in r];valid=[r for r in rows if r and 'error' not in r]
    seen=set();valid=[r for r in valid if not (r['episode_id'] in seen or seen.add(r['episode_id']))]
    groups=collections.defaultdict(list)
    for r in valid:
        for seat,name in enumerate(r['teams']):
            groups[name].append({'cash':r['rewards'][seat],'margin':r['rewards'][seat]-r['rewards'][1-seat],**r,'seat':seat})
    summary=[]
    for name,rs in groups.items():
        summary.append({'teacher':name,'games':len(rs),'win_rate':sum(r['margin']>0 for r in rs)/len(rs),
                        'mean_cash':sum(r['cash'] for r in rs)/len(rs),'mean_margin':sum(r['margin'] for r in rs)/len(rs)})
    summary.sort(key=lambda r:(r['mean_margin']),reverse=True)
    (B/'teacher_inventory.json').write_text(json.dumps({'dates':['2026-09-14','2026-09-15','2026-09-16'],
        'files':len(paths),'valid':len(valid),'errors':errors,'summary':summary,'rows':valid,
        'version_boundary':'Names identify observed teams, not verified submission versions; do not claim current active-model identity.'},indent=2)+'\n')
    print('files',len(paths),'valid',len(valid),'errors',len(errors));print(json.dumps([r for r in summary if r['games']>=20][:25],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
