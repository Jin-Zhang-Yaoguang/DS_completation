"""Frozen, paired V54 research. No network, submission, or implicit PASS fallback."""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import traceback

ROOT = Path(__file__).resolve().parent
_CODES = {}
_ENGINE = None

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    path = str(Path(path).resolve())
    if path not in _CODES:
        _CODES[path] = compile(Path(path).read_text(), path, 'exec')
    ns = {}
    exec(_CODES[path], ns)
    # Kaggle submission loader selects the final callable after executing source.
    fn = [v for k, v in ns.items() if callable(v) and not k.startswith('__')][-1]
    return fn, ns

def engine():
    global _ENGINE
    if _ENGINE is None:
        p = next((ROOT/'frozen/engine').glob('kagsim*.so'))
        spec = importlib.util.spec_from_file_location('kagsim', p)
        _ENGINE = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ENGINE)
    return _ENGINE

def key(job):
    return hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()

def one(job):
    started = time.monotonic()
    out = {'job': job, 'key': key(job), 'status': 'error'}
    try:
        if any(k.startswith('KAG_FORCE_') for k in os.environ):
            raise RuntimeError('Research force-route environment variable is set')
        me, ns = load(ROOT/job['agent'])
        other, _ = load(ROOT/'frozen/opponents'/f"{job['opponent']}.py")
        seat = job['seat']; funcs = [None, None]
        funcs[seat] = me; funcs[1-seat] = other
        g = engine().Game(seed=job['seed'])
        h = hashlib.sha256(); steps = 0; max_seconds = 0.0
        seen = {}
        done = lambda: g.done() if callable(g.done) else g.done
        while not done():
            obs = [g.observe(0), g.observe(1)]
            step = int(obs[seat]['step'])
            if step in (2, 144, 150, 160, 216):
                o = obs[seat]
                seen[str(step)] = {'cash': round(float(o['farms'][1-seat]['money']),3),
                    'wheat': int(o['market']['inventory']['WHEAT']),
                    'shops': list(o['town'].get('unlocked_shops', []))}
            acts = []
            for p in (0,1):
                t = time.monotonic(); act = funcs[p](obs[p]); dt = time.monotonic()-t
                if p == seat: max_seconds = max(max_seconds,dt)
                if not isinstance(act,dict): raise TypeError('Agent action is not a dict')
                acts.append(act)
            h.update(json.dumps(acts,sort_keys=True,separators=(',',':')).encode())
            g.step(*acts); steps += 1
            if job.get('prefix') and steps == 145: break
            if steps > 720: raise RuntimeError('Episode exceeded 720 steps')
        # Kaggle's 720 states include the initial state: 719 action transitions.
        if not job.get('prefix') and steps != 719:
            raise RuntimeError(f'Unexpected episode length: {steps}')
        scores = [float(g.reward(p)) for p in (0,1)]
        out.update(status='ok', steps=steps, scores=scores, margin=scores[seat]-scores[1-seat],
            observations=seen, trace_sha256=h.hexdigest(), max_action_seconds=max_seconds,
            entry=me.__name__, telemetry=ns.get('_CODEZ_STATS', {}))
    except Exception:
        out['error'] = traceback.format_exc()
    out['elapsed_seconds'] = time.monotonic()-started
    gc.collect()
    return out

