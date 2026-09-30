"""Match complete joint-label experiments by opponent, seed and seat."""
from pathlib import Path
import gzip,json
import numpy as np
B=Path(__file__).resolve().parent

def read(version,runs):
    rows={};provenance={}
    for run in runs:
        root=B/version/'runs'/run
        plan=json.loads((root/'plan.json').read_text());summary=json.loads((root/'summary.json').read_text())
        assert summary['completed']==plan['expected']
        provenance[run]={'hashes':plan['hashes'],'seeds':plan['seeds']}
        for p in (root/'games').glob('*.gz'):
            r=json.load(gzip.open(p,'rt'));key=(r['opponent'],r['seed'],r['seat']);assert key not in rows
            rows[key]=r
    return rows,provenance

def main():
    panels={'ddam':['broad01'],'ddar':['dev01','expand01'],'ddas':['broad01']}
    data={};provenance={}
    for v,runs in panels.items():data[v],provenance[v]=read(v,runs)
    keys=set(data['ddam']);assert all(set(rows)==keys for rows in data.values())
    assert len(keys)==40
    summary=[];matched=[]
    for version,rows in data.items():
        margins=[r['margin'] for r in rows.values()];base=data['ddam']
        summary.append({'version':version,'games':len(rows),'wins':sum(r['win'] for r in rows.values()),'mean_margin':float(np.mean(margins)),'worst_margin':min(margins),'mean_margin_delta_vs_ddam':float(np.mean([r['margin']-base[k]['margin'] for k,r in rows.items()])),'mean_own_cash_delta':float(np.mean([r['own_cash']-base[k]['own_cash'] for k,r in rows.items()])),'mean_opponent_cash_delta':float(np.mean([r['opponent_cash']-base[k]['opponent_cash'] for k,r in rows.items()])),'win_to_loss':sum(base[k]['win'] and not r['win'] for k,r in rows.items()),'loss_to_win':sum(not base[k]['win'] and r['win'] for k,r in rows.items())})
    for op,seed,seat in sorted(keys):
        matched.append({'opponent':op,'seed':seed,'seat':seat,'models':{v:{f:rows[op,seed,seat][f] for f in ['own_cash','opponent_cash','margin','win']} for v,rows in data.items()}})
    result={'scope':'20 development seeds, both seats, y68v only; no qualification claim. Different farm states can change subsequent shop RNG.','summary':summary,'matched':matched,'provenance':provenance}
    (B/'comparison_joint_allocators.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
