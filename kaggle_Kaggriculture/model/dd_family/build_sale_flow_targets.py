"""Build future exogenous inventory-flow labels without future input features.

Animal products cannot be bought. Their market stock is monotone during market
processing. A post-market quote above $1 proves every own sale added one stock;
otherwise windows with own sales are excluded, avoiding floor-clipping bias.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
B=Path(__file__).resolve().parent;OUT=B/'sale_flow_labels';sys.path.insert(0,str(B/'ddau'));import sale_policy as policy,rules
HORIZONS=[1,4,24]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    OUT.mkdir(exist_ok=True);manifest=json.loads((B/'executed_sale_labels/manifest.json').read_text());rows=[]
    source_rows={s:json.loads((B/s/'training_manifest.json').read_text())['episodes'] for s in ['ddm','dde','ddo']}
    for r in manifest['rows']:
        source=r['source'];k=r['prototype'];row=source_rows[source][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==r['source_sha256'];rep=json.loads(raw)
        data=B/'executed_sale_labels'/source/f'{k:03}.npz';assert sha(data)==r['label_sha256'];z=np.load(data);cfg=rep['configuration'];inv=[];cons=[];params=rules._resolve_market_params(rep['steps'][0][0]['observation']['market'].get('params'))
        for t,step in enumerate(rep['steps']):
            obs=step[0]['observation'];inv.append([obs['market']['inventory'][item] for item in policy.ITEMS])
            if t>=719:continue
            demand=[]
            for item in policy.ITEMS:
                n=0
                if t%max(1,int(cfg.get('townShopSellInterval',4)))==0:
                    n+=sum(2 if len(rules.SHOPS[shop])==1 else 1 for shop in obs['town']['unlocked_shops'] if item in rules.SHOPS[shop])
                if t%max(1,int(cfg.get('townCenterSellInterval',24)))==0:n+=1
                demand.append(n)
            cons.append(demand)
        inv=np.asarray(inv);cons=np.asarray(cons);assert inv.shape==(720,3)
        after_market=inv[1:]+cons;assert np.all(after_market>=inv[:-1])
        safe=np.asarray([[rules.market_price(item,int(after_market[t,j]),params)>1 or z['filled'][t,j]==0 for j,item in enumerate(policy.ITEMS)] for t in range(719)])
        cum_sales=np.vstack([np.zeros(3),np.cumsum(z['filled'],axis=0)]);cum_bad=np.vstack([np.zeros(3),np.cumsum(~safe,axis=0)])
        target=np.zeros((719,3,3),np.float32);valid=np.zeros_like(target,dtype=bool)
        for hi,h in enumerate(HORIZONS):
            n=720-h;target[:n,:,hi]=inv[h:]-inv[:n]-(cum_sales[h:]-cum_sales[:n]);valid[:n,:,hi]=z['eligible'][:n]&(cum_bad[h:]==cum_bad[:n])
            # With self flow removed, only opponent supply minus town demand
            # remains. Any violation indicates clipping or alignment errors.
            cum_cons=np.vstack([np.zeros(3),np.cumsum(cons,axis=0)])
            floor=-(cum_cons[h:]-cum_cons[:n]);assert np.all(target[:n,:,hi][valid[:n,:,hi]]>=floor[valid[:n,:,hi]])
        dest=OUT/source;dest.mkdir(exist_ok=True);np.savez_compressed(dest/f'{k:03}.npz',target=target,valid=valid)
        rows.append({'source':source,'prototype':k,'seed':r['seed'],'feature_data_sha256':r['label_sha256'],'target_sha256':sha(dest/f'{k:03}.npz'),'samples_by_horizon':valid.sum((0,1)).tolist(),'floor_ambiguous_item_turns':int((~safe).sum())})
        if len(rows)%40==0:print('built',len(rows),flush=True)
    result={'episodes':len(rows),'horizons':HORIZONS,'feature_manifest_sha256':sha(B/'executed_sale_labels/manifest.json'),'builder_sha256':sha(Path(__file__)),'samples_by_horizon':np.sum([r['samples_by_horizon'] for r in rows],axis=0).tolist(),'floor_ambiguous_item_turns':sum(r['floor_ambiguous_item_turns'] for r in rows),'rows':rows}
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
if __name__=='__main__':main()