def run(manifest, workers=4):
    manifest = Path(manifest)
    spec = json.loads(manifest.read_text()); jobs = spec['jobs']
    if len({key(j) for j in jobs}) != len(jobs): raise ValueError('Duplicate jobs')
    for path, sha in spec['hashes'].items():
        if digest(ROOT/path) != sha: raise ValueError(f'Frozen hash mismatch: {path}')
    dest = manifest.with_suffix('.jsonl'); existing = {}
    if dest.exists():
        for line in dest.read_text().splitlines():
            row = json.loads(line)
            if row['key'] in existing: raise ValueError('Duplicate result')
            existing[row['key']] = row
    wanted = {key(j) for j in jobs}
    if not set(existing).issubset(wanted): raise ValueError('Unexpected result keys')
    pending = [j for j in jobs if key(j) not in existing]
    print(f'{manifest.stem}: {len(existing)}/{len(jobs)} cached; {len(pending)} pending',flush=True)
    with dest.open('a') as f, concurrent.futures.ProcessPoolExecutor(workers) as pool:
        for row in pool.map(one, pending, chunksize=1):
            f.write(json.dumps(row,sort_keys=True)+'\n');f.flush()
            existing[row['key']] = row
            n = len(existing)
            if row['status'] != 'ok': print(row['error'],flush=True)
            if n % 20 == 0 or n == len(jobs):
                print(f'{manifest.stem}: {n}/{len(jobs)} errors={sum(r["status"]!="ok" for r in existing.values())}',flush=True)
    errors = sum(r['status']!='ok' for r in existing.values())
    summary = {'complete': len(existing)==len(jobs), 'jobs':len(jobs),'errors':errors,
        'manifest_sha256':digest(manifest),'result_sha256':digest(dest)}
    manifest.with_suffix('.summary.json').write_text(json.dumps(summary,indent=2))
    if errors: raise RuntimeError(f'{errors} games failed; cannot promote')

def manifest(name, jobs, extra=None):
    paths = {j['agent'] for j in jobs}|{f'frozen/opponents/{j["opponent"]}.py' for j in jobs}
    paths |= {'research.py', 'frozen/engine/kagsim.cpython-312-darwin.so'}
    obj = {'name':name,'hashes':{p:digest(ROOT/p) for p in sorted(paths)},'jobs':jobs,**(extra or {})}
    p = ROOT/'runs'/f'{name}.json';p.parent.mkdir(exist_ok=True)
    if p.exists(): raise FileExistsError(p)
    p.write_text(json.dumps(obj,indent=2));return p

def build(version, entries):
    """Immutable sparse routing overlay; no modification to the parent source."""
    parent = ROOT/'versions/v000/main.py'
    dest = ROOT/'versions'/version; dest.mkdir(exist_ok=False)
    suffix = '''
# codez-v54: exact-key sparse table; original routing is preserved on no match.
_CODEZ_PARENT_ENTRY = [v for k,v in list(globals().items()) if callable(v) and not k.startswith('__')][-1]
_CODEZ_PARENT_ROUTER = _IMPL.chassis.router
_CODEZ_TABLE = ENTRIES
_CODEZ_STATS = {'route_changes': 0}
def _codez_router(observation, step, state):
    first = not state.get('day6')
    rid = _CODEZ_PARENT_ROUTER(observation, step, state)
    if step == 0: _CODEZ_STATS['route_changes'] = 0
    if step == 144 and first:
        shops = tuple(observation.get('town',{}).get('unlocked_shops',[])[:2])
        rkey = state.get('rkey')
        seat = int(observation['player'])
        for row in _CODEZ_TABLE:
            if rkey == tuple(row['rkey']) and shops == tuple(row['shops']) and seat in row['seats']:
                chosen = row['route']
                if chosen not in _IMPL.chassis.routes: raise ValueError('Unknown codez route')
                _CODEZ_STATS['route_changes'] += int(rid != chosen)
                state['route'] = chosen
                return chosen
    return rid
_IMPL.chassis.router = _codez_router
def codez_agent(observation, configuration=None):
    return _CODEZ_PARENT_ENTRY(observation, configuration)
'''.replace('ENTRIES',repr(entries))
    (dest/'main.py').write_text(parent.read_text()+suffix)
    (dest/'manifest.json').write_text(json.dumps({'version':version,'parent':'v000',
        'parent_sha256':digest(parent),'sha256':digest(dest/'main.py'),'entries':entries},indent=2))
    return f'versions/{version}/main.py'

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('manifest');ap.add_argument('--workers',type=int,default=4)
    a=ap.parse_args();run(a.manifest,a.workers)
