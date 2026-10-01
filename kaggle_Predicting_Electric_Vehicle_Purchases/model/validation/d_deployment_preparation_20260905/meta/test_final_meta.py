"""Only synthetic inputs and temporary files; never loads existing prediction arrays."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
import final_meta as m


def synthetic(seed=913):
    rng = np.random.default_rng(seed)
    y = np.tile([0, 1], 100).astype(np.int32)
    train_id = np.arange(200, dtype=np.int64)
    test_id = np.arange(1000, 1009, dtype=np.int64)
    v90_oof = np.clip(.2 + .6*y + rng.normal(0, .3, len(y)), 0, 1).astype(np.float64)
    v90_test = rng.uniform(0, 1, len(test_id)).astype(np.float64)
    cache = {"train_id": train_id.copy(), "test_id": test_id.copy(), "oof_proba": np.full(len(y), np.nan, np.float32),
             "test_proba_foldmean": np.zeros(len(test_id), np.float64), "atom_fold": np.full(len(y), -1, np.int8)}
    atoms = []
    for fold, (fit, hold) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y)):
        raw_oof = np.clip(.3 + .4*y[hold] + rng.normal(0, .25, len(hold)), 0, 1).astype(np.float64)
        raw_test = rng.uniform(0, 1, len(test_id)).astype(np.float64)
        atoms.append({"fit_idx": fit, "hold_idx": hold, "fit_id": train_id[fit], "hold_id": train_id[hold],
                      "test_id": test_id.copy(), "oof_proba": raw_oof, "test_proba": raw_test})
        cache["oof_proba"][hold] = raw_oof.astype(np.float32)
        cache["atom_fold"][hold] = fold
        cache["test_proba_foldmean"] += raw_test / 5
    return train_id, test_id, y, v90_oof, v90_test, cache, atoms


def fit_args(inputs):
    _, _, y, v90_oof, v90_test, cache, _ = inputs
    return y, v90_oof, cache["oof_proba"], v90_test, cache["test_proba_foldmean"]


def receipt():
    return {"status": "VERIFIED_D_REBUILD_ELIGIBLE", "candidate_rebuild_eligible": True,
            "selected_candidate": "D", "candidate": "D", "baseline": "C",
            "execution_authorized": False, "allowed_for_submission": False,
            "bound_sources": {"comparison_config.json": "a"*64},
            "terminal_artifacts": {"comparison/results.json": "b"*64}, "readiness_gate_sha256": "c"*64}


class FinalMetaTests(unittest.TestCase):
    def test_matches_historical_final_stage_and_independent_formula(self):
        arrays = synthetic()
        m.validate_global_arrays(*arrays)
        args = fit_args(arrays)
        actual = m.final_fit(*args)
        historical = m.reference().nested_blend(*args)
        self.assertEqual(actual["selected_ct_weight"], historical["final_ctboost_weight"])
        np.testing.assert_array_equal(actual["test_proba"], historical["test"])
        self.assertEqual(m.verify_final(actual, *args)["status"], "INDEPENDENT_FINAL_META_PASS")

    def test_new_ct_selects_weight_instead_of_copying_old_point2(self):
        y = np.tile([0, 1], 100).astype(np.int32)
        args = y, np.full(len(y), .5, np.float64), (.1 + .8*y).astype(np.float32), np.array([.2, .8]), np.array([.1, .9])
        result = m.final_fit(*args)
        self.assertEqual(result["selected_ct_weight"], .025)
        self.assertNotEqual(result["selected_ct_weight"], .2)
        m.verify_final(result, *args)

    def test_exact_auc_tie_keeps_smallest_ct_weight(self):
        y = np.tile([0, 1], 64).astype(np.int32)
        args = y, np.full(len(y), .5, np.float64), np.full(len(y), .5, np.float32), np.array([.2, .8]), np.array([.1, .9])
        result = m.final_fit(*args)
        self.assertEqual(result["selected_ct_weight"], 0.)
        m.verify_final(result, *args)

    def test_ecdf_duplicate_values_and_below_above_boundaries(self):
        reference = np.array([.2, .2, .5, .9], np.float64)
        query = np.array([.1, .2, .35, .5, .9, 1.], np.float64)
        expected = np.array([0., .25, .5, .625, .875, 1.])
        np.testing.assert_array_equal(m.independent_ecdf(reference, query), expected)
        np.testing.assert_array_equal(m.reference().transform_mid_ecdf(m.reference().fit_mid_ecdf(reference), query), expected)

    def test_float32_oof_is_promoted_without_inventing_lost_precision(self):
        args = fit_args(synthetic())
        result = m.final_fit(*args)
        self.assertEqual(result["ct_ecdf_state"].dtype, np.dtype("float64"))
        np.testing.assert_array_equal(result["ct_ecdf_state"], np.sort(args[2].astype(np.float64)))

    def test_test_values_cannot_change_fitted_weight_or_ecdf(self):
        args = fit_args(synthetic())
        first = m.final_fit(*args)
        second = m.final_fit(*args[:3], 1-args[3], 1-args[4])
        self.assertEqual(first["selected_ct_weight"], second["selected_ct_weight"])
        for key in ("v90_ecdf_state", "ct_ecdf_state"):
            np.testing.assert_array_equal(first[key], second[key])

    def test_independent_rebuild_does_not_call_primary_helpers(self):
        args = fit_args(synthetic())
        actual = m.final_fit(*args)
        with patch.object(m, "reference", side_effect=AssertionError("independent path used primary")):
            m.verify_final(actual, *args)

    def test_independent_auc_matches_sklearn_on_ties_and_reversed_order(self):
        rng = np.random.default_rng(61)
        for size in (20, 100, 256):
            y = np.tile([0, 1], size//2).astype(np.int32)
            scores = rng.integers(0, 6, size=size).astype(np.float64)
            self.assertEqual(m.independent_auc(y, scores), roc_auc_score(y, scores))
            self.assertEqual(m.independent_auc(y, -scores), roc_auc_score(y, -scores))

    def test_independent_weight_mismatch_fails_instead_of_new_tolerance(self):
        args = fit_args(synthetic())
        actual = m.final_fit(*args)
        other = .5 if actual["selected_ct_weight"] != .5 else 0.
        actual["selected_ct_weight"] = other
        with self.assertRaisesRegex(ValueError, "selected weight"):
            m.verify_final(actual, *args)

    def test_changed_final_prediction_or_scope_is_rejected(self):
        args = fit_args(synthetic())
        actual = m.final_fit(*args)
        actual["test_proba"][0] += .0001
        with self.assertRaisesRegex(ValueError, "prediction"):
            m.verify_final(actual, *args)
        actual = m.final_fit(*args); actual["is_unbiased_validation"] = True
        with self.assertRaisesRegex(ValueError, "scope"):
            m.verify_final(actual, *args)
        actual = m.final_fit(*args); actual['ct_ecdf_state'] = actual['ct_ecdf_state'].astype(np.float32)
        with self.assertRaisesRegex(ValueError,'state dtype'):
            m.verify_final(actual,*args)

    def test_wrong_global_and_fold_ids_are_rejected(self):
        for where in ("cache", "atom"):
            arrays = synthetic()
            target = arrays[5] if where == "cache" else arrays[6][0]
            target["test_id"] = target["test_id"][::-1]
            with self.assertRaisesRegex(ValueError, "ID|identity"):
                m.validate_global_arrays(*arrays)

    def test_missing_duplicate_or_permuted_ct_fold_is_rejected(self):
        for mode in ("missing", "duplicate", "permuted"):
            arrays = synthetic(); atoms = arrays[-1]
            if mode == "missing": atoms.pop()
            elif mode == "duplicate": atoms[-1] = copy.deepcopy(atoms[0])
            else: atoms[0], atoms[1] = atoms[1], atoms[0]
            with self.assertRaises(ValueError):
                m.validate_global_arrays(*arrays)

    def test_old_oof_cannot_be_paired_with_new_fold_tests(self):
        arrays = synthetic()
        arrays[5]["oof_proba"][0] = np.float32(.12345)
        with self.assertRaisesRegex(ValueError, "this batch"):
            m.validate_global_arrays(*arrays)

    def test_cached_mean_must_rebuild_from_all_five_current_tests(self):
        arrays = synthetic()
        arrays[6][4]["test_proba"][0] += .01
        with self.assertRaisesRegex(ValueError, "batch/order"):
            m.validate_global_arrays(*arrays)

    def test_ct_precision_and_scalar_broadcast_are_not_coerced(self):
        for key, change in (("oof_proba", lambda a:a.astype(np.float64)),
                            ("test_proba_foldmean", lambda a:a.astype(np.float32)),
                            ("test_proba_foldmean", lambda a:np.array(.5)),
                            ("atom_fold", lambda a:a.astype(np.int64))):
            arrays = synthetic(); arrays[5][key] = change(arrays[5][key])
            with self.assertRaisesRegex(ValueError, "dtype/shape"):
                m.validate_global_arrays(*arrays)

    def test_nonfinite_out_of_range_or_duplicate_official_id_is_rejected(self):
        for mode in ("nan", "range", "duplicate"):
            arrays = synthetic()
            if mode == "nan": arrays[3][0] = np.nan
            elif mode == "range": arrays[3][0] = 1.01
            else: arrays[0][0] = arrays[0][1]
            with self.assertRaises(ValueError):
                m.validate_global_arrays(*arrays)

    def test_receipt_boolean_without_live_d_qualification_is_insufficient(self):
        saved = receipt()
        for change in ({"status":"NOT_READY"}, {"candidate_rebuild_eligible":False}, {"selected_candidate":"B"}, {"execution_authorized":True}):
            with self.assertRaises(ValueError):
                m.validate_readiness({**saved, **change}, saved)

    def test_receipt_must_match_live_bound_sources_and_final_artifacts(self):
        saved = receipt(); m.validate_readiness(copy.deepcopy(saved), saved)
        for key in ("bound_sources", "terminal_artifacts", "readiness_gate_sha256"):
            changed = copy.deepcopy(saved); changed[key] = {"wrong":"d"*64} if isinstance(saved[key], dict) else "d"*64
            with self.assertRaisesRegex(ValueError, "differs"):
                m.validate_readiness(changed, saved)

    def test_production_missing_contract_or_authorization_never_loads_arrays(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(m.np, "load", side_effect=AssertionError("real input read")), \
             patch.object(m, "reference", side_effect=AssertionError("real weight fit")):
            root = Path(tmp); contract, auth = root/'contract.json', root/'START_AUTHORIZATION.json'
            for create_contract in (False, True):
                if create_contract: contract.write_text('{}')
                with self.assertRaisesRegex(ValueError, "PREPARATION_ONLY_NOT_AUTHORIZED"):
                    m.authorize_production(contract, auth, 'a'*64, 'b'*64)

    def test_preparation_config_or_untrusted_hashes_do_not_unlock_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); contract, auth = root/'contract.json', root/'START_AUTHORIZATION.json'
            contract.write_text(json.dumps({'status':m.STATUS, 'candidate':'D'})); auth.write_text('{}')
            with self.assertRaisesRegex(ValueError, "trusted expected"):
                m.authorize_production(contract, auth, None, None)
            with self.assertRaisesRegex(ValueError, "scope invalid"):
                m.authorize_production(contract, auth, m.sha(contract), m.sha(auth))

    def test_recursive_v90_source_closure_cannot_be_replaced_by_file_count(self):
        arrays = synthetic(); train_id, test_id = arrays[:2]
        identity = {"train_rows":len(train_id), "test_rows":len(test_id),
                    "train_id_sha256":m.id_text_sha(train_id), "test_id_sha256":m.id_text_sha(test_id)}
        refs = [{"path": f"members/deep_{i}/prediction.npy", "sha256": f"{i:064x}"} for i in range(27)]
        refs += [{"path": k, "sha256": v} for k, v in m.V90_DIGESTS.items()]
        original = {"deep":{"nested":[{"references":refs}]}, "row_identity":identity,
                    "row_identity_hash_contract":{"expected_row_identity":identity}, "member_row_identities":{"v80":identity,"v85":identity}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); path = root/'sources.json'; path.write_text(json.dumps(original))
            digest = m.sha(path)
            sources = {r['path']:r['sha256'] for r in refs}; sources['sources.json']=digest
            record = {"status":"VERIFIED_OLD_V90_GLOBAL_INPUTS","independent_reconstruction_passed":True,
                      "cpu_fit_rule":"F_TRAIN_H_EARLY_STOP_SAME_MODEL_NO_REFIT","v90_test_aggregation":"five_meta_folds_mean",
                      **identity, "source_files":sources}
            with patch.object(m,"PROJECT",root),patch.object(m,"V90_SOURCES","sources.json"),patch.object(m,"V90_SOURCES_SHA",digest):
                m.verify_v90_receipt(record, {'source_files':sources}, train_id, test_id)
                missing = copy.deepcopy(record); del missing['source_files'][refs[17]['path']]
                missing['source_files']['unrelated/filler.bin']='a'*64
                self.assertGreaterEqual(len(missing['source_files']),27)
                with self.assertRaisesRegex(ValueError,'deep source lineage'):
                    m.verify_v90_receipt(missing, {'source_files':missing['source_files']}, train_id,test_id)
                with self.assertRaisesRegex(ValueError,'row identity'):
                    m.verify_v90_receipt({**record,'test_id_sha256':m.id_text_sha(test_id[::-1])}, {'source_files':sources},train_id,test_id[::-1])

    def test_duplicate_v90_references_need_identical_hashes(self):
        ref={'path':'member/output.npy','sha256':'a'*64}
        self.assertEqual(m.nested_source_references({'a':ref,'deep':[ref]}),{ref['path']:ref['sha256']})
        with self.assertRaisesRegex(ValueError,'conflicting'):
            m.nested_source_references({'a':ref,'deep':[{'path':ref['path'],'sha256':'b'*64}]})

    def test_ct_archive_api_uses_local_root_and_keeps_remote_contract_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve(); artifact=output/'cache.bin'; artifact.write_bytes(b'synthetic cache')
            config={'ct_adapter':str((m.ROOT.parent/'ct/ct_runner.py').relative_to(m.PROJECT)),
                    'ct_config':'future/original_remote_config.json','ct_start_authorization':'future/original_remote_auth.json',
                    'ct_archive_map':'future/archive_map.json','qualification_receipt':'future/qualification.json','ct_cohort_id':'one-new-cohort',
                    'source_files':{'future/original_remote_config.json':'a'*64,'future/original_remote_auth.json':'b'*64,
                                    'future/archive_map.json':'c'*64,'future/qualification.json':'d'*64}}
            context={'mode':'ARCHIVE_READ_ONLY','artifact_root':str(output),'config_sha256':'a'*64,'start_authorization_sha256':'b'*64,
                     'config':{'output_dir':'/kaggle/working/unavailable-remote','qualification_receipt':{'sha256':'d'*64}}}
            proof={'status':'CT_GLOBAL5_SUPERVISED_COMPLETE_UNSCORED','allowed_for_submission':False,
                   'identity':{'cohort_id':'one-new-cohort','config_sha256':'a'*64,'start_authorization_sha256':'b'*64},
                   'files':{'cache.bin':m.sha(artifact)},'arrays':{}}
            adapter=Mock(); adapter.authorize_archived.return_value=context; adapter.require_successful_completion.return_value=proof
            with patch.object(m,'module',return_value=adapter):
                actual, local=m.verified_ct(config)
                self.assertEqual(local,output); self.assertEqual(actual,proof)
                self.assertEqual(context['config']['output_dir'],'/kaggle/working/unavailable-remote')
                adapter.authorize_contract.assert_not_called()
                adapter.require_successful_completion.assert_called_with(output,context)
                self.assertEqual(adapter.authorize_archived.call_args.args[-1],'c'*64)
                for changed in ('cohort','hash','mapping','terminal'):
                    with self.subTest(changed=changed):
                        bad=copy.deepcopy(proof);adapter.require_successful_completion.return_value=bad
                        if changed=='cohort': bad['identity']['cohort_id']='foreign-cohort'
                        elif changed=='hash': bad['files']['cache.bin']='e'*64
                        elif changed=='terminal': bad['status']='CT_GLOBAL5_CACHE_REBUILT_UNSCORED'
                        else: adapter.authorize_archived.side_effect=ValueError('archive path mapping mismatch')
                        with self.assertRaises(ValueError):m.verified_ct(config)
                        adapter.authorize_archived.side_effect=None

    def test_failed_ct_supervision_is_not_replaced_by_cache_only_validation(self):
        config={'ct_adapter':str((m.ROOT.parent/'ct/ct_runner.py').relative_to(m.PROJECT)),
                'ct_config':'future/cfg','ct_start_authorization':'future/auth','ct_archive_map':'future/map',
                'qualification_receipt':'future/receipt','source_files':{'future/cfg':'a'*64,'future/auth':'b'*64,
                'future/map':'c'*64,'future/receipt':'d'*64}}
        context={'mode':'ARCHIVE_READ_ONLY','artifact_root':'/does/not/need/to/exist',
                 'config':{'qualification_receipt':{'sha256':'d'*64}}}
        adapter=Mock();adapter.authorize_archived.return_value=context
        for failure in ('supervisor not complete','parent final budget violation','model/state SHA changed'):
            adapter.require_successful_completion.side_effect=ValueError(failure)
            with patch.object(m,'module',return_value=adapter),patch.object(m,'load_npz',side_effect=AssertionError('premature arrays')):
                with self.assertRaisesRegex(ValueError,failure):m.verified_ct(config)
            adapter.check_cache.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
