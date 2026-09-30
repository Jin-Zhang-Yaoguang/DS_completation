"""Counterexample-guided plan search. All matches remain development data."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json
import numpy as np
import search_plans as search
B=Path(__file__).resolve().parent;OUT=B/'robust_search_ddt'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    ranking=json.loads((B/'plan_search_ddn/screen_summary.json').read_text())['ranking']
    ks=sorted(r['k'] for r in ranking if r['worst_margin']>=-10000)
    seeds=[919260013,919261002,919261003,919261006]
    tasks=[(k,'teacher','y68v',s,0) for k in ks for s in seeds]
    OUT.mkdir(exist_ok=True)
    import evaluate
    plan={'tasks':tasks,'candidate_hashes':evaluate.snapshot(B/'ddn'),'driver_sha256':evaluate.sha(Path(__file__)),
          'search_driver_sha256':evaluate.sha(B/'search_plans.py'),'status':'development counterexamples; not gate'}
    plan=json.loads(json.dumps(plan));pp=OUT/'plan.json'
    if pp.exists():assert json.loads(pp.read_text())==plan
    else:pp.write_text(json.dumps(plan,indent=2)+'\n')
    output=OUT/'games.jsonl';rows=[json.loads(x) for x in output.read_text().splitlines()] if output.exists() else []
    done={(r['k'],r['seed']) for r in rows};tasks=[t for t in tasks if (t[0],t[3]) not in done]
    print('pending',len(tasks),flush=True)
    for start in range(0,len(tasks),a.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
            fs=[pool.submit(search.game,t) for t in tasks[start:start+a.workers*6]]
            for f in concurrent.futures.as_completed(fs):
                r=f.result();rows.append(r)
                with output.open('a') as out:out.write(json.dumps(r)+'\n')
                print(len(rows),r['k'],r['seed'],round(r['margin']),flush=True)
    ranked=[]
    for k in ks:
        rs=[r for r in rows if r['k']==k]
        ranked.append({'k':k,'wins':sum(r['win'] for r in rs),'games':len(rs),'worst_margin':min(r['margin'] for r in rs),'mean_margin':np.mean([r['margin'] for r in rs])})
    ranked.sort(key=lambda r:(r['wins'],r['worst_margin'],r['mean_margin']),reverse=True)
    (OUT/'summary.json').write_text(json.dumps({'ranking':ranked,'games':len(rows)},indent=2)+'\n');print(json.dumps(ranked[:10]),flush=True)
if __name__=='__main__':main()
