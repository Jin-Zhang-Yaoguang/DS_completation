#!/usr/bin/env python3
"""用官方和v3派生快引擎核对已有动作带；零候选调用，不产生新独立比赛。"""
import argparse,copy,gzip,importlib.util,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
RUNNER=HERE.parents[1]/'evaluation/run_match_v3.py'


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,action='append',required=True)
    p.add_argument('--game-index',type=int);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    sys.dont_write_bytecode=True;out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    assert HERE==out.parent or HERE in out.parents,'输出须位于本研究目录内'
    assert not (out/'manifest.json').exists(),'拒绝覆盖已冻结重放验证'
    spec=importlib.util.spec_from_file_location('saved_parity_v3',RUNNER);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
    make,rules,fixed,engine=h.import_engines();entries=[];seen=set();sourcefiles={}
    for root in args.run_dir:
        root=root.resolve();m=json.loads((root/'run_manifest.json').read_text());rows=[json.loads(x) for x in (root/'games.jsonl').read_text().splitlines()]
        assert h.sha(m['harness']['path'])==m['harness']['sha256'];h.check_files(m['engine'])
        for f in [root/'run_manifest.json',root/'games.jsonl']:sourcefiles[str(f)]=h.sha(f)
        indices=range(len(rows)) if args.game_index is None else [args.game_index]
        for index in indices:
            game=rows[index];assert game['backend']=='official';key=(game['key'],game['trace']['sha256']);assert key not in seen,'重复源对局'
            seen.add(key);assert h.sha(game['trace']['path'])==game['trace']['sha256'];entries.append((root,index,m,game))
    freeze={'schema':'v125-saved-actions-v3-parity-v1','script_sha256':h.sha(__file__),'runner':{'path':str(RUNNER),'sha256':h.sha(RUNNER)},'engine':engine,
            'sources':sourcefiles,'expected_games':len(entries),'candidate_calls':0,'new_independent_matches':0,'workers':1,
            'interpretation':'同一已有动作轨迹校验；不改变源game status，不生成新candidate回报样本，也不证明适应性重跑同轨迹。'}
    h.write_json(out/'manifest.json',freeze);results=[]
    for root,index,m,g in entries:
        trace=json.load(gzip.open(g['trace']['path']));assert len(trace['actions'])==g['calls']
        if g['status']=='DONE':assert len(trace['actions'])==719
        official=h.Engine('official',trace['seed'],make,fixed);shadow=h.Engine('fast',trace['seed'],make,fixed)
        checks=0;difference=None;compared_steps=0
        for t in range(len(trace['actions'])+1):
            for seat in (0,1):
                a,b=official.observe(seat),shadow.observe(seat)
                for field in h.FIELDS:
                    d=h.first_difference(a.get(field),b.get(field),field)
                    if d:difference={'observation_step':t,'seat':seat,'difference':d};break
                if difference:break
                checks+=1
            if difference:break
            if t==len(trace['actions']):break
            pair=trace['actions'][t];official.step(copy.deepcopy(pair));shadow.step(copy.deepcopy(pair));compared_steps+=1
        terminal_equal=None;rewards_equal=None
        if not difference and g['status']=='DONE':
            terminal_equal=h.snapshot([official.observe(s) for s in (0,1)])==g['terminal'];rewards_equal=official.rewards()==g['rewards']
            if not terminal_equal or not rewards_equal:difference={'kind':'OFFICIAL_SOURCE_TERMINAL_MISMATCH','terminal_equal':terminal_equal,'rewards_equal':rewards_equal}
        row={'source_run':str(root),'source_game_index':index,'source_key':g['key'],'source_status_retained':g['status'],'trace':g['trace'],
             'actions_replayed':compared_steps,'seat_state_pairs_compared':checks,'status':'ERROR' if difference else 'SAVED_TRACE_PARITY_PASS',
             'first_difference':difference,'source_terminal_equal':terminal_equal,'source_rewards_equal':rewards_equal,
             'final_official_cash':[official.observe(s)['farms'][s]['money'] for s in (0,1)],'candidate_calls':0,'new_independent_matches':0}
        results.append(row)
        with (out/'games.jsonl').open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
        if difference:
            with gzip.open(out/'first_difference_states.json.gz','wt') as f:json.dump({'official':[official.observe(s) for s in (0,1)],'fast':[shadow.observe(s) for s in (0,1)]},f)
            break
    h.check_files(engine)
    for path,value in sourcefiles.items():assert h.sha(path)==value,'源文件漂移'
    assert h.sha(RUNNER)==freeze['runner']['sha256']
    summary={'status':'COMPLETE_PASS' if len(results)==len(entries) and all(r['status']=='SAVED_TRACE_PARITY_PASS' for r in results) else 'INCOMPLETE_OR_ERROR',
             'expected_games':len(entries),'audited_games':len(results),'parity_passed_games':sum(r['status']=='SAVED_TRACE_PARITY_PASS' for r in results),
             'saved_action_steps_replayed':sum(r['actions_replayed'] for r in results),'candidate_calls':0,'new_independent_matches':0,'source_files_unchanged':True}
    h.write_json(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2));sys.exit(0 if summary['status']=='COMPLETE_PASS' else 2)


if __name__=='__main__':main()
