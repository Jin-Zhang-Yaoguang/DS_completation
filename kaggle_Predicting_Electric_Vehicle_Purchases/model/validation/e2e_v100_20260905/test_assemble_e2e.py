"""Synthetic assembly tests. No true cache, no competition score."""
import json
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import assemble_e2e as a
import cpu_runner as cpu


class AssemblyTests(unittest.TestCase):
    def complete_supervisors(self):
        phases=["START","BEFORE_bootstrap.py","AFTER_EXIT_bootstrap.py","AFTER_CLEANUP_bootstrap.py","BEFORE_cache_runner.py","AFTER_EXIT_cache_runner.py","AFTER_CLEANUP_cache_runner.py","BEFORE_COMPLETE"]
        state={"status":"CPU_CACHE_COMPLETE","completed_atoms":400,"config_sha256":"cpu","complete_v100_scored":False,"pid":11}
        budget={"pid":11,"spent_seconds":100.,"peak_rss_bytes":1000}
        gpu={"status":"GPU_CACHE_RUN_COMPLETE","seconds":8.,"peak_process_tree_rss":1000,"resource_checks":[{"phase":phase,"seconds":float(i+1),"rss_bytes":1000,"peak_process_tree_rss":1000} for i,phase in enumerate(phases)]}
        return state,budget,gpu,"cpu"

    def test_gpu_cache_complete_cannot_override_supervisor_failure_or_budget(self):
        args=self.complete_supervisors(); a.require_supervisors(*args)
        for field,value in (("status","GPU_CACHE_RUN_FAILED"),("seconds",7200.),("seconds",7201.),("peak_process_tree_rss",24*1024**3+1)):
            changed=copy.deepcopy(args); changed[2][field]=value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): a.require_supervisors(*changed)

    def test_cpu_all_caches_cannot_override_incomplete_supervisor_or_budget(self):
        args=self.complete_supervisors()
        for position,field,value in ((0,"status","RUNNING"),(0,"completed_atoms",399),(0,"config_sha256","wrong"),(1,"spent_seconds",43200.1),(1,"peak_rss_bytes",24*1024**3+1),(1,"pid",99)):
            changed=copy.deepcopy(args); changed[position][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): a.require_supervisors(*changed)

    def test_gpu_final_before_complete_check_is_required(self):
        args=self.complete_supervisors(); args[2]["resource_checks"]=args[2]["resource_checks"][:-1]
        with self.assertRaises(ValueError): a.require_supervisors(*args)
    def ct_fixture(self,d):
        train=np.arange(10); hold=np.arange(10,14); ids=np.arange(100,114)
        folds=np.arange(10,dtype=np.int8)%5
        cfg={"source_sha256":{"train.csv":"trainhash"}}
        identity={"train_idx_sha256":cpu.arr_sha(train),"valid_idx_sha256":cpu.arr_sha(hold),"train_id_sha256":cpu.arr_sha(ids[train]),"valid_id_sha256":cpu.arr_sha(ids[hold]),"config_sha256":"gpu"}
        oof=np.zeros(10,dtype=np.float32); mean=np.zeros(4); records=[]
        for atom in range(1,6):
            local=np.flatnonzero(folds==atom-1); fit=np.flatnonzero(folds!=atom-1)
            op=np.array([.11,.29])+atom*.01; vp=np.arange(4)*.1+atom*.01
            cpu.atomic_npz(d/f"atom_{atom:02d}.npz",fit_idx=train[fit],hold_idx=train[local],valid_idx=hold,oof_proba=op,valid_proba=vp)
            record={"atom":atom,"identity":identity,"sha256":cpu.sha(d/f"atom_{atom:02d}.npz"),"seconds":1.}
            cpu.atomic_json(d/f"atom_{atom:02d}.json",record); records.append(record)
            oof[local]=op; mean+=vp/5
        full=np.array([.1,.3,.4,.7])
        cpu.atomic_npz(d/"fullfit.npz",valid_idx=hold,valid_proba=full)
        fr={"identity":identity,"sha256":cpu.sha(d/"fullfit.npz"),"seconds":1.}
        cpu.atomic_json(d/"fullfit.json",fr)
        cpu.atomic_npz(d/"cache.npz",train_idx=train,valid_idx=hold,train_id=ids[train],valid_id=ids[hold],oof_proba=oof,valid_proba_fullfit=full,valid_proba_foldmean=mean,atom_fold=folds)
        m={"status":"CT_CACHE_COMPLETE_UNSCORED","identity":identity,"cache_sha256":cpu.sha(d/"cache.npz"),"atoms":records,"fullfit":fr,"atom_fold_sha256":cpu.arr_sha(folds),"validation_labels_used":False,"allowed_for_submission":False,"source_sha256":cfg["source_sha256"]}
        cpu.atomic_json(d/"cache_manifest.json",m)
        return train,hold,ids,folds,cfg,"gpu"

    def test_missing_cache_is_rejected_before_reading_any_labels(self):
        with patch.object(a,"required_files",return_value=[a.OUT/'synthetic_missing/cache.npz']), patch.object(a.pd,"read_csv",side_effect=AssertionError("labels must not be loaded")):
            with self.assertRaises(FileNotFoundError): a.inputs()

    def test_ct_rebuild_and_float32_contract_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); args=self.ct_fixture(d)
            actual=a.check_ct(d,*args)
            self.assertEqual(actual["oof_proba"].dtype,np.float32)

    def test_ct_foreign_id_cannot_pass_even_with_updated_file_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); args=self.ct_fixture(d)
            z=a.read_npz(d/"cache.npz"); z["valid_id"][0]=99999
            cpu.atomic_npz(d/"cache.npz",**z)
            m=json.loads((d/"cache_manifest.json").read_text()); m["cache_sha256"]=cpu.sha(d/"cache.npz"); cpu.atomic_json(d/"cache_manifest.json",m)
            with self.assertRaisesRegex(ValueError,"identity"): a.check_ct(d,*args)

    def test_ct_wrong_atom_folds_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); args=self.ct_fixture(d)
            wrong=args[3].copy(); wrong[[0,1]]=wrong[[1,0]]
            with self.assertRaises(ValueError): a.check_ct(d,args[0],args[1],args[2],wrong,args[4],args[5])

    def test_ct_foldmean_must_equal_atom_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); args=self.ct_fixture(d)
            z=a.read_npz(d/"cache.npz"); z["valid_proba_foldmean"]+=.001
            cpu.atomic_npz(d/"cache.npz",**z)
            m=json.loads((d/"cache_manifest.json").read_text()); m["cache_sha256"]=cpu.sha(d/"cache.npz"); cpu.atomic_json(d/"cache_manifest.json",m)
            with self.assertRaisesRegex(ValueError,"reconstruction"): a.check_ct(d,*args)

    def test_cpu_40_atoms_rebuild_and_corruption_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); train=np.arange(80); hold=np.arange(80,84); ids=np.arange(100,184); folds=np.arange(80,dtype=np.int8)%40
            oof=np.zeros(80); mean=np.zeros(4); hashes={}
            for atom in range(1,41):
                part=d/f"atom_{atom:02d}"; part.mkdir()
                local=np.flatnonzero(folds==atom-1); fit=np.flatnonzero(folds!=atom-1)
                op=np.array([.1,.2])+atom*.001; vp=np.arange(4)*.1+atom*.001
                cpu.atomic_npz(part/"predictions.npz",oof_idx=train[local],valid_idx=hold,oof_id=ids[train[local]],valid_id=ids[hold],oof_proba=op,valid_proba=vp)
                (part/"model.txt").write_text('fixture')
                cpu.atomic_json(part/"manifest.json",{"config_sha256":"cpu","outer":1,"family":"v80","atom":atom,"fit_idx_sha256":cpu.arr_sha(train[fit]),"query_idx_sha256":cpu.arr_sha(np.concatenate([train[local],hold])),"prediction_sha256":cpu.sha(part/"predictions.npz"),"model_sha256":cpu.sha(part/"model.txt"),"query_labels_available":False,"final_fit_eval_set_used":False,"outer_hold_labels_used":False})
                hashes[str(atom)]=cpu.sha(part/"manifest.json"); oof[local]=op; mean+=vp/40
            cpu.atomic_npz(d/"cache.npz",train_idx=train,valid_idx=hold,train_id=ids[train],valid_id=ids[hold],atom_fold=folds,oof_proba=oof,valid_proba=mean)
            m={"status":"CPU_CACHE_COMPLETE","outer":1,"family":"v80","config_sha256":"cpu","input_sha256":"input","splits_sha256":"split","cache_sha256":cpu.sha(d/"cache.npz"),"atom_manifest_sha256":hashes}
            for name,v in (("train_idx",train),("valid_idx",hold),("train_id",ids[train]),("valid_id",ids[hold])): m[name+"_sha256"]=cpu.arr_sha(v)
            cpu.atomic_json(d/"cache_manifest.json",m)
            a.check_cpu(d,1,"v80",train,hold,ids,folds,"cpu","input","split")
            first=d/"atom_01"; original=a.read_npz(first/"predictions.npz")
            record=json.loads((first/"manifest.json").read_text())
            for malformed in (original["oof_proba"][:1],original["oof_proba"].astype(np.float32)):
                changed=dict(original); changed["oof_proba"]=malformed
                cpu.atomic_npz(first/"predictions.npz",**changed)
                record["prediction_sha256"]=cpu.sha(first/"predictions.npz"); cpu.atomic_json(first/"manifest.json",record)
                m["atom_manifest_sha256"]["1"]=cpu.sha(first/"manifest.json"); cpu.atomic_json(d/"cache_manifest.json",m)
                with self.assertRaises(ValueError): a.check_cpu(d,1,"v80",train,hold,ids,folds,"cpu","input","split")
            cpu.atomic_npz(first/"predictions.npz",**original)
            record["prediction_sha256"]=cpu.sha(first/"predictions.npz"); cpu.atomic_json(first/"manifest.json",record)
            m["atom_manifest_sha256"]["1"]=cpu.sha(first/"manifest.json"); cpu.atomic_json(d/"cache_manifest.json",m)
            (d/"atom_40/model.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError,"model hash"): a.check_cpu(d,1,"v80",train,hold,ids,folds,"cpu","input","split")

    def test_independent_full_meta_matches_original_two_layers(self):
        rng=np.random.default_rng(987); y=np.tile([0,1],150)
        atoms=[np.clip(.2+.55*y+rng.normal(size=len(y))*.12,.001,.999) for _ in range(3)]
        query=[rng.uniform(.01,.99,44) for _ in range(4)]
        args=(y,*atoms,*query)
        original=cpu.fit_v100_meta(*args); independent=a.independent_meta(*args)
        for key in ("refit_prediction","foldmean_prediction"):
            np.testing.assert_allclose(original[key],independent[key],atol=1e-12,rtol=0)
        self.assertEqual(original["v90_fold_weights"],independent["v90_fold_weights"])
        self.assertEqual(original["ct_final_weight"],independent["ct_final_weight"])

    def test_positive_small_delta_only_opens_candidate_rebuild_gate(self):
        n=1000; y=np.tile(np.r_[np.zeros(n),np.ones(n)],5).astype(np.int8)
        folds=np.repeat(np.arange(1,6),2*n)
        candidate=np.tile(np.r_[np.linspace(.1,.4,n),np.linspace(.6,.9,n)],5)
        baseline=candidate.copy()
        for f in range(5): baseline[f*2*n+n]=.3999
        r=a.score_vectors(y,baseline,candidate,folds,True)
        self.assertGreater(r["delta"],0); self.assertLess(r["delta"],.0001)
        self.assertEqual(r["positive_folds"],5)
        self.assertFalse(r["research_promotion_gate_passed"])
        self.assertTrue(r["submission_candidate_rebuild_gate_passed"])
        self.assertFalse(r["allowed_for_submission"])

    def test_missing_verification_or_fold_never_scores(self):
        y=np.tile([0,1],50); baseline=np.linspace(.1,.9,100); candidate=baseline.copy(); folds=np.repeat(np.arange(1,6),20)
        with self.assertRaises(ValueError): a.score_vectors(y,baseline,candidate,folds,False)
        folds[folds==5]=4
        with self.assertRaises(ValueError): a.score_vectors(y,baseline,candidate,folds,True)


if __name__=="__main__": unittest.main(verbosity=2)
