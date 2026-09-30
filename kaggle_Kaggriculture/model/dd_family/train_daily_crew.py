"""Train daily staffing on immutable official teacher replays, never opponent actions."""
from pathlib import Path
import argparse,copy,hashlib,json,sys,time
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error
from train_source_options import export
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');a=ap.parse_args();d=B/a.version
    assert not (d/'daily_crew.npz').exists(),'Train changed policies in a new version'
    sys.path.insert(0,str(d));import crew_features as C,tree_runtime
    plan=json.loads((d/'source_manifest.json').read_text());cfg=json.loads((d/'config.json').read_text())
    rows=plan['rows'];pools={s:{'x':[],'y':[],'seed':[],'day':[]} for s in ['train','validation']};started=time.perf_counter()
    audits={r['source_sha256']:r for r in json.loads((B/'task_policy_data/ddbo/manifest.json').read_text())['rows']}
    for j,row in enumerate(rows):
        assert row['split'] in pools;path=Path(row['path']);assert sha(path)==row['sha256']
        audit=audits[row['sha256']];assert audit['source_exact_719_states'] and audit['source_seed']==row['seed']
        rep=json.loads(path.read_text());seat=int(row['seat']);pool=pools[row['split']]
        assert len(rep['steps'])==720 and rep['module_version']=='1.32.7'
        for day in range(30):
            t=day*24;obs=copy.deepcopy(rep['steps'][t][0]['observation']);obs.update(copy.deepcopy(rep['steps'][t][seat]['observation']));obs.update(step=t,player=seat)
            # Exclude the next day's reset. Day 29 includes final state 719.
            states=rep['steps'][t:min(t+24,720)]
            sizes=[len(s[0]['observation']['farms'][seat]['hands']) for s in states]
            pool['x'].append(C.encode(obs));pool['y'].append(max(sizes));pool['seed'].append(row['seed']);pool['day'].append(day)
        if (j+1)%20==0:print('sources',j+1,'/',len(rows),flush=True)
    assert not set(pools['train']['seed'])&set(pools['validation']['seed'])
    for split,pool in pools.items():
        assert len(set(pool['seed']))==plan['split_counts'][split]
        pools[split]={k:np.asarray(v,np.float32 if k=='x' else np.int64) for k,v in pool.items()}
    out=B/'daily_crew_data'/a.version;out.mkdir(parents=True,exist_ok=True)
    for split,pool in pools.items():np.savez_compressed(out/f'{split}.npz',**pool)
    tr,va=pools['train'],pools['validation'];model=ExtraTreesRegressor(n_estimators=cfg['crew_trees'],max_depth=cfg['crew_depth'],min_samples_leaf=cfg['crew_min_leaf'],max_features=1.,n_jobs=4,random_state=cfg['seed'])
    model.fit(tr['x'],tr['y']);export(model,d/'daily_crew.npz');runtime=tree_runtime.Model(d/'daily_crew.npz')
    predicted=model.predict(va['x']);err=float(np.max(np.abs(predicted-runtime.predict(va['x']))));assert err<1e-6
    median=float(np.median(tr['y']));report={'version':a.version,'test_used':False,'source_manifest_sha256':sha(d/'source_manifest.json'),'features':int(tr['x'].shape[1]),'algorithm':'ExtraTrees regression from day-start visible state to actual teacher daily maximum crew; behavioral supervision, not optimal staffing or reinforcement learning.','target_boundary':'Maximum hands in observation states [24*day, min(24*day+24,720)); next day reset excluded.','validation_mae':mean_absolute_error(va['y'],predicted),'validation_median_baseline_mae':mean_absolute_error(va['y'],np.full_like(predicted,median)),'train_median':median,'validation_r2':model.score(va['x'],va['y']),'export_max_abs_error':err,'seconds':time.perf_counter()-started,'splits':{}}
    for s,p in pools.items():
        report['splits'][s]={'sources':len(set(p['seed'])),'days':len(p['y']),'crew_min':int(p['y'].min()),'crew_max':int(p['y'].max()),'crew_quantiles':np.quantile(p['y'],[0,.25,.5,.75,1]).tolist(),'sha256':sha(out/f'{s}.npz')}
    report['hashes']={p.name:sha(p) for p in d.iterdir() if p.suffix in ['.py','.npz','.json']}
    (d/'crew_training_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
