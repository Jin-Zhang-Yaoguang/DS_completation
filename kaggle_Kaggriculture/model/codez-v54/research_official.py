"""Official-engine acceptance backend; the frozen fast simulator remains unchanged."""
import argparse
import contextlib
import copy
import io
import types
import research

_FAST_ONE=research.one
_KE=None

class OfficialGame:
    def __init__(self,seed):
        global _KE
        if _KE is None:
            with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                import kaggle_environments
                _KE=kaggle_environments
            assert _KE.__version__=='1.32.7',_KE.__version__
        self.env=_KE.make('kaggriculture',configuration={'seed':seed},debug=True)
        self.env.reset(2)
        assert self.env.info['seed']==seed
    @property
    def done(self):return self.env.done
    def observe(self,p):
        obs=dict(self.env.state[0].observation)
        obs.update(dict(self.env.state[p].observation))
        return copy.deepcopy(obs)
    def step(self,a,b):self.env.step([a,b])
    def reward(self,p):return self.env.state[p].reward

def official_one(job):
    assert job.get('backend')=='official_1.32.7'
    research.engine=lambda:types.SimpleNamespace(Game=OfficialGame)
    return _FAST_ONE(job)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('manifest');ap.add_argument('--workers',type=int,default=4)
    a=ap.parse_args();research.one=official_one;research.run(a.manifest,a.workers)
