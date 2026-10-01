"""Small synthetic isolation and checkpoint-integrity tests; no competition fit."""
import inspect
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import expit
import cpu_runner as run
from feature_backends import Backend, module_at


class IsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rng=np.random.default_rng(911)
        cls.raw=cls.rng.normal(size=(300,2))
        cls.labels=(cls.raw[:,0]+cls.rng.normal(size=300)*.7>0).astype(np.int8)
        cls.fit=np.arange(240); cls.query=np.arange(240,300)
        cls.params={"n_estimators":25,"learning_rate":.1,"num_leaves":7,"max_depth":3,"min_child_samples":5,"n_jobs":1,"random_state":13,"verbosity":-1,"deterministic":True,"force_col_wise":True}
        v80=module_at(run.PROJECT/"model/v80_strict_v61_outer104395303_40f/v80_strict_v61_outer104395303_40f.py","test_e2e_v80")
        cls.b80=Backend("v80",pd.DataFrame(cls.raw,columns=["a","b"]),keys={"bucket":np.arange(300,dtype=np.int32)%19},strict_encoder=v80.strict_encode_key)
        cls.b85=Backend("v85",pd.DataFrame({"a":cls.raw[:,0],"b":cls.raw[:,1],"bucket":(np.arange(300)%19).astype(str)}),te_columns=["bucket"])

    def test_query_labels_are_absent_from_api(self):
        self.assertNotIn("query_y",inspect.signature(run.fit_atom).parameters)
        self.assertNotIn("valid_y",inspect.signature(run.fit_atom).parameters)
        self.assertNotIn("query_labels",inspect.signature(Backend.encode).parameters)

    def test_v85_encoded_matrices_match_original_recipe(self):
        original=module_at(run.PROJECT/"model/v85_naji_v74_40f/v85_naji_v74_40f.py","test_e2e_v85_matrix")
        actual_fit,actual_query,names=self.b85.encode(self.fit,self.labels[self.fit],self.query,43)
        old_fit,old_query,_=original.encode_naji_fold(self.b85.static,pd.Series(self.labels),self.b85.static.iloc[self.query],self.b85.te_columns,self.fit,self.query,1)
        self.assertEqual(names,list(old_fit.columns))
        np.testing.assert_array_equal(actual_fit,old_fit.to_numpy())
        np.testing.assert_array_equal(actual_query,old_query.to_numpy())

    def test_both_families_ignore_outer_hold_labels(self):
        flipped=self.labels.copy(); flipped[self.query]=1-flipped[self.query]
        for backend in (self.b80,self.b85):
            a,sa,_=run.fit_atom(backend,self.fit,self.labels[self.fit],self.query,self.params,43,717,4)
            b,sb,_=run.fit_atom(backend,self.fit,flipped[self.fit],self.query,self.params,43,717,4)
            np.testing.assert_array_equal(a,b)
            self.assertEqual(sa,sb)
            self.assertFalse(sa["query_labels_available"])
            self.assertFalse(sa["final_fit_eval_set_used"])

    def test_overlap_is_rejected(self):
        with self.assertRaises(ValueError):
            run.fit_atom(self.b80,self.fit,self.labels[self.fit],np.arange(230,250),self.params,43,717,4)

    def test_training_labels_actually_change_the_fit(self):
        a,_,_=run.fit_atom(self.b85,self.fit,self.labels[self.fit],self.query,self.params,43,717,4)
        b,_,_=run.fit_atom(self.b85,self.fit,1-self.labels[self.fit],self.query,self.params,43,717,4)
        self.assertGreater(float(np.max(np.abs(a-b))),.01)

    def test_early_stop_rounds_do_not_depend_on_query_features(self):
        altered=self.b85.static.copy(); altered.loc[self.query,["a","b"]]=10000
        backend=Backend("v85",altered,te_columns=["bucket"])
        _,sa,_=run.fit_atom(self.b85,self.fit,self.labels[self.fit],self.query,self.params,43,717,4)
        _,sb,_=run.fit_atom(backend,self.fit,self.labels[self.fit],self.query,self.params,43,717,4)
        self.assertEqual(sa["selected_iteration"],sb["selected_iteration"])
        self.assertEqual(sa["early_valid_idx_sha256"],sb["early_valid_idx_sha256"])

    def test_checkpoint_config_and_payload_corruption_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            d=Path(name)
            (d/"model.txt").write_text("synthetic fixture only")
            run.atomic_npz(d/"predictions.npz",oof_proba=np.array([.2,.8]),valid_proba=np.array([.1,.9]))
            run.atomic_json(d/"manifest.json",{"config_sha256":"frozen","prediction_sha256":run.sha(d/"predictions.npz"),"model_sha256":run.sha(d/"model.txt")})
            run.verify_atom(d,"frozen")
            with self.assertRaises(ValueError): run.verify_atom(d,"changed")
            with (d/"predictions.npz").open("ab") as f: f.write(b"corruption")
            with self.assertRaises(ValueError): run.verify_atom(d,"frozen")

    def test_full_v100_meta_shares_weights_between_query_contracts(self):
        rng=np.random.default_rng(772)
        y=np.tile([0,1],120)
        signal=y*.8+rng.normal(size=len(y))*.5
        atoms=[expit(signal+rng.normal(size=len(y))*.2) for _ in range(3)]
        queries=[rng.uniform(.02,.98,31) for _ in range(3)]
        result=run.fit_v100_meta(y,*atoms,*queries,queries[2])
        np.testing.assert_array_equal(result["refit_prediction"],result["foldmean_prediction"])
        self.assertEqual(len(result["v90_fold_weights"]),5)
        self.assertIn(round(result["ct_final_weight"],3),[round(.025*i,3) for i in range(21)])
        self.assertFalse(result["outer_hold_labels_used"])


if __name__=="__main__": unittest.main(verbosity=2)
