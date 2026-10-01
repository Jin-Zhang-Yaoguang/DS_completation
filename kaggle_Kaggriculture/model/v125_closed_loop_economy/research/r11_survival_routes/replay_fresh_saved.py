#!/usr/bin/env python3
"""单进程顺序重放已完整保存的动作；候选调用和新比赛均为零。"""
import argparse,contextlib,hashlib,json,runpy,sys,traceback
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if p.name=='v125_closed_loop_economy')
ANALYZER=ROOT/'research/mechanism_analysis/analyze_trace.py'
ANALYZER_SHA='cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,action='append',required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'manifest.json').exists()
    assert sha(ANALYZER)==ANALYZER_SHA
    sources={};jobs=[];keys=set()
    for run in args.run_dir:
        run=run.resolve();summary=json.loads((run/'summary.json').read_text());assert summary['status']=='COMPLETE' and summary['done_games']==6 and summary['all_parity_pass'] is True
        manifest=json.loads((run/'run_manifest.json').read_text());rows=[json.loads(x) for x in (run/'games.jsonl').read_text().splitlines()]
        assert len(rows)==6 and {(r['seed'],r['candidate_seat']) for r in rows}=={(s,t) for s in [1950906101,1950906102,1950906103] for t in [0,1]}
        for n in ['run_manifest.json','games.jsonl','summary.json']:sources[str(run/n)]=sha(run/n)
        for name in ['candidate','opponent','engine']:
            for path,digest in manifest[name]['files'].items():assert sha(path)==digest;sources[path]=digest
        sources[manifest['harness']['path']]=manifest['harness']['sha256'];assert sha(manifest['harness']['path'])==manifest['harness']['sha256']
        for index,r in enumerate(rows):
            assert r['key'] not in keys;keys.add(r['key'])
            assert r['status']=='DONE' and r['calls']==719 and r['parity_pass'] is True and r['errors']==[]
            assert sha(r['trace']['path'])==r['trace']['sha256'];sources[r['trace']['path']]=r['trace']['sha256']
            jobs.append({'run_dir':str(run),'game_index':index,'seed':r['seed'],'seat':r['candidate_seat'],'source_key':r['key'],'output':str(out/run.name/f"seed{r['seed']}_seat{r['candidate_seat']}")})
    dump(out/'manifest.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),'driver_sha256':sha(__file__),'analyzer_sha256':ANALYZER_SHA,'sources':sources,'jobs':jobs,
                              'candidate_calls':0,'new_independent_matches':0,'planned_saved_action_replay_steps':719*len(jobs),'workers':1})
    results=[];(out/'logs').mkdir(exist_ok=True)
    for i,job in enumerate(jobs):
        target=Path(job['output']);target.mkdir(parents=True,exist_ok=True);before=list(sys.argv)
        try:
            sys.argv=[str(ANALYZER),'--run-dir',job['run_dir'],'--output',job['output'],'--game-index',str(job['game_index'])]
            log=out/'logs'/f"{Path(job['run_dir']).name}_seed{job['seed']}_seat{job['seat']}.txt"
            with log.open('w') as f,contextlib.redirect_stdout(f):runpy.run_path(str(ANALYZER),run_name='__main__')
            validation=json.loads((target/'validation.json').read_text());assert validation['saved_actions_replayed']==719 and validation['agent_calls']==0
            results.append({**job,'status':'VERIFIED','validation_sha256':sha(target/'validation.json')})
            print(f"{i+1}/{len(jobs)} VERIFIED {Path(job['run_dir']).name} seed{job['seed']} seat{job['seat']}",flush=True)
        except BaseException as exc:
            (target/'failure.txt').write_text(traceback.format_exc());results.append({**job,'status':'ERROR','error':repr(exc)});dump(out/'results.json',results);raise
        finally:sys.argv=before
        dump(out/'results.json',results)
    assert sha(ANALYZER)==ANALYZER_SHA and all(sha(p)==v for p,v in sources.items())
    dump(out/'validation.json',{'verified_games':len(results),'saved_actions_replayed':719*len(results),'candidate_calls':0,'new_independent_matches':0,'source_files_unchanged':True,
                               'analyzer_unchanged':True,'workers':1})

if __name__=='__main__':main()
