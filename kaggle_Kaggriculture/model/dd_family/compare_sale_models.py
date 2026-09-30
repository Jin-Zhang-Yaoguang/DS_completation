"""Matched competition and public-inventory forecast checks for sale models."""
from pathlib import Path
import gzip,json,sys
import numpy as np
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddav'));import rules

def main():
    panels={'ddam':['broad01'],'ddat':['dev01','expand01'],'ddau':['dev01','expand01'],'ddav':['broad01']};data={};summary=[]
    for version,runs in panels.items():
        rows={}
        for run in runs:
            p=B/version/'runs'/run;s=json.loads((p/'summary.json').read_text());plan=json.loads((p/'plan.json').read_text());assert s['completed']==plan['expected']
            for path in (p/'games').glob('*.gz'):
                r=json.load(gzip.open(path,'rt'));key=(r['opponent'],r['seed'],r['seat']);assert key not in rows;rows[key]=r
        data[version]=rows
    keys=set(data['ddam']);assert len(keys)==40 and all(set(rows)==keys for rows in data.values())
    for version,rows in data.items():
        base=data['ddam'];rs=list(rows.values());summary.append({'version':version,'games':len(rs),'wins':sum(r['win'] for r in rs),'mean_margin':float(np.mean([r['margin'] for r in rs])),'own_cash_delta':float(np.mean([r['own_cash']-base[k]['own_cash'] for k,r in rows.items()])),'opponent_cash_delta':float(np.mean([r['opponent_cash']-base[k]['opponent_cash'] for k,r in rows.items()])),'win_to_loss':sum(base[k]['win'] and not r['win'] for k,r in rows.items()),'loss_to_win':sum(not base[k]['win'] and r['win'] for k,r in rows.items()),'max_seconds':max(r['max_seconds'] for r in rs)})
    samples={item:[] for item in ['EGG','MILK','WOOL']};held_outside_consumption=0;actual_hold=0;requested_hold=0
    for r in data['ddav'].values():
        shops={day['day']:day['shops'] for day in r['daily']}
        for t in range(718):
            current=r['trace'][t];nxt=r['trace'][t+1];diag=current['diagnostic'];market=diag['market_inventory']
            for item,pred in diag['flow'].items():
                if pred['hold']:
                    requested_hold+=1;held_outside_consumption+=int(t%4!=0)
                sold=sum(o[2] for o in current['action']['market'] if o[0]=='SELL' and o[1]==item)
                actual_hold+=int(pred['hold'] and sold<pred['stock'])
                consumption=int(t%24==0)
                if t%4==0:consumption+=sum(2 if len(rules.SHOPS[s])==1 else 1 for s in shops[t//24] if item in rules.SHOPS[s])
                after=nxt['diagnostic']['market_inventory'][item]+consumption
                if rules.market_price(item,after)<=1:continue
                opponent=after-market[item]-sold
                assert 0<=opponent<=100,(r['seed'],r['seat'],t,item,opponent)
                quantiles=pred['opponent_sale_quantiles'];samples[item].append({'actual':opponent,'median':quantiles[2],'low':quantiles[0],'high':quantiles[-1]})
    assert held_outside_consumption==0
    calibration={}
    for item,rows in samples.items():
        calibration[item]={'samples':len(rows),'median_mae':float(np.mean([abs(r['actual']-r['median']) for r in rows])),'zero_baseline_mae':float(np.mean([r['actual'] for r in rows])),'empirical_p10_p90_coverage':float(np.mean([r['low']<=r['actual']<=r['high'] for r in rows]))}
    result={'panel':'Same 20 development seeds, y68v, both seats; no gate or confirmation.','summary':summary,'forecast_calibration':calibration,'forecast_scope':'Actual opponent inventory contribution inferred from observed public stock and own requests only when the market does not touch the $1 floor. Samples are on-policy development, not new holdout.','hold_requests':requested_hold,'actual_hold_item_turns':actual_hold,'holds_without_town_consumption':held_outside_consumption}
    (B/'comparison_sale_models.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
