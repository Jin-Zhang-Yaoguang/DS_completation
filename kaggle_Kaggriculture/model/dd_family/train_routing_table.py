"""Fit a deliberately small day-conditioned value table from completed continuations."""
from pathlib import Path
import argparse,hashlib,json,shutil
import numpy as np
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');ap.add_argument('--run',default='priority_pilot');a=ap.parse_args();source=B/'routing_value'/a.run;plan=json.loads((source/'plan.json').read_text());summary=json.loads((source/'summary.json').read_text());assert summary['completed']==summary['expected']==len(plan['tasks'])
    rows=[json.loads((source/f'{s}_{seat}_{d}_{m}.json').read_text()) for _,s,seat,d,m in plan['tasks']]
    seeds=sorted({r['seed'] for r in rows});days=sorted({r['day'] for r in rows});assert set(seeds)==set(range(919260010,919260014)) and len(rows)==len(seeds)*len(days)*4
    for day in days:
        for seed in seeds:
            group=[r for r in rows if r['day']==day and r['seed']==seed];assert {r['mode'] for r in group}=={0,1,2,3};first=group[0];assert all(r['features']==first['features'] for r in group)
            neutral=next(r for r in group if r['mode']==0);assert neutral['neutral_continuation_exact'] and neutral['changed_action_steps']==neutral['margin_delta']==neutral['cash_delta']==0
    candidate=B/'routing_value/source_candidate';assert all(sha(candidate/p)==h for p,h in plan['candidate_hashes'].items())
    parent=B/'ddbs';parent_plan=json.loads((parent/'runs/development01/plan.json').read_text());assert all(sha(parent/p)==h for p,h in parent_plan['hashes'].items())
    d=B/a.version;assert not d.exists(),'Do not overwrite candidates';d.mkdir()
    for p in parent.iterdir():
        if p.suffix in ['.py','.npz'] or p.name=='feature_schema.json':shutil.copy2(p,d/p.name)
    shutil.copy2(candidate/'route_modes.py',d/'route_modes.py')
    values=np.zeros((30,4),np.float64);counts=np.zeros((30,4),np.int32)
    for day in days:
        for mode in range(4):
            rs=[r for r in rows if r['day']==day and r['mode']==mode];values[day,mode]=np.mean([r['margin_delta'] for r in rs]);counts[day,mode]=len(rs)
    np.save(d/'route_values.npy',values)
    config=json.loads((parent/'config.json').read_text());config.update(version=a.version,parent='ddbs',method='Replay-distilled service ranking with simulator-calibrated daily routing table',value_label='Mean terminal competitive margin delta against unchanged continuation, one-day intervention.',value_scope='Only day 3/10/20 have observed values; all other days retain teacher ranking. Four training seeds, no claim of generalization.',value_validation_seeds=[919261001,919261002,919261003,919261004]);(d/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    p=d/'main.py';text=p.read_text().replace('idle_services as I','idle_services as I,route_modes as R').replace('        self.goals={};self.previous={};self.day=-1;',"        self.route_values=np.load(B/'route_values.npy');self.route_mode=0\n        self.goals={};self.previous={};self.day=-1;")
    text=text.replace('if self.day!=day:self.goals={};self.previous={};self.day=day','if self.day!=day:self.goals={};self.previous={};self.day=day;self.route_mode=int(np.argmax(self.route_values[day]))')
    text=text.replace('scores=self.rank.predict(x);chosen=int(np.argmax(scores))','scores=R.adjust(shadow,i,candidates,self.rank.predict(x),self.route_mode);chosen=int(np.argmax(scores))')
    text=text.replace("'method':'learned_service_idle_fallback'","'method':'distilled_services_value_calibrated_routing','route_mode':self.route_mode");p.write_text(text)
    parent_hashes={p.name:sha(p) for p in parent.iterdir() if p.suffix in ['.py','.npz','.json']};(d/'parent_provenance.json').write_text(json.dumps({'parent':'ddbs','inherited_hashes':parent_hashes,'source_branch_plan_sha256':sha(source/'plan.json'),'weights_retrained':False,'routing_values_fitted':True,'independence_caveat':'This is one policy-improvement candidate, not an independently qualified model by renaming.'},indent=2)+'\n')
    report={'version':a.version,'algorithm':'Empirical mean terminal margin delta for each observed day and routing mode; a tabular value estimate on top of frozen replay-distilled models. No neural value model, PPO or expert relabelling.','training_seeds':seeds,'training_branch_rows':len(rows),'observed_days':days,'feature_used':['current_day'],'other_142_collected_features_used':False,'training_counts':counts.tolist(),'selected_modes':{str(day):int(values[day].argmax()) for day in days},'mean_margin_delta_table':values[days].tolist(),'validation_seeds_not_used':[919261001,919261002,919261003,919261004],'composition_warning':'One-day branch effects do not add; combined policy must be evaluated from step zero.','branch_hashes':{f'{r["seed"]}_{r["seat"]}_{r["day"]}_{r["mode"]}.json':sha(source/f'{r["seed"]}_{r["seat"]}_{r["day"]}_{r["mode"]}.json') for r in rows},'hashes':{p.name:sha(p) for p in d.iterdir() if p.suffix in ['.py','.npz','.npy','.json']}}
    (d/'value_training_report.json').write_text(json.dumps(report,indent=2)+'\n')
    registry=json.loads((B/'registry.json').read_text());assert registry['next_version']==a.version;registry['versions'].append({'version':a.version,'index':max(v['index'] for v in registry['versions'])+1,'parent':'ddbs','status':'PREPARING','method':config['method'],'hypothesis':'A small value-calibrated daily priority schedule can improve terminal competitive outcomes beyond replay imitation and idle-work corrections.','selection':report['selected_modes']});registry['next_version']=None;(B/'registry.json').write_text(json.dumps(registry,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['hashes','branch_hashes','training_counts']},indent=2))
if __name__=='__main__':main()
