"""Check quote lockstep, order priority and $1 supply clipping against engine."""
from pathlib import Path
import contextlib,copy,importlib,io,json,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddav'))
import competitive_sale as c,rules
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    from kaggle_environments import make
    engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')

def main():
    env=make('kaggriculture',configuration={'seed':919260010});cases=0
    for item in ['EGG','MILK','WOOL']:
        for inventory in [9950,10000,10070,10100]:
            for own,other in [(1,1),(23,17),(100,100)]:
                for alignment in ['joint','ours_first','other_first']:
                    env.reset(2);env.state[0].observation.market.inventory[item]=inventory
                    for player,n in enumerate([own,other]):
                        env.state[0].observation.farms[player]['money']=0
                        env.state[player].observation.private['shed']={item:n}
                        orders=[['SELL',item,n]]
                        if (alignment=='ours_first' and player==1) or (alignment=='other_first' and player==0):orders.insert(0,['BUY_SEED','WHEAT',0])
                        env.state[player].action={'market':orders}
                    engine._process_market(env.state,env)
                    actual=[env.state[0].observation.farms[player]['money'] for player in [0,1]]
                    if alignment=='joint':expected=list(c.joint(item,inventory,own,other,rules.MARKET_PARAMS))
                    elif alignment=='ours_first':
                        ours,after=c.sale(item,inventory,own,rules.MARKET_PARAMS);theirs,_=c.sale(item,after,other,rules.MARKET_PARAMS);expected=[ours,theirs]
                    else:
                        theirs,after=c.sale(item,inventory,other,rules.MARKET_PARAMS);ours,_=c.sale(item,after,own,rules.MARKET_PARAMS);expected=[ours,theirs]
                    assert actual==expected,(item,inventory,own,other,alignment,actual,expected);cases+=1
    result={'cases':cases,'official_market_cash_parity':True,'scope':'Current-turn market mechanics only; future opponent quantity forecasts and order alignment probabilities remain model assumptions.'}
    (B/'audit_competitive_sale.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
