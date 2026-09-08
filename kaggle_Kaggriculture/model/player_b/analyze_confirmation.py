"""按随机种子聚类的父子配对分析；不把双席位当独立样本。"""
import json,random,statistics,math,argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent

def quant(x,p):
 s=sorted(x);i=(len(s)-1)*p;a=int(i);b=min(a+1,len(s)-1);return s[a]+(s[b]-s[a])*(i-a)

def analyze(run,candidate,parent):
 rows=[json.loads(l) for l in (run/'games.jsonl').read_text().splitlines()]
 assert all(r['status']=='DONE' and r['calls']==719 for r in rows)
 keys=[(r['candidate'],r['opponent'],r['seed'],r['seat']) for r in rows];assert len(keys)==len(set(keys))
 index={k:r for k,r in zip(keys,rows)}
 opponents=sorted(set(r['opponent'] for r in rows if r['candidate']==parent))
 seeds=sorted(set(r['seed'] for r in rows));diffs=[];cash=[];flips={'positive':0,'negative':0,'unchanged':0}
 for seed in seeds:
  d=[];m=[]
  for opp in opponents:
   for seat in (0,1):
    a=index[candidate,opp,seed,seat];b=index[parent,opp,seed,seat]
    z=a['win']-b['win'];d.append(z);m.append(a['margin']-b['margin'])
    flips['positive' if z>0 else 'negative' if z<0 else 'unchanged']+=1
  diffs.append(statistics.mean(d));cash.append(statistics.mean(m))
 rng=random.Random(91452);draws=[];mdraws=[]
 for _ in range(20000):
  ids=rng.choices(range(len(seeds)),k=len(seeds));draws.append(statistics.mean(diffs[i] for i in ids));mdraws.append(statistics.mean(cash[i] for i in ids))
 seat_rates={}
 for opp in sorted(set(r['opponent'] for r in rows if r['candidate']==candidate)):
  seat_rates[opp]={str(s):statistics.mean(r['win'] for r in rows if r['candidate']==candidate and r['opponent']==opp and r['seat']==s) for s in (0,1)}
 ci=[quant(draws,.025),quant(draws,.975)]
 result={'candidate':candidate,'parent':parent,'cluster':'seed; opponent/seat paired within each seed','independent_seed_clusters':len(seeds),'paired_opponents':opponents,'paired_games':len(seeds)*2*len(opponents),'pure_winrate_delta':statistics.mean(diffs),'delta_95ci':ci,'mean_margin_delta':statistics.mean(cash),'mean_margin_delta_95ci':[quant(mdraws,.025),quant(mdraws,.975)],'flips':flips,'seat_winrates':seat_rates,'complete_games':len(rows),'error_count':0,'local_improvement_gate':ci[0]>0 and all(v>=.5 for rr in seat_rates.values() for v in rr.values()),'gold_status':'NOT_ESTABLISHED','online_submitted':False}
 (run/'analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',default='b2-confirmation');p.add_argument('--candidate',default='b2');p.add_argument('--parent',default='v54d');a=p.parse_args();analyze(HERE/'runs'/a.run,a.candidate,a.parent)
