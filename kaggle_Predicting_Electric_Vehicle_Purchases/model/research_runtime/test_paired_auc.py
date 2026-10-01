"""用显式正负配对枚举核对统计工具的AUC、并列处理和输入约束。"""
import unittest
import numpy as np
from paired_auc import auc_components, paired_auc

def brute(y, p):
    y=np.asarray(y,dtype=bool);p=np.asarray(p)
    differences=p[y,None]-p[~y][None,:]
    return float(((differences>0)+0.5*(differences==0)).mean())

class PairedAucTest(unittest.TestCase):
    def test_exact_ties_and_random(self):
        rng=np.random.default_rng(91037)
        for n in [8,19,50]:
            for _ in range(10):
                y=np.arange(n)%2
                p=rng.integers(0,6,n)/5
                self.assertAlmostEqual(auc_components(y,p)[0],brute(y,p),places=14)
    def test_identical_predictions_have_zero_delta_and_se(self):
        result=paired_auc([0,1,0,1],[.2,.5,.5,.8],[.2,.5,.5,.8])
        self.assertEqual(result["delta"],0)
        self.assertEqual(result["conditional_standard_error"],0)
    def test_monotone_transform_preserves_comparison(self):
        y=np.array([0,1,1,0,1,0])
        p=np.array([.1,.3,.8,.5,.9,.2])
        self.assertEqual(paired_auc(y,p,np.exp(p))["delta"],0)
    def test_folds_and_positive_direction(self):
        y=[0,1,0,1,0,1,0,1]
        base=[.5]*8
        candidate=[0,1,0,1,0,1,0,1]
        result=paired_auc(y,base,candidate,[0,0,1,1,0,0,1,1])
        self.assertEqual(result["delta"],.5)
        self.assertEqual(result["positive_folds"],2)
    def test_invalid_inputs(self):
        for y,p in [([0,1],[.2]),([1,1],[.2,.3]),([0,2],[.2,.3]),([0,1],[float("nan"),.3])]:
            with self.assertRaises(ValueError):
                auc_components(y,p)
if __name__=="__main__":
    unittest.main()

