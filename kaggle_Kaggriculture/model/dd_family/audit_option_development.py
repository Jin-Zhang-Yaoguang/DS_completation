"""Audit immutable complete development games and summarize option execution."""
from pathlib import Path
import collections,gzip,hashlib,json,sys
B=Path(__file__).resolve().parent
for version in sys.argv[1:]:
 D=B/version;run=D/'runs/development01';plan=json.loads((run/'plan.json').read_text());summary=json.loads((run/'summary.json').read_text())
 assert summary['completed']==summary['expected']==plan['expected']
 assert all(hashlib.sha256((D/p).read_bytes()).hexdigest()==h for p,h in plan['hashes'].items())
 stats=collections.Counter();rows=[]
 for p in sorted((run/'games').glob('*.json.gz')):
  with gzip.open(p,'rt') as f:g=json.load(f)
  assert g['steps']==len(g['trace'])==719 and g['status']=='DONE' and g['overage_remaining']>=0
  stats.update(g['stats']);rows.append({k:g[k] for k in ['seed','seat','own_cash','opponent_cash','margin','win','max_seconds','p99_seconds','overage_remaining']})
 result={'version':version,'games':len(rows),'wins':sum(r['win'] for r in rows),'mean_margin':sum(r['margin'] for r in rows)/len(rows),'mean_cash':sum(r['own_cash'] for r in rows)/len(rows),'hashes_unchanged':True,'all_budget_nonnegative':True,'total_stats':dict(stats),'rows':rows}
 (B/'diagnostics'/f'{version}_development_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
