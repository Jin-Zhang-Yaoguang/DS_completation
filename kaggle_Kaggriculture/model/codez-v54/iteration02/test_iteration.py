import unittest
from finalize_iteration import matched

def row(seed,seat,margin,opponent='r14'):
    return {'job':{'seed':seed,'seat':seat,'opponent':opponent},'margin':margin}
class PairedEvidenceTests(unittest.TestCase):
    def test_missing_pair_rejected(self):
        with self.assertRaises(AssertionError):matched([row(1,0,1),row(1,1,1)],[row(1,0,2)])
    def test_duplicate_rejected(self):
        with self.assertRaises(AssertionError):matched([row(1,0,1),row(1,0,1)],[row(1,0,2),row(1,0,2)])
    def test_gain_does_not_hide_former_win_loss(self):
        out=matched([row(1,0,1),row(1,1,-100)],[row(1,0,-1),row(1,1,1000)])
        self.assertGreater(out['groups']['all']['margin_delta'],0)
        self.assertEqual(out['groups']['all']['win_regressions'],1)
        self.assertEqual(out['groups']['seat:0']['win_regressions'],1)
    def test_cluster_counts_seeds_not_seats_or_opponents(self):
        a=[row(s,t,1,o) for s in [1,2] for t in [0,1] for o in ['a','b']]
        b=[row(s,t,3,o) for s in [1,2] for t in [0,1] for o in ['a','b']]
        out=matched(a,b);self.assertEqual(out['seed_cluster']['seeds'],2)
        self.assertEqual(out['seed_cluster']['mean_margin_delta'],2)
        self.assertEqual(out['seed_cluster']['margin_delta_lower95'],2)
if __name__=='__main__':unittest.main()
