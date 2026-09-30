#!/usr/bin/env python3
"""只读事前清单与本地结果，校验完整性并按分差配对；不调用候选或引擎。"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,statistics
from datetime import datetime,timezone
from pathlib import Path

PASS={'farmer':['PASS'],'hands':[],'market':[]}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def number(value):return type(value) in (int,float) and math.isfinite(value)
def stamp(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'));assert dt.tzinfo is not None;return dt
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def evaluate(plan,snapshots,initial_issues=()):
    """纯数据核查。快照由read_plan载入；测试可注入坏数据，不修改真实来源。"""
    issues=list(initial_issues);valid_rows={};job_reports=[]
    def issue(code,**detail):issues.append({'code':code,**detail})
    candidate=plan.get('candidate');references=plan.get('references',[]);seeds=plan.get('seeds',[]);seats=plan.get('seats',[]);opponents=plan.get('opponents',[]);jobs=plan.get('jobs',[])
    def unique_list(values,name):
        if not isinstance(values,list) or not values:issue('EMPTY_OR_INVALID_PLAN_LIST',field=name);return False
        if any(not isinstance(z,(str,int)) for z in values) or len(set(values))!=len(values):issue('DUPLICATE_OR_INVALID_PLAN_VALUE',field=name);return False
        return True
    structure_valid=True
    for name,values in [('references',references),('seeds',seeds),('seats',seats),('opponents',opponents)]:structure_valid=unique_list(values,name) and structure_valid
    if not isinstance(jobs,list) or any(not isinstance(j,dict) for j in jobs):issue('INVALID_PLAN_JOBS');structure_valid=False
    if not structure_valid:return {'schema':'v125-paired-development-assessment-v1','data_integrity_pass':False,'development_strength_guard_pass':False,
                                   'expected_games':None,'observed_unique_cells':0,'issues':issues,'jobs':[],'pairwise_groups':[],
                                   'candidate_calls':0,'engine_steps':0,'new_independent_matches':0}
    if not isinstance(candidate,str) or not candidate or candidate in references:issue('INVALID_CANDIDATE_ID')
    if set(seats)!={0,1}:issue('BOTH_SEATS_REQUIRED')
    if any(type(s) is not int or not 0<=s<2**31 for s in seeds):issue('INVALID_SEED')
    names=[candidate]+references;expected_jobs={(c,o) for c in names for o in opponents};seen_jobs=collections.Counter()
    freeze=None
    try:freeze=stamp(plan['frozen_at_utc'])
    except (KeyError,ValueError,TypeError,AssertionError):issue('MISSING_OR_INVALID_PLAN_FREEZE_TIME')
    if plan.get('evidence_role')=='POSTHOC_SCHEMA_FIXTURE':issue('POSTHOC_FIXTURE_NOT_DEVELOPMENT_EVIDENCE')
    if not plan.get('engine_composite_sha256'):issue('PLAN_ENGINE_SHA_MISSING')
    if not plan.get('runner_sha256'):issue('PLAN_RUNNER_SHA_MISSING')
    common_engine=set();common_runner=set();candidate_hashes=collections.defaultdict(set);opponent_hashes=collections.defaultdict(set)
    n_expected=len(seeds)*len(seats)
    for index,job in enumerate(jobs):
        cid=job.get('candidate_id');opp=job.get('opponent_label');pair=(cid,opp);seen_jobs[pair]+=1
        if pair not in expected_jobs:issue('UNPLANNED_JOB',job_index=index,candidate_id=cid,opponent_label=opp)
        snapshot=snapshots[index] if index<len(snapshots) else None
        if snapshot is None:issue('JOB_FILES_MISSING',job_index=index);continue
        m,rows,summary=snapshot['manifest'],snapshot['games'],snapshot['summary'];job_codes=[]
        def ji(code,**detail):job_codes.append(code);issue(code,job_index=index,candidate_id=cid,opponent_label=opp,**detail)
        try:
            ch=m['candidate'];oh=m['opponent'];eh=m['engine'];rh=m['harness'];mhash=digest(m)
            if ch['entry_sha256']!=job.get('entry_sha256'):ji('CANDIDATE_ENTRY_SHA_MISMATCH')
            if job.get('candidate_composite_sha256') and ch['composite_sha256']!=job['candidate_composite_sha256']:ji('PLAN_CANDIDATE_COMPOSITE_SHA_MISMATCH')
            if job.get('opponent_composite_sha256') and oh['composite_sha256']!=job['opponent_composite_sha256']:ji('PLAN_OPPONENT_COMPOSITE_SHA_MISMATCH')
            if eh['composite_sha256']!=plan.get('engine_composite_sha256'):ji('PLAN_ENGINE_SHA_MISMATCH')
            if rh['sha256']!=plan.get('runner_sha256'):ji('PLAN_RUNNER_SHA_MISMATCH')
            common_engine.add(eh['composite_sha256']);common_runner.add(rh['sha256']);candidate_hashes[cid].add(ch['composite_sha256']);opponent_hashes[opp].add(oh['composite_sha256'])
            if opp=='PASS' and oh['entry']!='PASS':ji('PASS_LABEL_IS_NOT_PASS_AGENT')
            if len(m['seeds'])!=len(set(m['seeds'])) or set(m['seeds'])!=set(seeds):ji('MANIFEST_SEEDS_NOT_EXACT_PLAN')
            if len(m['seats'])!=len(set(m['seats'])) or set(m['seats'])!=set(seats):ji('MANIFEST_SEATS_NOT_EXACT_PLAN')
            if m['options'].get('parity') is not True:ji('MANIFEST_PARITY_NOT_ENABLED')
            if m.get('workers')!=1:ji('MANIFEST_WORKER_CONTRACT_MISMATCH')
            if len(rows)!=n_expected:ji('GAME_COUNT_NOT_EXACT_PLAN',expected=n_expected,actual=len(rows))
            seen_cells=collections.Counter();seen_keys=collections.Counter();outcomes=collections.Counter();margins=[]
            for row_index,g in enumerate(rows):
                rissues=[]
                def ri(code,**detail):rissues.append(code);ji(code,row_index=row_index,**detail)
                seed=g.get('seed');seat=g.get('candidate_seat');cell=(seed,seat);seen_cells[cell]+=1;seen_keys[g.get('key')]+=1
                if cell not in {(s,t) for s in seeds for t in seats}:ri('UNPLANNED_GAME_CELL',seed=seed,seat=seat)
                expected_key=f'{ch["composite_sha256"]}:{oh["composite_sha256"]}:{seed}:{seat}:{eh["composite_sha256"]}'
                if g.get('key')!=expected_key:ri('GAME_KEY_SHA_IDENTITY_MISMATCH')
                for field,value in [('candidate_composite_sha256',ch['composite_sha256']),('opponent_composite_sha256',oh['composite_sha256']),('engine_composite_sha256',eh['composite_sha256']),('manifest_sha256',mhash)]:
                    if g.get(field)!=value:ri('GAME_'+field.upper()+'_MISMATCH')
                if g.get('status')!='DONE' or g.get('statuses')!=['DONE','DONE']:ri('GAME_NOT_COMPLETE')
                if g.get('calls')!=719:ri('GAME_NOT_719_CALLS')
                if g.get('errors')!=[]:ri('GAME_ERRORS_OR_MISSING_ERROR_EVIDENCE')
                if g.get('parity_pass') is not True or g.get('parity_state_checks')!=1440:ri('GAME_PARITY_INCOMPLETE')
                agents=g.get('agents',[])
                if len(agents)!=2:ri('AGENT_REPORTS_NOT_BOTH_SEATS')
                for s,a in enumerate(agents):
                    if a.get('calls')!=719:ri('AGENT_CALLS_NOT_719',agent_seat=s)
                    maximum=a.get('latency_ms',{}).get('max')
                    if a.get('calls_over_1s')!=0 or not number(maximum) or not 0<=maximum<=1000:ri('AGENT_LATENCY_OVER_LIMIT_OR_MISSING',agent_seat=s)
                try:
                    start=stamp(g['started_at']);end=stamp(g['completed_at'])
                    if freeze is None or start<freeze:ri('GAME_PRECEDES_PLAN_FREEZE')
                    if end<start:ri('GAME_TIMESTAMP_ORDER_INVALID')
                except (KeyError,ValueError,TypeError,AssertionError):ri('GAME_TIMESTAMP_MISSING_OR_INVALID')
                rewards=g.get('rewards',[])
                if not isinstance(rewards,list) or len(rewards)!=2 or not all(number(x) for x in rewards) or seat not in (0,1):ri('REWARDS_INVALID');continue
                own,rival=rewards[seat],rewards[1-seat];margin=own-rival
                if g.get('candidate_reward')!=own or g.get('opponent_reward')!=rival or g.get('margin')!=margin:ri('MARGIN_REWARDS_NOT_CLOSED')
                outcome='win' if margin>0 else 'tie' if margin==0 else 'loss';outcomes[outcome]+=1;margins.append(margin)
                if g.get('outcome')!=outcome:ri('OUTCOME_NOT_REWARDS')
                row={'candidate_id':cid,'opponent_label':opp,'seed':seed,'seat':seat,'source_key':g.get('key'),'own_cash':own,'opponent_cash':rival,'margin':margin,
                     'row_issues':rissues,'job_index':index,'row_index':row_index}
                k=(cid,opp,seed,seat)
                if k in valid_rows:ri('DUPLICATE_GLOBAL_PLANNED_KEY')
                else:valid_rows[k]=row
            for cell in {(s,t) for s in seeds for t in seats}:
                if seen_cells[cell]!=1:ji('MISSING_OR_DUPLICATE_GAME_CELL',seed=cell[0],seat=cell[1],count=seen_cells[cell])
            if any(n!=1 for n in seen_keys.values()):ji('DUPLICATE_GAME_KEY')
            expected_summary={'expected_games':n_expected,'recorded_games':n_expected,'done_games':n_expected,'status':'COMPLETE','manifest_sha256':mhash,
                              'all_719_calls':True,'all_call_counts_719_per_seat':True,'all_parity_pass':True,
                              'wins_ties_losses_errors':[outcomes['win'],outcomes['tie'],outcomes['loss'],0],
                              'pure_win_rate_expected_denominator':outcomes['win']/n_expected if n_expected else None,
                              'mean_margin_completed_only':statistics.mean(margins) if margins else None}
            for field,value in expected_summary.items():
                if summary.get(field)!=value:ji('SUMMARY_NOT_RECONCILED',field=field,expected=value,actual=summary.get(field))
        except (KeyError,TypeError,ValueError,IndexError) as exc:ji('MALFORMED_JOB_EVIDENCE',detail=str(exc))
        job_reports.append({'job_index':index,'candidate_id':cid,'opponent_label':opp,'output':job.get('output'),'issues':job_codes,'recorded_rows':len(rows)})
    for pair in expected_jobs:
        if seen_jobs[pair]!=1:issue('MISSING_OR_DUPLICATE_JOB',candidate_id=pair[0],opponent_label=pair[1],count=seen_jobs[pair])
    if len(common_engine)!=1:issue('MIXED_OR_MISSING_ENGINES')
    if len(common_runner)!=1:issue('MIXED_OR_MISSING_RUNNERS')
    for cid,hashes in candidate_hashes.items():
        if len(hashes)!=1:issue('CANDIDATE_CHANGED_ACROSS_OPPONENTS',candidate_id=cid)
    for opp,hashes in opponent_hashes.items():
        if len(hashes)!=1:issue('OPPONENT_CHANGED_ACROSS_CANDIDATES',opponent_label=opp)
    groups=[]
    for ref in references:
        for opp in opponents:
            pairs=[];missing=[]
            for seed in seeds:
                for seat in seats:
                    a=valid_rows.get((candidate,opp,seed,seat));b=valid_rows.get((ref,opp,seed,seat))
                    if a is None or b is None:missing.append({'seed':seed,'seat':seat});continue
                    delta=a['margin']-b['margin'];own=a['own_cash']-b['own_cash'];rival=a['opponent_cash']-b['opponent_cash']
                    residual=delta-(own-rival)
                    if abs(residual)>1e-9:issue('PAIRED_CASH_DECOMPOSITION_NOT_CLOSED',reference=ref,opponent=opp,seed=seed,seat=seat,residual=residual)
                    pairs.append({'seed':seed,'seat':seat,'candidate_margin':a['margin'],'reference_margin':b['margin'],'margin_delta':delta,
                                  'candidate_own_cash':a['own_cash'],'reference_own_cash':b['own_cash'],'own_cash_delta':own,
                                  'candidate_opponent_cash':a['opponent_cash'],'reference_opponent_cash':b['opponent_cash'],'opponent_cash_delta':rival,
                                  'decomposition_residual':residual,'candidate_key':a['source_key'],'reference_key':b['source_key']})
            deltas=[x['margin_delta'] for x in pairs];positive=sum(x>0 for x in deltas);needed=math.ceil(.6*n_expected)
            seat_stats={str(s):{'n':sum(x['seat']==s for x in pairs),'mean_margin_delta':statistics.mean([x['margin_delta'] for x in pairs if x['seat']==s]) if any(x['seat']==s for x in pairs) else None,
                                'mean_own_cash_delta':statistics.mean([x['own_cash_delta'] for x in pairs if x['seat']==s]) if any(x['seat']==s for x in pairs) else None,
                                'mean_opponent_cash_delta':statistics.mean([x['opponent_cash_delta'] for x in pairs if x['seat']==s]) if any(x['seat']==s for x in pairs) else None} for s in seats}
            median=statistics.median(deltas) if deltas else None
            guard=len(pairs)==n_expected and positive>=needed and median is not None and median>0 and set(seats)=={0,1} and all(v['n']==len(seeds) and v['mean_margin_delta']>=0 for v in seat_stats.values())
            groups.append({'reference':ref,'opponent_label':opp,'expected_pairs':n_expected,'available_pairs':len(pairs),'missing_pairs':missing,'positive_deltas':positive,
                           'required_positive_deltas':needed,'ties':sum(x==0 for x in deltas),'negative_deltas':sum(x<0 for x in deltas),'median_margin_delta':median,
                           'mean_margin_delta':statistics.mean(deltas) if deltas else None,'per_seat':seat_stats,'pairwise_guard_pass':guard,'pairs':pairs})
    return {'schema':'v125-paired-development-assessment-v1','evidence_role':'LOCAL_DEVELOPMENT_STRENGTH_GUARD_ONLY_NOT_G1_G2_OR_GOLD',
            'data_integrity_pass':not issues,'development_strength_guard_pass':not issues and bool(groups) and all(g['pairwise_guard_pass'] for g in groups),
            'expected_games':len(expected_jobs)*n_expected,'observed_unique_cells':len(valid_rows),'issues':issues,'jobs':job_reports,'pairwise_groups':groups,
            'candidate_calls':0,'engine_steps':0,'new_independent_matches':0,
            'rule':'每reference×opponent独立：完整N对，margin_delta>0至少ceil(0.6N)，median>0，两个席位mean>=0。主机制另行核验。'}


def read_plan(plan_path):
    issues=[];files={};snapshots=[];plan=json.loads(plan_path.read_text());files[str(plan_path.resolve())]=sha(plan_path)
    def issue(code,**detail):issues.append({'code':code,**detail})
    def fingerprint(path,expected=None):
        path=Path(path).resolve()
        try:value=sha(path);files[str(path)]=value
        except OSError as exc:issue('SOURCE_FILE_MISSING',path=str(path),detail=str(exc));return
        if expected is not None and value!=expected:issue('SOURCE_SHA_MISMATCH',path=str(path),expected=expected,actual=value)
    for index,job in enumerate(plan.get('jobs',[])):
        try:
            root=Path(job['output']).expanduser();root=root if root.is_absolute() else plan_path.parent/root
            m=json.loads((root/'run_manifest.json').read_text());rows=[json.loads(x) for x in (root/'games.jsonl').read_text().splitlines() if x.strip()];summary=json.loads((root/'summary.json').read_text())
            for name in ('run_manifest.json','games.jsonl','summary.json'):fingerprint(root/name)
            for name in ('candidate','opponent','engine'):
                info=m[name]
                for path,value in info['files'].items():fingerprint(path,value)
                expected=digest({'builtin':'PASS','action':PASS}) if info.get('entry')=='PASS' else digest(info['files'])
                if info['composite_sha256']!=expected:issue('PACKAGE_COMPOSITE_NOT_FILES',job_index=index,package=name)
                if name!='engine':
                    entry_expected=digest(PASS) if info['entry']=='PASS' else info['files'].get(info['entry'])
                    if info.get('entry_sha256')!=entry_expected:issue('PACKAGE_ENTRY_SHA_NOT_FILES',job_index=index,package=name)
            fingerprint(m['harness']['path'],m['harness']['sha256'])
            if m.get('protocol'):fingerprint(m['protocol']['path'],m['protocol']['sha256'])
            for g in rows:
                if g.get('trace'):fingerprint(g['trace']['path'],g['trace']['sha256'])
            snapshots.append({'manifest':m,'games':rows,'summary':summary})
        except (OSError,KeyError,ValueError,TypeError) as exc:issue('SOURCE_JOB_LOAD_FAILED',job_index=index,detail=str(exc));snapshots.append(None)
    return plan,snapshots,issues,files


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True);assert not (out/'assessment_manifest.json').exists(),'拒绝覆盖已冻结评估'
    try:plan,snapshots,issues,files=read_plan(args.plan.resolve())
    except (OSError,ValueError,TypeError,AttributeError) as exc:
        failure={'schema':'v125-paired-development-assessment-v1','data_integrity_pass':False,'development_strength_guard_pass':False,
                 'issues':[{'code':'PLAN_UNREADABLE_OR_MALFORMED','detail':str(exc)}],'candidate_calls':0,'engine_steps':0,'new_independent_matches':0}
        dump(out/'assessment_manifest.json',{'assessor_sha256':sha(__file__),'plan_path':str(args.plan.resolve()),'plan_read_failed':True})
        dump(out/'assessment.json',failure);print(json.dumps(failure,ensure_ascii=False));raise SystemExit(2)
    freeze={'created_at_utc':datetime.now(timezone.utc).isoformat(),'assessor':{'path':str(Path(__file__).resolve()),'sha256':sha(__file__)},
            'plan':{'path':str(args.plan.resolve()),'sha256':sha(args.plan)},'source_files':files,'candidate_calls':0,'engine_steps':0,'new_independent_matches':0}
    dump(out/'assessment_manifest.json',freeze)
    result=evaluate(plan,snapshots,issues)
    for path,value in files.items():
        if not Path(path).is_file() or sha(path)!=value:result['issues'].append({'code':'SOURCE_CHANGED_DURING_ASSESSMENT','path':path});result['data_integrity_pass']=False;result['development_strength_guard_pass']=False
    if sha(__file__)!=freeze['assessor']['sha256']:result['issues'].append({'code':'ASSESSOR_CHANGED_DURING_RUN'});result['data_integrity_pass']=False;result['development_strength_guard_pass']=False
    dump(out/'assessment.json',result)
    print(json.dumps({'data_integrity_pass':result['data_integrity_pass'],'development_strength_guard_pass':result['development_strength_guard_pass'],
                      'expected_games':result['expected_games'],'observed_unique_cells':result['observed_unique_cells'],'issues':result['issues'],'output':str(out)},ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['data_integrity_pass'] else 2)


if __name__=='__main__':main()
