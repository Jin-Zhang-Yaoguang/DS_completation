#!/usr/bin/env python3
"""只重放保存的失败动作带，定位官方与快引擎首差；不调用候选。"""
import argparse,copy,gzip,hashlib,importlib.util,inspect,json,sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def load(path):
    spec=importlib.util.spec_from_file_location('failure_harness',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    sys.dont_write_bytecode=True;out=args.output;out.mkdir(parents=True,exist_ok=True);assert not (out/'manifest.json').exists()
    m=json.loads((args.run_dir/'run_manifest.json').read_text());g=json.loads((args.run_dir/'games.jsonl').read_text().splitlines()[0])
    assert sha(g['trace']['path'])==g['trace']['sha256'];assert sha(m['harness']['path'])==m['harness']['sha256']
    trace=json.load(gzip.open(g['trace']['path']));h=load(m['harness']['path']);h.check_files(m['engine']);make,rules,fast,engine=h.import_engines()
    assert engine['composite_sha256']==m['engine']['composite_sha256']
    dump(out/'manifest.json',{'source_trace':g['trace'],'source_manifest_sha256':sha(args.run_dir/'run_manifest.json'),'harness':m['harness'],'engine':m['engine'],
                            'script_sha256':sha(__file__),'candidate_calls':0,'new_matches':0,'saved_actions':len(trace['actions'])})
    official=h.Engine('official',trace['seed'],make,fast);shadow=h.Engine('fast',trace['seed'],make,fast)
    original=rules._commit_unit;commits=[];step=0;prior_interpreter=official.g.interpreter;farms={}
    def bound(state,env,logs=None):
        farms.update({id(f):i for i,f in enumerate(state[0].observation.farms)})
        return prior_interpreter(state,env)
    official.g.interpreter=bound
    def commit(op,item,price,farm,private,market,*a,**kw):
        caller=inspect.currentframe().f_back;money=farm['money'];inv=market['inventory'].get(item)
        result=original(op,item,price,farm,private,market,*a,**kw)
        if step==len(trace['actions'])-1:
            commits.append({'action_step':step,'seat':farms[id(farm)],'order_index':caller.f_locals.get('i'),'op':op,'item':item,'quoted_price':price,
                            'market_inventory_at_commit_before':inv,'market_inventory_after':market['inventory'].get(item),'success':result,
                            'money_before':money,'money_after':farm['money'],'money_delta':farm['money']-money})
        return result
    rules._commit_unit=commit
    first=None
    try:
        for step,pair in enumerate(trace['actions']):
            before=[official.observe(s) for s in (0,1)];before_fast=[shadow.observe(s) for s in (0,1)]
            for s in (0,1):
                for field in h.FIELDS:assert h.first_difference(before[s].get(field),before_fast[s].get(field),field) is None
            official.step(copy.deepcopy(pair));shadow.step(copy.deepcopy(pair));after=[official.observe(s) for s in (0,1)];after_fast=[shadow.observe(s) for s in (0,1)]
            differences=[]
            for s in (0,1):
                for field in h.FIELDS:
                    diff=h.first_difference(after[s].get(field),after_fast[s].get(field),field)
                    if diff:differences.append({'seat':s,'difference':diff})
            if differences:
                first={'observation_step':step+1,'action_step':step,'source_failure':g['errors'],'differences':differences,'actions':pair,
                       'official_cash_before':[o['farms'][s]['money'] for s,o in enumerate(before)],
                       'official_cash_after':[o['farms'][s]['money'] for s,o in enumerate(after)],
                       'fast_cash_after':[o['farms'][s]['money'] for s,o in enumerate(after_fast)]}
                with gzip.open(out/'first_difference_states.json.gz','wt') as f:json.dump({'official_before':before,'fast_before':before_fast,'official_after':after,'fast_after':after_fast},f)
                break
        assert first,'保存动作未复现源失败'
    finally:rules._commit_unit=original;official.g.interpreter=prior_interpreter
    dump(out/'first_difference.json',first);dump(out/'official_commits_at_failure.json',commits)
    h.check_files(m['engine']);assert sha(m['harness']['path'])==m['harness']['sha256']
    dump(out/'validation.json',{'candidate_calls':0,'new_matches':0,'all_before_states_identical':True,'source_failure_reproduced':True,'source_and_engine_unchanged':True})
    print(json.dumps(first,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
