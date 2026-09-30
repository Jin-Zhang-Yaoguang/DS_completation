"""Preserve v014's rejection; independently qualify and package v019 only if all gates pass."""
from finalize_iteration import ROOT,P,jread,atomic,read_run,matched,stats,evaluate,research
import json,hashlib,tarfile,gzip,io

def select(rows,v):return [r for r in rows if r['job']['agent']==f'versions/{v}/main.py']
def trace_equal(control,candidate):
    key=lambda r:(r['job']['opponent'],r['job']['seed'],r['job']['seat'])
    a={key(r):r for r in control};b={key(r):r for r in candidate};assert a.keys()==b.keys()
    return sum(a[k]['trace_sha256']==b[k]['trace_sha256'] and a[k]['scores']==b[k]['scores'] for k in a)
def no_regression(result):
    return all(g['win_regressions']==0 and g['candidate_wins']>=g['control_wins'] and g['margin_delta']>=0 for g in result['groups'].values())
def extended_pass(result):
    return all(g['candidate_wins']>=g['control_wins'] for k,g in result['groups'].items() if k=='all' or k.startswith('opponent:'))

def main():
    candidate='v019';sel=jread(P/'candidate_selection_v019.json');assert research.digest(ROOT/f'versions/{candidate}/main.py')==sel['sha256']
    for item in jread(ROOT/'official_environment.json')['files']:assert research.digest(__import__('pathlib').Path(item['installed_path']))==item['sha256']
    names=['36_v019_fresh_confirmation','37_v019_legacy_exact','38_v019_legacy_fresh','39_v019_extended_regression','40_v019_extended_fresh']
    panels={}
    for name in names:
        spec=jread(ROOT/'runs'/f'{name}.json');assert spec['selection_sha256']==research.digest(P/'candidate_selection_v019.json');assert spec['official_runner_sha256']==research.digest(ROOT/'research_official.py');panels[name]=read_run(name)
    assert jread(ROOT/'runs/37_v019_legacy_exact.json')['baseline_result_sha256']==research.digest(ROOT/'runs/11_h002_gate9.jsonl')
    assert jread(ROOT/'runs/39_v019_extended_regression.json')['baseline_result_sha256']==research.digest(ROOT/'runs/34_frozen_extended_pool.jsonl')
    modern=panels[names[0]];fresh_path=ROOT/'runs/36_v019_fresh_confirmation.evaluation.json'
    fresh=evaluate(names[0],candidate) if not fresh_path.exists() else jread(fresh_path)
    cand=select(modern,candidate);assert len(cand)==320
    paired={v:matched(select(modern,v),cand) for v in ['v002','v003']}
    legacy_base=select(read_run('11_h002_gate9'),'v002');legacy_old=matched(legacy_base,panels[names[1]]);old_equal=trace_equal(legacy_base,panels[names[1]])
    legacy_new_base=select(panels[names[2]],'v002');legacy_new_cand=select(panels[names[2]],candidate);legacy_new=matched(legacy_new_base,legacy_new_cand);new_equal=trace_equal(legacy_new_base,legacy_new_cand)
    ext_old=matched(select(read_run('34_frozen_extended_pool'),'v003'),panels[names[3]])
    ext_new=matched(select(panels[names[4]],'v003'),select(panels[names[4]],candidate))
    all_candidate=[r for rows in panels.values() for r in select(rows,candidate)]
    errors=sum(r['telemetry'].get('errors',0)+r['telemetry'].get('terminal',{}).get('errors',0)+r['telemetry'].get('cxd',{}).get('cxd_errors',0) for r in all_candidate)
    max_time=max(r['max_action_seconds'] for r in all_candidate)
    entry=jread(P/'official_file_entry_v019.json');audit=jread(P/'idle_official_rule_audit_v019.json')
    engineering=errors==0 and max_time<1 and entry['statuses']==['DONE','DONE'] and entry['states']==720 and audit['status']=='ok' and all(r['telemetry'].get('prefix_agreement') for r in all_candidate)
    legacy_ok=no_regression(legacy_old) and no_regression(legacy_new) and old_equal==288 and new_equal==72
    extended_ok=extended_pass(ext_old) and extended_pass(ext_new)
    independent_gain=paired['v003']['seed_cluster']['margin_delta_lower95']>0
    passed=fresh['modern_bar_pass'] and legacy_ok and extended_ok and engineering and independent_gain
    report={'candidate':candidate,'source_sha256':sel['sha256'],'status':'LOCAL_QUALIFIED_BROAD_PUBLIC_POOL' if passed else 'NOT_QUALIFIED_BROAD_BAR','qualification':passed,'online_submission':None,'scope':'Local adaptive public programs, not an online rank or a guarantee against private strategies. Four legacy opening cells can collide with unseen policies.','modern':fresh,'paired_vs_controls':paired,'legacy_old':legacy_old,'legacy_fresh':legacy_new,'legacy_trace_matches':{'old':old_equal,'fresh':new_equal},'legacy_pass':legacy_ok,'extended_old':ext_old,'extended_fresh':ext_new,'extended_pass':extended_ok,'engineering_pass':engineering,'candidate_caught_errors':errors,'max_action_seconds':max_time,'novel_gain_lower95_positive':independent_gain}
    atomic(P/'qualification_v019.json',report)
    print(json.dumps({'status':report['status'],'modern':stats(cand),'r14_head_to_head':fresh['versions'][candidate]['opponents']['v54r14'],'paired_novel_gain':paired['v003']['seed_cluster'],'legacy':report['legacy_trace_matches'],'extended_old':ext_old['groups']['all'],'extended_fresh':ext_new['groups']['all'],'flags':{'modern':fresh['modern_bar_pass'],'legacy':legacy_ok,'extended':extended_ok,'engineering':engineering}},ensure_ascii=False,indent=2))
    if not passed:return
    d=ROOT/f'versions/{candidate}';package=d/'submission.tar.gz';assert not package.exists()
    notice=('codez-v54 '+candidate+' is a derivative research agent. Its modern expert is derived from the frozen Claude V54r14 control; its legacy expert is codez-v54 v002, derived from the original public V54 source. Original public V54/V56/Rescue7 credits and notices are retained in main.py.\nNew layers include public-state-consistent opponent shadowing, bounded market/terminal search, isolated no-op harvest repair, and opening-compatible legacy routing.\nDeterministic rules are extracted from kaggle-environments 1.32.7, kaggriculture.py SHA256 bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e. Original Apache-2.0 references are retained in main.py.\nNo ownership or endorsement of upstream work is claimed. This is locally validated against frozen public programs; no online rating or universal dominance is claimed.\nmain.py SHA256 '+sel['sha256']+'\n').encode()
    with package.open('xb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='') as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for name,body in [('main.py',(d/'main.py').read_bytes()),('NOTICE.txt',notice)]:
            info=tarfile.TarInfo(name);info.size=len(body);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(body))
    with tarfile.open(package,'r:gz') as tar:
        assert tar.getnames()==['main.py','NOTICE.txt'];assert hashlib.sha256(tar.extractfile('main.py').read()).hexdigest()==sel['sha256']
    atomic(d/'decision.json',{'status':report['status'],'source_sha256':sel['sha256'],'package_sha256':research.digest(package),'qualification_sha256':research.digest(P/'qualification_v019.json'),'online_submission':None})
if __name__=='__main__':main()
