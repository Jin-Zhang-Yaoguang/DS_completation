#!/usr/bin/env python3
"""串行重放已完成的来源批次，候选调用为0。"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ANALYZER_SHA='cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output-prefix',required=True);args=p.parse_args()
    assert '/' not in args.output_prefix and '..' not in args.output_prefix
    run=args.run_dir.resolve();rows=[json.loads(z) for z in (run/'games.jsonl').read_text().splitlines()]
    m=json.load(open(run/'run_manifest.json'));assert len(rows)==len(m['seeds'])*len(m['seats'])
    assert all(r['status']=='DONE' and r['calls']==719 for r in rows)
    assert len({r['key'] for r in rows})==len(rows)
    analyzer=HERE/'analyze_trace.py';derive=HERE/'derive_findings.py';assert sha(analyzer)==ANALYZER_SHA
    jobfile=HERE/(args.output_prefix+'_batch_manifest.json')
    if jobfile.exists():raise RuntimeError('批次清单已存在，拒绝覆盖')
    jobs=[{'index':i,'seed':r['seed'],'seat':r['candidate_seat'],'key':r['key'],'output_dir':str(HERE/f'{args.output_prefix}_game{i}')} for i,r in enumerate(rows)]
    manifest={'source_run_dir':str(run),'games_sha256':sha(run/'games.jsonl'),'source_manifest_sha256':sha(run/'run_manifest.json'),
              'analyzer_sha256':ANALYZER_SHA,'derive_sha256':sha(derive),'batch_script_sha256':sha(__file__),'workers':1,'candidate_calls':0,'jobs':jobs}
    dump(jobfile,manifest)
    for job in jobs:
        assert sha(run/'games.jsonl')==manifest['games_sha256']
        out=Path(job['output_dir']);out.mkdir(parents=True,exist_ok=True)
        with open(out/'replay_stdout.txt','w') as log:
            subprocess.run([sys.executable,str(analyzer),'--run-dir',str(run),'--game-index',str(job['index']),'--output',str(out)],stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run([sys.executable,str(derive),str(out)],stdout=subprocess.DEVNULL,check=True)
        print(json.dumps({'completed':job['index']+1,'total':len(jobs),'seed':job['seed'],'seat':job['seat'],'output':str(out)}),flush=True)
    assert sha(run/'games.jsonl')==manifest['games_sha256']
    dump(HERE/(args.output_prefix+'_batch_complete.json'),{'manifest_sha256':sha(jobfile),'completed':len(jobs),'candidate_calls':0,
                                                         'validation_files':{j['output_dir']:sha(Path(j['output_dir'])/'validation.json') for j in jobs}})

if __name__=='__main__':main()
