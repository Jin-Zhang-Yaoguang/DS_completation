"""Test early carrot harvest at existing maintenance visits, with no new moves."""
from pathlib import Path
import copy,hashlib,json
from compile_wheat_alternatives import simulate
B=Path(__file__).resolve().parent

def main():
    source=B/'wheat_alternative_modules.json';base=json.loads(source.read_text());out=[]
    for j,job in enumerate(base['jobs']):
        if 'harvest_step' not in job or job['purchase_step']<0 or job['purchase_slot']<0 or job['direct_grain_dependencies']:continue
        options=[]
        for at,(t,i,op) in enumerate(job['events']):
            if op not in ['WATER','FERTILIZE','HARVEST']:continue
            candidate=copy.deepcopy(job);candidate['harvest_step']=t;candidate['harvest_unit']=i;candidate['events']=job['events'][:at]+[[t,i,'HARVEST']]
            qty=simulate(candidate,'CARROT')
            if qty>0:options.append({'harvest_step':t,'harvest_unit':i,'replaced_action':op,'carrot_yield':qty,'earlier_turns':job['harvest_step']-t})
        if options:
            options.sort(key=lambda x:(-x['carrot_yield'],x['harvest_step']))
            out.append({'source_job':j,'purchase_step':job['purchase_step'],'purchase_slot':job['purchase_slot'],'plant_step':job['plant_step'],'plant_unit':job['plant_unit'],'xy':job['xy'],'source_harvest_step':job['harvest_step'],'source_harvest_unit':job['harvest_unit'],'source_wheat_yield':job['source_yield'],'best':options[0],'options':options})
    late=[r for r in out if r['purchase_step']//24>=12]
    result={'source_modules_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'eligible_cycles':len(out),'late_eligible_cycles':len(late),'late_carrot_units':sum(r['best']['carrot_yield'] for r in late),'late_source_wheat_units':sum(r['source_wheat_yield'] for r in late),'additional_late_cycles_vs_fixed_harvest':len(late)-base['late_eligible_cycles'],'boundary':'Every alternative is physically simulated with official lifecycle rules and uses an existing unit visit. Economics, seed ordering, whole-agent stock replacement and dynamic competition are not yet tested.','modules':out}
    (B/'wheat_early_harvest_modules.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='modules'}),flush=True)
if __name__=='__main__':main()
