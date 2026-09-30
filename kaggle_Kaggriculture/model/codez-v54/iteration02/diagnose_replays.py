"""Describe losses without treating a loss-enriched replay sample as a win-rate estimate."""
from pathlib import Path
import json,collections
P=Path(__file__).resolve().parent
reg={r['episode_id']:r for r in json.loads((P/'replay_registry.json').read_text())}
rows={}
for name in ['historical_reproduction','counterfactual_baselines','counterfactual_shadow_v005']:
    summary=json.loads((P/f'{name}.summary.json').read_text());assert summary['complete'] and not summary['errors']
    for line in (P/f'{name}.jsonl').read_text().splitlines():
        r=json.loads(line);assert r['status']=='ok';v=r['job'].get('agent','history');rows[(r['job']['episode_id'],v)]=r
out={'sample':'26 selected losses plus 24 controls; not an unbiased online population','n':len(reg),'episodes':[]}
for eid,meta in reg.items():
    h=rows[(eid,'history')];a=rows[(eid,'versions/v003/main.py')];b=rows[(eid,'versions/v005/main.py')];seat=meta['seat']
    prev=0;windows=[]
    for point in h['timeline']:
        margin=point['cash'][seat]-point['cash'][1-seat];windows.append({'end_step':point['step'],'cash_margin':margin,'margin_change':margin-prev});prev=margin
    top=sorted(windows,key=lambda x:x['margin_change'])[:3]
    out['episodes'].append(dict(episode_id=eid,opponent=meta['opponent_name'],opponent_submission=meta['opponent_submission_id'],live_margin=meta['live_margin'],r14_tape_margin=a['margin'],v005_tape_margin=b['margin'],v005_vs_r14_delta=b['margin']-a['margin'],identified_turns=b['telemetry']['identified_turns'],last_models=b['telemetry']['survivors'],eliminated=b['telemetry']['eliminated'],largest_cash_gap_widenings=top))
for loss in [True,False]:
    g=[r for r in out['episodes'] if (r['live_margin']<0)==loss]
    out['losses' if loss else 'controls']={'n':len(g),'v005_tape_wins':sum(r['v005_tape_margin']>0 for r in g),'r14_tape_wins':sum(r['r14_tape_margin']>0 for r in g),'v005_vs_r14_margin_delta':sum(r['v005_vs_r14_delta'] for r in g),'zero_identified_turns':sum(r['identified_turns']==0 for r in g)}
(P/'replay_diagnosis.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print(out['losses']);print(out['controls'])
