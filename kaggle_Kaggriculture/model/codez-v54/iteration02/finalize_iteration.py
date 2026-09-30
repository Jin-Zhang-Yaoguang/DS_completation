"""Complete, paired, hash-pinned finalization. Never promotes an incomplete or failed panel."""
import sys,json,hashlib,collections,datetime,tarfile,gzip,io
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research
from evaluate_iteration import read_run,stats,cluster_ci,evaluate
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'iteration02'

def jread(p):return json.loads(p.read_text())
def atomic(p,obj):
    temp=p.with_suffix(p.suffix+'.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2));temp.replace(p)
def matched(a,b):
    key=lambda r:(r['job']['opponent'],r['job']['seed'],r['job']['seat'])
    x={key(r):r for r in a};y={key(r):r for r in b};assert len(x)==len(a) and len(y)==len(b) and x.keys()==y.keys()
    groups=collections.defaultdict(lambda:dict(n=0,control_wins=0,candidate_wins=0,win_regressions=0,margin_delta=0,margin_decreases=0));seed_deltas=collections.defaultdict(list)
    pairs=[]
    for k in sorted(x):
        c=x[k]['margin'];v=y[k]['margin'];d=v-c;loss=int(c>0 and v<=0)
        for group in ['all',f'opponent:{k[0]}',f'seat:{k[2]}',f'opponent_seat:{k[0]}:{k[2]}']:
            g=groups[group];g['n']+=1;g['control_wins']+=int(c>0);g['candidate_wins']+=int(v>0);g['win_regressions']+=loss;g['margin_delta']+=d;g['margin_decreases']+=int(d<0)
        seed_deltas[k[1]].append((d,int(v>0)-int(c>0)))
        pairs.append(dict(opponent=k[0],seed=k[1],seat=k[2],control_margin=c,candidate_margin=v,margin_delta=d,win_regression=bool(loss)))
    vals=np.array([np.mean(seed_deltas[k],axis=0) for k in sorted(seed_deltas)]);rng=np.random.default_rng(218743);boot=vals[rng.integers(0,len(vals),(20000,len(vals)))].mean(axis=1)
    return {'groups':dict(groups),'pairs':pairs,'seed_cluster':{'seeds':len(vals),'mean_margin_delta':float(vals[:,0].mean()),'margin_delta_lower95':float(np.quantile(boot[:,0],.025)),'margin_delta_upper95':float(np.quantile(boot[:,0],.975)),'win_rate_delta_pp':float(vals[:,1].mean()*100),'win_delta_pp_lower95':float(np.quantile(boot[:,1],.025)*100),'win_delta_pp_upper95':float(np.quantile(boot[:,1],.975)*100)}}

def main():
    for f in jread(ROOT/'official_environment.json')['files']:
        assert research.digest(Path(f['installed_path']))==f['sha256']
        assert research.digest(ROOT/f['snapshot'])==f['sha256']
    selection=jread(P/'candidate_selection.json');assert research.digest(ROOT/'versions/v014/main.py')==selection['frozen_sha256']
    for name in ['32_frozen_confirmation','33_frozen_legacy','34_frozen_extended_pool']:
        spec=jread(ROOT/'runs'/f'{name}.json');assert research.digest(ROOT/'research_official.py')==spec['official_runner_sha256']
    spec=jread(ROOT/'runs/32_frozen_confirmation.json');assert research.digest(P/'protocol.json')==spec['protocol_sha256'];assert research.digest(P/'candidate_selection.json')==spec['selection_sha256']
    rows=read_run('32_frozen_confirmation');legacy=read_run('33_frozen_legacy');extended=read_run('34_frozen_extended_pool');old=read_run('11_h002_gate9')
    assert research.digest(ROOT/'runs/11_h002_gate9.jsonl')==jread(ROOT/'runs/33_frozen_legacy.json')['baseline_sha256']
    candidate=[r for r in rows if r['job']['agent']=='versions/v014/main.py'];assert len(candidate)==320
    controls={v:[r for r in rows if r['job']['agent']==f'versions/{v}/main.py'] for v in ['v002','v003']};assert all(len(v)==320 for v in controls.values())
    fresh_path=ROOT/'runs/32_frozen_confirmation.evaluation.json'
    fresh=evaluate('32_frozen_confirmation','v014') if not fresh_path.exists() else jread(fresh_path)
    comparisons={v:matched(g,candidate) for v,g in controls.items()}
    legacy_pair=matched([r for r in old if r['job']['agent']=='versions/v002/main.py'],legacy)
    legacy_pass=all(g['win_regressions']==0 and g['candidate_wins']>=g['control_wins'] and g['margin_delta']>=0 for g in legacy_pair['groups'].values())
    ext_candidate=[r for r in extended if r['job']['agent']=='versions/v014/main.py'];ext_control=[r for r in extended if r['job']['agent']=='versions/v003/main.py'];extra=matched(ext_control,ext_candidate)
    extra_pass=all(g['candidate_wins']>=g['control_wins'] for name,g in extra['groups'].items() if name=='all' or name.startswith('opponent:'))
    all_candidate=candidate+legacy+ext_candidate
    new_errors=sum(r['telemetry'].get('errors',0)+r['telemetry'].get('terminal',{}).get('errors',0)+r['telemetry'].get('cxd',{}).get('cxd_errors',0) for r in all_candidate)
    max_seconds=max(r['max_action_seconds'] for r in all_candidate);file_entry=jread(P/'official_file_entry.json');audit=jread(P/'idle_official_rule_audit.json')
    engineering=new_errors==0 and max_seconds<1 and file_entry['statuses']==['DONE','DONE'] and file_entry['states']==720 and audit['status']=='ok'
    histories={}
    for name in ['historical_reproduction','source_reproduction','replay_ledger']:
        summary=jread(P/f'{name}.summary.json');assert summary['complete'] and summary['errors']==0 and research.digest(P/f'{name}.jsonl')==summary['result_sha256'];histories[name]=summary
    historical=[json.loads(s) for s in (P/'historical_reproduction.jsonl').read_text().splitlines()];source=[json.loads(s) for s in (P/'source_reproduction.jsonl').read_text().splitlines()]
    assert len(historical)==len(source)==50 and all(r['reward_exact'] for r in historical+source) and all(r['changed_requests']==0 for r in source)
    replay=[json.loads(s) for s in (P/'counterfactual_idle.jsonl').read_text().splitlines() if 'versions/v014/main.py' in s];assert len(replay)==50 and all(r['status']=='ok' for r in replay)
    base={r['job']['episode_id']:r for r in map(json.loads,(P/'counterfactual_baselines.jsonl').read_text().splitlines()) if r['job']['agent']=='versions/v003/main.py'}
    replay_stats={}
    for label,loss in [('selected_losses',True),('selected_win_controls',False)]:
        subset=[r for r in replay if (r['live_margin']<0)==loss];replay_stats[label]={'n':len(subset),'r14_tape_wins':sum(base[r['job']['episode_id']]['margin']>0 for r in subset),'v014_tape_wins':sum(r['margin']>0 for r in subset),'margin_delta_vs_r14':sum(r['margin']-base[r['job']['episode_id']]['margin'] for r in subset),'formerly_winning_tape_regressions':sum(base[r['job']['episode_id']]['margin']>0 and r['margin']<=0 for r in subset)}
    qualified=fresh['modern_bar_pass'] and legacy_pass and extra_pass and engineering and comparisons['v003']['seed_cluster']['margin_delta_lower95']>0
    result={'version':'v014','status':'LOCAL_QUALIFIED_BROAD_PUBLIC_POOL' if qualified else 'NOT_QUALIFIED_BROAD_BAR','not_online_validation':True,'source_sha256':selection['frozen_sha256'],'fresh_confirmation':fresh,'paired_vs_controls':comparisons,'legacy_pass':legacy_pass,'legacy':legacy_pair,'extended_pool_pass':extra_pass,'extended_pool':extra,'engineering_pass':engineering,'caught_candidate_errors':new_errors,'max_action_seconds':max_seconds,'replay_diagnostics_only':replay_stats,'qualification':qualified,'online_submission':None}
    atomic(P/'qualification.json',result)
    print(json.dumps({'status':result['status'],'modern':fresh['modern_bar'],'legacy_pass':legacy_pass,'extended_pass':extra_pass,'engineering':engineering,'candidate_stats':stats(candidate),'novel_vs_r14':comparisons['v003']['seed_cluster'],'replay':replay_stats},ensure_ascii=False,indent=2))
    # Package only after every gate passes. Failed evidence and the source remain available.
    if qualified:
        d=ROOT/'versions/v014';package=d/'submission.tar.gz';assert not package.exists()
        notice=('codez-v54 v014 is a derivative research agent. It incorporates the frozen Claude V54r14 control and its original public V54/V56/Rescue7 attributions, retained in main.py.\nNew layers: public-state-consistent opponent shadowing; bounded market search refinements; certified terminal search budget; official-rule-proven no-op productivity repairs.\nDeterministic rules are extracted from kaggle-environments 1.32.7, kaggriculture.py SHA256 bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e. Original upstream notices and Apache-2.0 references are retained in main.py.\nNo claim to ownership or endorsement of upstream work. No online rating or universal unseen-opponent advantage is claimed.\nmain.py SHA256 '+selection['frozen_sha256']+'\n').encode()
        with package.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
            for name,body in [('main.py',(d/'main.py').read_bytes()),('NOTICE.txt',notice)]:
                info=tarfile.TarInfo(name);info.size=len(body);info.mtime=0;info.mode=0o644;tar.addfile(info,io.BytesIO(body))
        with tarfile.open(package,'r:gz') as tar:
            assert tar.getnames()==['main.py','NOTICE.txt'];assert hashlib.sha256(tar.extractfile('main.py').read()).hexdigest()==selection['frozen_sha256']
        atomic(d/'decision.json',{'status':result['status'],'source_sha256':selection['frozen_sha256'],'package_sha256':research.digest(package),'qualification_file':'iteration02/qualification.json','qualification_sha256':research.digest(P/'qualification.json'),'online_submission':None})
if __name__=='__main__':main()
