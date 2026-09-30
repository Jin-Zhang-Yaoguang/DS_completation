"""Regression tests for research validity, not strategy performance."""
import unittest
from evaluate import pair
from finalize import seed_test

def row(agent,seed,seat,margin):
    return {'job':{'agent':agent,'opponent':'rival','seed':seed,'seat':seat},
        'margin':margin,'observations':{'144':{'shops':['A','B']}},
        'telemetry':{'route_changes':1},'trace_sha256':f'{agent}:{seed}:{seat}'}

class EvaluationTests(unittest.TestCase):
    def test_missing_pair_cannot_be_silently_intersected(self):
        data=[row('versions/v000/main.py',1,0,1),row('candidate',2,0,2)]
        with self.assertRaises(AssertionError):pair(data,'candidate')

    def test_aggregate_gain_cannot_hide_seat_regression(self):
        data=[]
        for seed,seat,baseline,candidate in [(1,0,1,-1),(2,1,-1,2),(3,1,-1,2)]:
            data += [row('versions/v000/main.py',seed,seat,baseline),row('candidate',seed,seat,candidate)]
        result=pair(data,'candidate')
        self.assertGreater(result['groups']['all']['candidate_wins'],result['groups']['all']['baseline_wins'])
        self.assertFalse(result['paired_gate'])

    def test_duplicate_results_do_not_inflate_sample_size(self):
        base=row('versions/v000/main.py',1,0,1)
        with self.assertRaises(ValueError):pair([base,base,row('candidate',1,0,2)],'candidate')

    def test_cluster_test_does_not_count_seats_as_independent(self):
        pairs=[{'seed':seed,'baseline_margin':-1,'candidate_margin':1}
               for seed in range(10) for _ in range(6)]
        result=seed_test({'pairs':pairs})
        self.assertEqual(result['positive_seed_clusters'],10)
        self.assertEqual(result['one_sided_sign_p'],1/1024)

if __name__=='__main__':unittest.main()
