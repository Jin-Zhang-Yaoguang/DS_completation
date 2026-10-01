"""Actual-fill cash ledger from official historical replay, never from requested quantities."""
import sys,json,collections,importlib,concurrent.futures,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from research_official import OfficialGame
ROOT=Path(__file__).resolve().parent

def one(eid):
    out={'episode_id':eid,'status':'error'}
    try:
        tape=json.loads((ROOT/'tapes'/f'{eid}.json').read_text());game=OfficialGame(tape['seed'])
        module=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
        names=['_process_market','_commit_unit','_do_hire','_do_buy_land'];saved={n:getattr(module,n) for n in names}
        current={'step':0,'players':{}};ledger=collections.defaultdict(lambda:[0,0.0]);events=[]
        def record(farm,op,item,qty,cash):
            player=current['players'][id(farm)];key=(player,current['step']//24,op,item)
            ledger[key][0]+=qty;ledger[key][1]+=cash
        def market(states,env):
            current['players']={id(f):i for i,f in enumerate(states[0].observation.farms)}
            return saved['_process_market'](states,env)
        def commit(op,item,price,farm,private,market,shed_capacity=100):
            before=farm['money'];ok=saved['_commit_unit'](op,item,price,farm,private,market,shed_capacity)
            if ok:record(farm,op,item,1,farm['money']-before)
            return ok
        def hire(farm,private,board_size,mult=1):
            before=farm['money'];n=len(farm['hands']);result=saved['_do_hire'](farm,private,board_size,mult)
            if len(farm['hands'])>n:record(farm,'HIRE','HAND',1,farm['money']-before)
            return result
        def land(farm,board_size):
            before=farm['money'];n=len(farm['unlocked_quadrants']);result=saved['_do_buy_land'](farm,board_size)
            if len(farm['unlocked_quadrants'])>n:record(farm,'BUY_LAND','LAND',1,farm['money']-before)
            return result
        module._process_market=market;module._commit_unit=commit;module._do_hire=hire;module._do_buy_land=land
        try:
            initial=[f['money'] for f in game.observe(0)['farms']]
            for t,acts in enumerate(tape['actions']):current['step']=t;game.step(*acts)
        finally:
            for n,fn in saved.items():setattr(module,n,fn)
        final=[game.reward(i) for i in [0,1]];assert final==tape['rewards']
        cash=[initial[p]+sum(v[1] for k,v in ledger.items() if k[0]==p) for p in [0,1]]
        assert cash==final,('cash ledger does not reconcile',cash,final)
        rows=[dict(player=k[0],day=k[1],operation=k[2],item=k[3],executed_units=v[0],cash_change=v[1]) for k,v in sorted(ledger.items())]
        out.update(status='ok',seat=tape['seat'],opponent=tape['opponent_name'],initial=initial,final=final,ledger_reconciled=True,ledger=rows,final_private=[game.observe(p)['private'] for p in [0,1]],replay_sha256=tape['replay_sha256'])
    except Exception:out['error']=traceback.format_exc()
    return out
if __name__=='__main__':
    dest=ROOT/'replay_ledger.jsonl';assert not dest.exists()
    registry=json.loads((ROOT/'replay_registry.json').read_text());rows=[]
    with dest.open('w') as f,concurrent.futures.ProcessPoolExecutor(3) as pool:
        for row in pool.map(one,[r['episode_id'] for r in registry]):
            rows.append(row);f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
            if row['status']!='ok':print(row['error'][-2000:],flush=True)
            if len(rows)%10==0:print('ledgers',len(rows),'/',len(registry),flush=True)
    summary=dict(complete=len(rows)==len(registry),errors=sum(r['status']!='ok' for r in rows),runner_sha256=research.digest(Path(__file__)),result_sha256=research.digest(dest))
    (ROOT/'replay_ledger.summary.json').write_text(json.dumps(summary,indent=2));assert not summary['errors']
