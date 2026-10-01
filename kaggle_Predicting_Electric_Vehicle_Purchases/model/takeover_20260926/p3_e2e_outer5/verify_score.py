"""Independent P3 faithful baseline and internal replacement reconstruction; U scoring last."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE=Path(__file__).resolve().parent;TOP=HERE.parent;PROJECT=HERE.parents[2]
ARCH=PROJECT/'model/validation/e2e_v100_20260905';FORMAL=TOP/'p1_source_group_constraints_40f';DIAG=TOP/'p1_source_group_constraints_5f'
GPU=ARCH/'gpu/remote_output/ct_cache'
sys.path.insert(0,str(ARCH))
import cpu_runner as cpu
import assemble_e2e as assembly

def sha(path):return cpu.sha(path)
def prob(values,rows):
    if values.shape!=(rows,) or not np.isfinite(values).all() or ((values<0)|(values>1)).any():raise ValueError('invalid probability vector')
def tree_leaves(node,origins,seen=frozenset()):
    if 'split_feature' not in node:return 1
    used=seen|{origins[int(node['split_feature'])]}
    if len(used)>1:raise ValueError(f'cross-source grouped tree path: {used}')
    return tree_leaves(node['left_child'],origins,used)+tree_leaves(node['right_child'],origins,used)
def rank(sorted_fit,values):
    return (np.searchsorted(sorted_fit,values,'left')+np.searchsorted(sorted_fit,values,'right')).astype(float)/(2*len(sorted_fit))
def meta90(y,a,b,ua,ub):
    """Independent implementation of V90 five-fold fit-only ECDF and test averaging."""
    u=np.zeros(len(ua));oof=np.full(len(y),np.nan);weights=[]
    for fit,hold in StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y):
        sa=np.sort(a[fit]);sb=np.sort(b[fit]);af=rank(sa,a[fit]);bf=rank(sb,b[fit]);ah=rank(sa,a[hold]);bh=rank(sb,b[hold])
        grid=[round(k*.05,2) for k in range(21)]
        scores=[float(roc_auc_score(y[fit],(1-w)*af+w*bf)) for w in grid]
        best=max(scores);tied=[k for k,s in enumerate(scores) if abs(s-best)<=1e-15];index=min(tied,key=lambda k:(abs(round(k*.05,2)-.5),round(k*.05,2)))
        w=round(index*.05,2);weights.append(w);oof[hold]=(1-w)*ah+w*bh
        u+=((1-w)*rank(sa,ua)+w*rank(sb,ub))/5
    prob(oof,len(y));prob(u,len(ua))
    return oof,u,weights
def meta100(y,v90,ct,v90_u,ct_u):
    """Independent implementation of V100 full-T ECDF/CT grid for U inference."""
    # Historical code also creates five-fold meta OOF. Reconstruct it to
    # compare provenance, but U uses the full-T fitted states and weight.
    meta_oof=np.full(len(y),np.nan)
    grid=np.arange(0.,.5000001,.025)
    for fit,hold in StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y):
        s90=np.sort(v90[fit]);sct=np.sort(ct[fit]);a=rank(s90,v90[fit]);b=rank(sct,ct[fit])
        auc=[float(roc_auc_score(y[fit],(1-w)*a+w*b)) for w in grid]
        index=max(range(len(grid)),key=lambda k:(auc[k],-grid[k]));w=float(grid[index])
        meta_oof[hold]=(1-w)*rank(s90,v90[hold])+w*rank(sct,ct[hold])
    s90=np.sort(v90);sct=np.sort(ct);a=rank(s90,v90);b=rank(sct,ct)
    auc=[float(roc_auc_score(y,(1-w)*a+w*b)) for w in grid]
    index=max(range(len(grid)),key=lambda k:(auc[k],-grid[k]));w=float(grid[index])
    u=(1-w)*rank(s90,v90_u)+w*rank(sct,ct_u)
    prob(meta_oof,len(y));prob(u,len(v90_u))
    return meta_oof,u,w

def reconstructed_family(outer,family,train,hold,fold,ids,y,contract,names,origins,base,groups):
    directory=HERE/f'outer_{outer:02d}'/family;manifest=json.loads((directory/'cache_manifest.json').read_text())
    if manifest['status']!='CACHE_COMPLETE_UNSCORED' or manifest['contract_sha256']!=contract or manifest['outer_U_labels_used'] or manifest['cache_sha256']!=sha(directory/'cache.npz'):raise ValueError('family cache manifest invalid')
    oof=np.full(len(train),np.nan);valid=np.zeros(len(hold));coverage=np.zeros(len(train),np.int8);paths=0
    for atom in range(1,41):
        local=np.flatnonzero(fold==atom-1);fit=train[fold!=atom-1];h=train[local];part=directory/f'atom_{atom:02d}'
        m=json.loads((part/'manifest.json').read_text())
        if m['status']!='COMPLETE_UNSCORED' or m['contract_sha256']!=contract or m['outer']!=outer or m['family']!=family or m['atom']!=atom or m['outer_hold_labels_used'] or m['refit_performed'] or m['training_fit_count']!=1 or not m['atom_hold_labels_used_for_early_stopping']:raise ValueError('atom training scope mismatch')
        if m['fit_idx_sha256']!=cpu.arr_sha(fit) or m['early_stop_hold_idx_sha256']!=cpu.arr_sha(h) or m['outer_valid_idx_sha256']!=cpu.arr_sha(hold) or m['fit_y_sha256']!=cpu.arr_sha(y[fit]) or m['early_stop_hold_y_sha256']!=cpu.arr_sha(y[h]):raise ValueError('atom training identity mismatch')
        source='v85' if family=='grouped_v85' else family;config=base['families'][source];params=cpu.atom_params(source,config,atom);params['n_jobs']=8
        if family=='grouped_v85':params['interaction_constraints']=groups
        if m['params_sha256']!=cpu.json_sha(params) or m['te_seed']!=config['te_seed_base']+atom or m['matrix_dtype']!=('float32' if source=='v80' else 'float64') or m['selected_iteration']<1 or m['selected_iteration']>params['n_estimators']:raise ValueError('atom recipe, dtype or iteration mismatch')
        if m['feature_names_sha256']!=cpu.json_sha(m['feature_names']):raise ValueError('feature schema SHA mismatch')
        if manifest['atom_manifest_sha256'][str(atom)]!=sha(part/'manifest.json') or m['model_sha256']!=sha(part/'model.txt') or m['prediction_sha256']!=sha(part/'predictions.npz'):raise ValueError('atom artifact SHA mismatch')
        with np.load(part/'predictions.npz',allow_pickle=False) as z:
            for key,value in [('oof_idx',h),('valid_idx',hold),('oof_id',ids[h]),('valid_id',ids[hold])]:
                if not np.array_equal(z[key],value):raise ValueError('atom row identity mismatch')
            prob(z['oof_proba'],len(h));prob(z['valid_proba'],len(hold));oof[local]=z['oof_proba'];valid+=z['valid_proba']/40;coverage[local]+=1
        model=lgb.Booster(model_file=str(part/'model.txt'))
        if model.feature_name()!=m['feature_names'] or len(m['feature_names'])!=(113 if family=='v80' else 148):raise ValueError('model feature schema mismatch')
        if family=='grouped_v85':
            if model.feature_name()!=names:raise ValueError('grouped feature names drift')
            for tree in model.dump_model()['tree_info']:paths+=tree_leaves(tree['tree_structure'],origins)
    if not np.all(coverage==1):raise ValueError('atom coverage invalid')
    prob(oof,len(train));prob(valid,len(hold))
    with np.load(directory/'cache.npz',allow_pickle=False) as z:
        for key,value in [('train_idx',train),('valid_idx',hold),('train_id',ids[train]),('valid_id',ids[hold]),('atom_fold',fold)]:
            if not np.array_equal(z[key],value):raise ValueError('cache row/fold identity mismatch')
        np.testing.assert_array_equal(z['oof_proba'],oof);np.testing.assert_allclose(z['valid_proba'],valid,atol=1e-15,rtol=0)
    return oof,valid,paths,sha(directory/'cache.npz')

def main():
    complete=json.loads((HERE/'cache_complete.json').read_text());pre=json.loads((HERE/'preflight.json').read_text());pr=json.loads((HERE/'preregistration.json').read_text())
    if pre['contract']['verifier_sha256']!=sha(Path(__file__)) or pre['contract']['runner_sha256']!=sha(HERE/'run.py') or pre['contract']['prereg_sha256']!=sha(HERE/'preregistration.json'):raise ValueError('P3 code/protocol changed after preflight')
    if complete['status']!='COMPLETE_UNSCORED' or complete['atoms']!=600 or complete['ct_caches']!=5 or complete['contract_sha256']!=pre['contract_sha256'] or pre['baseline_role']!='FAITHFUL_ONLINE_V100_ALGORITHM' or pre['old_AB_gate_inherited'] or complete['archived_new_cpu_A_score_used'] or complete['candidate_selected_before_U_scoring']!='P3_INTERNAL_C':raise ValueError('P3 complete contract invalid')
    if pr['candidate_graph']!='V80 + C where C=0.5*(original V85+grouped V85) -> original V90 -> original V100 with same-T/U CT':raise ValueError('P3 candidate formula drift')
    mapping=json.loads((DIAG/'feature_origin_map.json').read_text());names=mapping['final_features'];origins=[mapping['feature_to_origin'][name] for name in names]
    base=cpu.load_config();groups=mapping['groups_zero_based']
    frame=pd.read_csv(PROJECT/'data/train.csv',usecols=['id','Will_Buy_EV']);ids=frame.id.to_numpy(np.int64);y=frame.Will_Buy_EV.eq('Yes').to_numpy(np.int8)
    with np.load(ARCH/'splits.npz',allow_pickle=False) as z:splits={name:z[name] for name in z.files}
    baseline=np.full(len(y),np.nan);candidate=np.full(len(y),np.nan);foldid=np.zeros(len(y),np.int8);coverage=np.zeros(len(y),np.int8);leaf_paths=0;reports=[]
    for outer in range(1,6):
        train=splits[f'outer_{outer:02d}_train_idx'];hold=splits[f'outer_{outer:02d}_valid_idx'];family={}
        for label in ('v80','v85','grouped_v85'):
            name='v85' if label=='grouped_v85' else label
            family[label]=reconstructed_family(outer,label,train,hold,splits[f'outer_{outer:02d}_{name}_fold'],ids,y,pre['contract_sha256'],names,origins,base,groups)
            leaf_paths+=family[label][2]
        ct_dir=GPU/f'outer_{outer:02d}';ct_manifest=json.loads((ct_dir/'cache_manifest.json').read_text())
        if ct_manifest['cache_sha256']!=sha(ct_dir/'cache.npz') or pre['ct_audit']['outer_caches'][outer-1]['cache_sha256']!=sha(ct_dir/'cache.npz'):raise ValueError('CT cache changed after preflight')
        with np.load(ct_dir/'cache.npz',allow_pickle=False) as z:
            for key,value in [('train_idx',train),('valid_idx',hold),('train_id',ids[train]),('valid_id',ids[hold]),('atom_fold',splits[f'outer_{outer:02d}_ct_fold'])]:
                if not np.array_equal(z[key],value):raise ValueError('CT row/fold drift')
            ct_oof=z['oof_proba'].astype(float);ct_u=z['valid_proba_fullfit'].astype(float)
        old90_oof,old90_u,old_weights=meta90(y[train],family['v80'][0],family['v85'][0],family['v80'][1],family['v85'][1])
        _,old100_u,old_ct_weight=meta100(y[train],old90_oof,ct_oof,old90_u,ct_u)
        c_oof=.5*(family['v85'][0]+family['grouped_v85'][0]);c_u=.5*(family['v85'][1]+family['grouped_v85'][1])
        new90_oof,new90_u,new_weights=meta90(y[train],family['v80'][0],c_oof,family['v80'][1],c_u)
        _,new100_u,new_ct_weight=meta100(y[train],new90_oof,ct_oof,new90_u,ct_u)
        for label,second_oof,second_u,independent,weights,weight in [('baseline',family['v85'][0],family['v85'][1],old100_u,old_weights,old_ct_weight),('candidate',c_oof,c_u,new100_u,new_weights,new_ct_weight)]:
            exact=cpu.fit_v100_meta(y[train],family['v80'][0],second_oof,ct_oof,family['v80'][1],second_u,ct_u,ct_u)
            np.testing.assert_allclose(independent,exact['refit_prediction'],atol=1e-12,rtol=0)
            if weights!=exact['v90_fold_weights'] or abs(weight-exact['ct_final_weight'])>1e-15:raise ValueError(f'{label} online meta weights differ')
        prob(old100_u,len(hold));prob(new100_u,len(hold));baseline[hold]=old100_u;candidate[hold]=new100_u;foldid[hold]=outer;coverage[hold]+=1
        reports.append({'outer':outer,'rows':len(hold),'v80_cache_sha256':family['v80'][3],'v85_cache_sha256':family['v85'][3],'grouped_cache_sha256':family['grouped_v85'][3],'ct_cache_sha256':sha(ct_dir/'cache.npz'),'baseline_v90_weights':old_weights,'candidate_v90_weights':new_weights,'baseline_ct_full_T_weight':old_ct_weight,'candidate_ct_full_T_weight':new_ct_weight,'outer_U_labels_used':False})
    if not np.all(coverage==1):raise ValueError('outer U coverage invalid')
    prob(baseline,len(y));prob(candidate,len(y))
    audit={'status':'PASS_UNSCORED_P3','contract_sha256':pre['contract_sha256'],'candidate':'P3_INTERNAL_C','baseline_role':'FAITHFUL_ONLINE_V100_ALGORITHM','checked_cpu_models':600,'checked_ct_prediction_caches':5,'grouped_leaf_paths_checked':leaf_paths,'cross_group_paths':0,'outer_reports':reports,'baseline_vector_sha256':hashlib.sha256(baseline.tobytes()).hexdigest(),'candidate_vector_sha256':hashlib.sha256(candidate.tobytes()).hexdigest(),'archived_new_cpu_A_used':False,'old_AB_branch_qualification_inherited':False,'historically_exposed_data':True,'CT_model_state_bytes_archived':False}
    cpu.atomic_json(HERE/'verification.json',audit)
    # First new outer U-label score occurs only after every source/model/row/meta check.
    b=float(roc_auc_score(y,baseline));c=float(roc_auc_score(y,candidate));folds=[]
    for outer in range(1,6):
        idx=foldid==outer;ba=float(roc_auc_score(y[idx],baseline[idx]));ca=float(roc_auc_score(y[idx],candidate[idx]));folds.append({'fold':outer,'baseline_auc':ba,'candidate_auc':ca,'delta':ca-ba})
    gate=c>b and all(row['delta']>0 for row in folds)
    result={'status':'COMPLETE_E2E_CONFIRMATION_P3','candidate':'P3_INTERNAL_C','baseline_role':'FAITHFUL_ONLINE_V100_ALGORITHM','baseline_auc':b,'candidate_auc':c,'delta':c-b,'folds':folds,'positive_folds':sum(row['delta']>0 for row in folds),'gate_passed':gate,'research_plus_0_0001':gate and c-b>=.0001,'verification_sha256':sha(HERE/'verification.json'),'development_result_sha256':pre['contract']['development_result_sha256'],'historically_exposed_data':True,'is_new_blind_test':False,'old_new_cpu_A_score_used':False,'submission_allowed_from_this_result_alone':False}
    cpu.atomic_json(HERE/'e2e_results.json',result)
    print(json.dumps({'status':result['status'],'baseline':b,'candidate':c,'delta':c-b,'positive_folds':result['positive_folds'],'gate':gate,'checked_leaf_paths':leaf_paths}))
if __name__=='__main__':main()
