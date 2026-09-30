#!/usr/bin/env python3
"""V125 串行自然 RNG 对局；冻结代码与引擎，完整错误保留，支持官方/快引擎逐帧校验。"""
from __future__ import annotations
import argparse, contextlib, copy, fcntl, gzip, hashlib, importlib, importlib.util, inspect, io, json, math, os, random, signal, statistics, sys, time, traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
KG=ROOT/'kaggle_Kaggriculture'
CPPSIM=KG/'model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim'
PASS={'farmer':['PASS'],'hands':[],'market':[]}
FIELDS=('player','day','hour','step','farms','private','market','town')
RUNTIME_EXT={'.py','.pyi','.joblib','.npz','.npy','.pkl','.pickle','.bin','.so'}
SKIP_DIRS={'evaluation','__pycache__','.git','tests','test','runs','development','training_quick'}
SCHEMA='v125-natural-rng-match-v2'

def now():return datetime.now(timezone.utc).isoformat()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write_json(p,x):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n');os.replace(tmp,p)
def val(x):return x() if callable(x) else x

def package_info(value,extras):
    if value.upper()=='PASS':return {'entry':'PASS','files':{},'entry_sha256':digest(PASS),'composite_sha256':digest({'builtin':'PASS','action':PASS})}
    entry=Path(value).expanduser().resolve()
    if not entry.is_file():raise FileNotFoundError(entry)
    files={entry}
    for p in entry.parent.rglob('*'):
        rel=p.relative_to(entry.parent)
        if p.is_file() and p.suffix in RUNTIME_EXT and not any(z in SKIP_DIRS for z in rel.parts[:-1]):files.add(p.resolve())
    for extra in extras:
        p=Path(extra).expanduser().resolve()
        if not p.is_file():raise FileNotFoundError(p)
        files.add(p)
    records={str(p):sha(p) for p in sorted(files)}
    return {'entry':str(entry),'files':records,'entry_sha256':records[str(entry)],'composite_sha256':digest(records),'closure_policy':'entry plus package Python/binary/weight files; dynamic external dependencies must use --candidate-file/--opponent-file'}

def check_files(info):
    for p,h in info.get('files',{}).items():
        if not Path(p).is_file() or sha(p)!=h:raise RuntimeError('SHA_DRIFT: '+p)

def import_engines():
    captured=io.StringIO()
    with contextlib.redirect_stdout(captured),contextlib.redirect_stderr(captured):
        import kaggle_environments
        from kaggle_environments import make
        rules=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
        sys.path.insert(0,str(CPPSIM))
        try:import kagsim
        finally:sys.path.remove(str(CPPSIM))
    pkg=Path(kaggle_environments.__file__).parent
    files=[Path(rules.__file__),Path(rules.__file__).with_suffix('.json'),pkg/'core.py',pkg/'utils.py',Path(kagsim.__file__),CPPSIM/'sim/sim.hpp',CPPSIM/'sim/pyrandom.hpp',CPPSIM/'python/kagsim.cpp']
    fp={str(p.resolve()):sha(p) for p in files if p.is_file()}
    evidence={'framework_version':kaggle_environments.__version__,'fast_engine_version':str(kagsim.ENGINE_VERSION),'python':sys.version,'python_executable':sys.executable,'files':fp,'composite_sha256':digest(fp),'natural_rng':True,'forced_shops':False,'source_replay_read':False,'current_online_parity':'NOT_INDEPENDENTLY_VERIFIED','import_messages':captured.getvalue()[-3000:]}
    if str(kagsim.ENGINE_VERSION)!='1.32.7':raise RuntimeError('未知快引擎版本，拒绝默认使用')
    return make,rules,kagsim,evidence

class Agent:
    """每席、每局独立模块、局部导入与随机状态；错误直接上抛，不以 PASS 掩盖。"""
    def __init__(self,info,seed,role):
        self.info=info;self.path=None if info['entry']=='PASS' else Path(info['entry']);self.modules={};self.module=None;self.latencies=[];self.wrapper_latencies=[];self.stdout_bytes=0;self.output_samples=[]
        self.python_rng=random.Random((seed*1000003+role*97409)&((1<<63)-1)).getstate()
        self.numpy=None;self.numpy_rng=None
        try:
            import numpy as np
            self.numpy=np;self.numpy_rng=np.random.RandomState((seed+role*65537)%(2**32-1)).get_state()
        except ImportError:pass
        if self.path is None:self.fn=lambda obs,configuration:copy.deepcopy(PASS);self.two_args=True;return
        self.names={p.stem for p in self.path.parent.glob('*.py')}|{p.name for p in self.path.parent.iterdir() if p.is_dir() and (p/'__init__.py').exists()}
        self.unique=f'v125_agent_{role}_{time.time_ns()}'
        with self.scope():
            spec=importlib.util.spec_from_file_location(self.unique,self.path);self.module=importlib.util.module_from_spec(spec);sys.modules[self.unique]=self.module
            capture=io.StringIO()
            with contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):spec.loader.exec_module(self.module)
            self.record_output(capture.getvalue(),'import')
            self.fn=self.module.create_agent() if callable(getattr(self.module,'create_agent',None)) else self.module.agent
            sig=inspect.signature(self.fn)
            try:sig.bind(None,None);self.two_args=True
            except TypeError:sig.bind(None);self.two_args=False
    def local(self,name,module):
        if name==getattr(self,'unique',None) or name.split('.')[0] in getattr(self,'names',set()):return True
        p=getattr(module,'__file__',None)
        return bool(p and self.path and str(p).startswith(str(self.path.parent)+os.sep))
    @contextlib.contextmanager
    def scope(self):
        if self.path is None:yield;return
        old_path=list(sys.path);saved={n:m for n,m in list(sys.modules.items()) if self.local(n,m)}
        for n in saved:sys.modules.pop(n,None)
        sys.modules.update(self.modules);sys.path.insert(0,str(self.path.parent));old_rng=random.getstate();random.setstate(self.python_rng)
        old_np=self.numpy.random.get_state() if self.numpy is not None else None
        if self.numpy is not None:self.numpy.random.set_state(self.numpy_rng)
        try:yield
        finally:
            self.python_rng=random.getstate();random.setstate(old_rng)
            if self.numpy is not None:self.numpy_rng=self.numpy.random.get_state();self.numpy.random.set_state(old_np)
            self.modules={n:m for n,m in list(sys.modules.items()) if self.local(n,m)}
            for n in self.modules:sys.modules.pop(n,None)
            sys.modules.update(saved);sys.path[:]=old_path
    def record_output(self,text,step):
        self.stdout_bytes+=len(text.encode())
        if text and len(self.output_samples)<5:self.output_samples.append({'step':step,'text':text[:1200]})
    def call(self,obs,cfg,hard_timeout):
        capture=io.StringIO();t=time.perf_counter();raw_started=None;raw_elapsed=None;old_handler=None
        def alarm(*_):raise TimeoutError('agent hard call timeout')
        try:
            if hard_timeout>0:
                old_handler=signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,hard_timeout)
            with self.scope(),contextlib.redirect_stdout(capture),contextlib.redirect_stderr(capture):
                raw_started=time.perf_counter()
                try:out=self.fn(obs,cfg) if self.two_args else self.fn(obs)
                finally:raw_elapsed=(time.perf_counter()-raw_started)*1000
            return out
        finally:
            if hard_timeout>0:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
            self.wrapper_latencies.append((time.perf_counter()-t)*1000);self.latencies.append(raw_elapsed if raw_elapsed is not None else (time.perf_counter()-t)*1000);self.record_output(capture.getvalue(),obs.get('step'))
    def diagnostics(self):
        method=getattr(self.module,'diagnostics',None) if self.module else None
        if not callable(method):method=getattr(self.fn,'diagnostics',None)
        if not callable(method):return None
        try:
            with self.scope():return method()
        except Exception as exc:return {'diagnostics_error':f'{type(exc).__name__}: {exc}'}
    def report(self):
        v=sorted(self.latencies)
        def quant(q):return v[min(len(v)-1,math.ceil(q*len(v))-1)] if v else None
        return {'calls':len(v),'latency_ms':{'mean':statistics.mean(v) if v else None,'p50':quant(.5),'p95':quant(.95),'p99':quant(.99),'max':max(v) if v else None,'total':sum(v)},'latency_definition':'agent callable only; isolation/capture wrapper excluded','wrapper_inclusive_ms_total':sum(self.wrapper_latencies),'calls_over_1s':sum(x>1000 for x in v),'captured_output_bytes':self.stdout_bytes,'output_samples':self.output_samples}

class Engine:
    def __init__(self,backend,seed,make,fast):
        self.backend=backend
        if backend=='official':self.g=make('kaggriculture',configuration={'seed':seed,'episodeSteps':720},debug=False);self.g.reset(2)
        else:self.g=fast.Game(seed)
    def observe(self,s):return copy.deepcopy(dict(self.g._Environment__get_shared_state(s).observation)) if self.backend=='official' else self.g.observe(s)
    def step(self,a):return self.g.step(a) if self.backend=='official' else self.g.step(a[0],a[1])
    def done(self):return bool(val(self.g.done))
    def rewards(self):return [float(s.reward or 0) for s in self.g.state] if self.backend=='official' else [float(self.g.reward(s)) for s in (0,1)]
    def statuses(self):return [str(s.status) for s in self.g.state] if self.backend=='official' else ['DONE' if self.done() else 'ACTIVE']*2

def first_difference(a,b,p=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):
            if k not in a or k not in b:return p+'.'+k+' missing'
            d=first_difference(a[k],b[k],p+'.'+k)
            if d:return d
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b):return p+' length'
        for i,(x,y) in enumerate(zip(a,b)):
            d=first_difference(x,y,f'{p}[{i}]')
            if d:return d
    elif a!=b:return f'{p}: {a!r} != {b!r}'
    return None

def snapshot(obs):
    rows=[]
    for s,o in enumerate(obs):
        f=o['farms'][s];p=o['private'];board=Counter();coords=[]
        for y,line in enumerate(f['tiles']):
            for x,tile in enumerate(line):
                if isinstance(tile,dict):
                    label=tile.get('animal') or tile.get('crop') or tile.get('kind');board[label]+=1
                    if tile.get('animal'):board['animals']+=1
                    if tile.get('crop'):board['crops']+=1
                    coords.append([x,y,label,tile.get('yield_units',0)])
        rows.append({'seat':s,'step':o['step'],'day':o['day'],'hour':o['hour'],'money':f['money'],'hands':len(f['hands']),'quadrants':f['unlocked_quadrants'],'board':dict(board),'tiles':coords,'shed':p['shed'],'seeds':p['seeds'],'carried':dict(sum((Counter(i) for i in p['inventories']),Counter())),'shops':o['town']['unlocked_shops'],'prices':o['market']['prices']})
    return rows

def basic_action_check(action):
    if not isinstance(action,dict):raise ValueError('action must be dict')
    canonical(action)
    if not isinstance(action.get('farmer',['PASS']),list):raise ValueError('farmer must be list')
    if not isinstance(action.get('hands',[]),list) or not all(isinstance(a,list) for a in action.get('hands',[])):raise ValueError('hands must be list[list]')
    if not isinstance(action.get('market',[]),list) or not all(isinstance(a,list) for a in action.get('market',[])):raise ValueError('market must be list[list]')

class Instrument:
    def __init__(self,rules):
        self.r=rules;self.orig={};self.farms={};self.step=0;self.counts=[Counter(),Counter()];self.failed=[];self.ledger=[defaultdict(Counter),defaultdict(Counter)];self.harvest=[Counter(),Counter()];self.bound_engines={}
    def __enter__(self):
        orig=self.r._apply_unit_action;self.orig['_apply_unit_action']=orig
        def wrapped(farm,private,idx,action,*args,**kw):
            seat=self.farms.get(id(farm));pos=self.r._farmer_position(farm,idx);op=action[0] if isinstance(action,list) and action else 'MALFORMED'
            def local():
                pp=self.r._farmer_position(farm,idx)
                return canonical([pp,farm['tiles'][pos[1]][pos[0]] if pos else None,private['inventories'][idx] if idx<len(private['inventories']) else None,private['seeds'],private['shed']])
            before=local();inv=Counter(private['inventories'][idx]) if idx<len(private['inventories']) else Counter()
            ret=orig(farm,private,idx,action,*args,**kw)
            if seat is not None:
                self.counts[seat]['submitted_'+op]+=1
                changed=before!=local()
                if changed:self.counts[seat]['changed_'+op]+=1
                elif op!='PASS':
                    self.counts[seat]['unchanged_nonpass']+=1
                    if len(self.failed)<100:self.failed.append({'decision_step':self.step,'seat':seat,'unit':idx,'action':action,'position':pos})
                if op in ('HARVEST','COLLECT_FERTILIZER') and idx<len(private['inventories']):self.harvest[seat].update(Counter(private['inventories'][idx])-inv)
            return ret
        self.r._apply_unit_action=wrapped
        commit=self.r._commit_unit;self.orig['_commit_unit']=commit
        def wc(op,item,price,farm,private,market,*args,**kw):
            ok=commit(op,item,price,farm,private,market,*args,**kw);seat=self.farms.get(id(farm))
            if ok and seat is not None:self.ledger[seat][op+'_qty'][item]+=1;self.ledger[seat][op+'_cash'][item]+=price
            return ok
        self.r._commit_unit=wc
        for name,label,field in [('_do_hire','HIRE','hands'),('_do_buy_land','BUY_LAND','unlocked_quadrants')]:
            fn=getattr(self.r,name);self.orig[name]=fn
            def wrap(farm,*args,_fn=fn,_label=label,_field=field,**kw):
                money=farm['money'];count=len(farm[_field]);result=_fn(farm,*args,**kw);seat=self.farms.get(id(farm))
                if seat is not None:self.ledger[seat][_label+'_qty'][_field]+=len(farm[_field])-count;self.ledger[seat][_label+'_cash'][_field]+=money-farm['money']
                return result
            setattr(self.r,name,wrap)
        return self
    def __exit__(self,*_):
        for engine,original in self.bound_engines.values():engine.g.interpreter=original
        for k,v in self.orig.items():setattr(self.r,k,v)
    def before(self,official,actions,step):
        self.step=step
        if id(official) not in self.bound_engines:
            original=official.g.interpreter;self.bound_engines[id(official)]=(official,original)
            def bound(state,env,logs=None):
                self.farms={id(f):i for i,f in enumerate(state[0].observation.farms)}
                return original(state,env)
            official.g.interpreter=bound
        for s,a in enumerate(actions):
            for order in a.get('market',[]):
                if isinstance(order,list) and order:
                    self.counts[s]['requested_market_order_'+str(order[0])]+=1
                    if len(order)>2:
                        try:self.counts[s]['requested_market_qty_'+str(order[0])+'_'+str(order[1])]+=max(0,int(order[2]))
                        except (TypeError,ValueError):self.counts[s]['malformed_market_quantity']+=1
            plants=Counter(z[1] for z in [a.get('farmer',[])]+a.get('hands',[]) if isinstance(z,list) and len(z)>1 and z[0]=='PLANT')
            seeds=official.g.state[s].observation.private['seeds'];self.counts[s]['atomic_plant_blocked_requests']+=sum(n for c,n in plants.items() if n>seeds.get(c,0))
    def report(self):return {'unit_counts':[dict(c) for c in self.counts],'unchanged_nonpass_examples':self.failed,'actual_market_ledger':[dict(c) for c in self.ledger],'harvest_qty':[dict(c) for c in self.harvest],'interpretation':'unchanged excludes deliberate PASS; state-changing actions are not necessarily economically useful; atomic PLANT blocking counted separately'}

def agent_configuration(manifest,official):
    """完整官方解释器初始化后会清空seed；快路径沿用同一代理可见配置。"""
    cfg=copy.deepcopy(dict(official.g.configuration) if official else manifest['configuration'])
    cfg['seed']=None
    return cfg

def play(manifest,seed,seat,args,make,rules,fast):
    started=time.perf_counter();candidate=manifest['candidate'];opponent=manifest['opponent'];key=f'{candidate["composite_sha256"]}:{opponent["composite_sha256"]}:{seed}:{seat}:{manifest["engine"]["composite_sha256"]}'
    result={'schema':SCHEMA,'key':key,'seed':seed,'candidate_seat':seat,'candidate_composite_sha256':candidate['composite_sha256'],'opponent_composite_sha256':opponent['composite_sha256'],'engine_composite_sha256':manifest['engine']['composite_sha256'],'manifest_sha256':digest(manifest),'backend':args.backend,'rng_policy':'natural engine seed; no forced shops/replay injections','evidence_role':'LOCAL_SIMULATION_NOT_ONLINE_GOLD','status':'ERROR','started_at':now(),'errors':[],'calls':0,'parity_state_checks':0,'daily':[]}
    agents=[];trace=[];instruments=None;primary=None
    try:
        check_files(candidate);check_files(opponent);check_files(manifest['engine'])
        specs=[candidate,opponent] if seat==0 else [opponent,candidate]
        agents=[Agent(info,seed,s) for s,info in enumerate(specs)]
        primary=Engine(args.backend,seed,make,fast);shadow=Engine('fast' if args.backend=='official' else 'official',seed,make,fast) if args.parity else None
        official=primary if args.backend=='official' else shadow
        cfg=agent_configuration(manifest,official)
        instruments=Instrument(rules) if args.audit_actions else None
        cm=instruments if instruments else contextlib.nullcontext()
        with cm:
            while True:
                observations=[primary.observe(s) for s in (0,1)]
                if shadow:
                    other=[shadow.observe(s) for s in (0,1)]
                    for s in (0,1):
                        for field in FIELDS:
                            difference=first_difference(observations[s].get(field),other[s].get(field),field)
                            if difference:raise RuntimeError(f'ENGINE_PARITY step={result["calls"]} seat={s}: {difference}')
                        result['parity_state_checks']+=1
                if args.daily and (result['calls']%24==23 or result['calls'] in (0,719)):
                    daily=snapshot(observations)
                    if instruments:
                        for s,row in enumerate(daily):row['audit_cumulative']={'unit_counts':dict(instruments.counts[s]),'market':copy.deepcopy(dict(instruments.ledger[s])),'harvest':dict(instruments.harvest[s])}
                    result['daily'].append(daily)
                if primary.done():break
                if result['calls']>=719:raise RuntimeError('engine exceeded 719 decisions')
                actions=[]
                for s,agent in enumerate(agents):
                    a=agent.call(observations[s],cfg,args.hard_call_timeout);basic_action_check(a);actions.append(a)
                if instruments:instruments.before(official,actions,result['calls'])
                if args.trace:trace.append(copy.deepcopy(actions))
                primary.step(actions)
                if shadow:shadow.step(actions)
                result['calls']+=1
        check_files(candidate);check_files(opponent);check_files(manifest['engine'])
        rewards=primary.rewards();statuses=primary.statuses();own=rewards[seat];rival=rewards[1-seat]
        if result['calls']!=719 or statuses!=['DONE','DONE']:raise RuntimeError(f'incomplete game: {result["calls"]} calls, {statuses}')
        result.update({'status':'DONE','statuses':statuses,'rewards':rewards,'candidate_reward':own,'opponent_reward':rival,'margin':own-rival,'outcome':'win' if own>rival else 'tie' if own==rival else 'loss','terminal':snapshot([primary.observe(s) for s in (0,1)]),'parity_pass':True if shadow else None})
    except Exception as exc:
        result['errors'].append({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc(limit=8)})
        if primary:
            result['statuses']=primary.statuses();result['observed_rewards_on_failure']=primary.rewards()
        result['outcome']='error'
    result['agents']=[a.report() for a in agents]
    if args.diagnostics:result['strategy_diagnostics']=[a.diagnostics() for a in agents]
    if instruments:result['action_audit']=instruments.report()
    result['elapsed_seconds']=time.perf_counter()-started;result['completed_at']=now()
    if args.trace:
        tracepath=args.output/f'trace_{seed}_seat{seat}.json.gz'
        with gzip.open(tracepath,'wt',encoding='utf-8') as f:json.dump({'seed':seed,'candidate_seat':seat,'actions':trace},f,separators=(',',':'))
        result['trace']={'path':str(tracepath),'sha256':sha(tracepath)}
    return result

def summary(rows,manifest):
    expected=len(manifest['seeds'])*len(manifest['seats']);done=[r for r in rows if r['status']=='DONE'];w=sum(r['outcome']=='win' for r in done);ties=sum(r['outcome']=='tie' for r in done);loss=sum(r['outcome']=='loss' for r in done)
    return {'schema':SCHEMA,'generated_at':now(),'evidence_role':'LOCAL_SIMULATION_NOT_ONLINE_GOLD','expected_games':expected,'recorded_games':len(rows),'done_games':len(done),'wins_ties_losses_errors':[w,ties,loss,len(rows)-len(done)],'pure_win_rate_expected_denominator':w/expected,'mean_margin_completed_only':statistics.mean(r['margin'] for r in done) if done else None,'all_719_calls':len(done)==expected and all(r['calls']==719 for r in done),'all_call_counts_719_per_seat':len(done)==expected and all(len(r['agents'])==2 and all(a['calls']==719 for a in r['agents']) for r in done),'all_parity_pass':all(r.get('parity_pass') is True for r in done) if manifest['options']['parity'] and len(done)==expected else None,'status':'COMPLETE' if len(done)==expected else 'INCOMPLETE_OR_ERROR','manifest_sha256':digest(manifest)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--candidate',required=True);p.add_argument('--opponent',default='PASS');p.add_argument('--candidate-file',action='append',default=[]);p.add_argument('--opponent-file',action='append',default=[])
    p.add_argument('--seed',type=int);p.add_argument('--seeds');p.add_argument('--seat',type=int,choices=[0,1]);p.add_argument('--seats',choices=['both','0','1']);p.add_argument('--backend',choices=['official','fast'],default='official');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--daily',action='store_true');p.add_argument('--audit-actions',action='store_true');p.add_argument('--parity',action='store_true');p.add_argument('--trace',action='store_true');p.add_argument('--diagnostics',action='store_true');p.add_argument('--protocol',type=Path);p.add_argument('--hard-call-timeout',type=float,default=10.0);args=p.parse_args()
    sys.dont_write_bytecode=True
    if args.seed is not None and args.seeds:p.error('--seed和--seeds互斥')
    if args.seat is not None and args.seats:p.error('--seat和--seats互斥')
    seeds=[args.seed] if args.seed is not None else [int(x) for x in (args.seeds or '').split(',') if x.strip()]
    seats=[args.seat] if args.seat is not None else [0,1] if args.seats=='both' else [int(args.seats)] if args.seats else []
    if not seeds or not seats:p.error('必须指定 seed(s) 与 seat(s)')
    if len(set(seeds))!=len(seeds):p.error('seed列表重复')
    if any(s<0 or s>2**31-1 for s in seeds):p.error('seed必须是非负31位整数')
    if args.audit_actions and args.backend=='fast' and not args.parity:p.error('快引擎动作审计需要--parity以完整官方解释器观测真实操作')
    args.output=args.output.expanduser().resolve()
    if not args.output.is_relative_to(HERE):p.error('输出必须位于V125 evaluation目录下')
    args.output.mkdir(parents=True,exist_ok=True)
    with (args.output/'.run.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:p.error('同一目录已有运行实例，拒绝重复启动')
        make,rules,fast,engine=import_engines()
        # 探查配置只reset，不执行任何对局决策。
        probe=make('kaggriculture',configuration={'seed':0,'episodeSteps':720},debug=False);cfg=dict(probe.configuration);cfg['seed']=None
        param_env={k:hashlib.sha256(v.encode()).hexdigest() for k,v in os.environ.items() if k in {'V15_PARAMS','V125_PARAMS'}}
        manifest={'schema':SCHEMA,'candidate':package_info(args.candidate,args.candidate_file),'opponent':package_info(args.opponent,args.opponent_file),'engine':engine,'harness':{'path':str(Path(__file__).resolve()),'sha256':sha(__file__)},'seeds':seeds,'seats':seats,'configuration':cfg,'options':{'backend':args.backend,'daily':args.daily,'audit_actions':args.audit_actions,'parity':args.parity,'trace':args.trace,'diagnostics':args.diagnostics,'hard_call_timeout_seconds':args.hard_call_timeout},'agent_parameter_environment_sha256':param_env,'protocol':{'path':str(args.protocol.resolve()),'sha256':sha(args.protocol)} if args.protocol else None,'workers':1,'statistical_unit':'seed with seat pairing; games are not claimed IID','promotion_status':'NOT_ONLINE_PROMOTION_EVIDENCE','platform_execution_fidelity':{'agent_configuration_seed':'always null; real seed is engine-only metadata','configuration_scope':'official callable-agent configuration; raw-file adapter __raw_path__ is not emulated','natural_rng_rules':True,'kaggle_sandbox_process_emulated':False,'remaining_overage_time_budget_emulated':False,'latency':'agent callable measured separately; hard wallclock watchdog only'}}
        mpath=args.output/'run_manifest.json'
        if mpath.exists():
            if json.loads(mpath.read_text())!=manifest:raise RuntimeError('MANIFEST_DRIFT：候选/引擎/参数/seed发生变化；使用新实验目录')
        else:write_json(mpath,manifest)
        out=args.output/'games.jsonl';rows=[];seen=set()
        allowed={f'{manifest["candidate"]["composite_sha256"]}:{manifest["opponent"]["composite_sha256"]}:{seed}:{seat}:{engine["composite_sha256"]}' for seed in seeds for seat in seats}
        if out.exists():
            for line in out.read_text().splitlines():
                if not line.strip():continue
                row=json.loads(line)
                if row['key'] in seen or row['key'] not in allowed:raise RuntimeError('DUPLICATE_OR_UNREGISTERED_KEY')
                if row['manifest_sha256']!=digest(manifest):raise RuntimeError('RESULT_MANIFEST_DRIFT')
                rows.append(row);seen.add(row['key'])
        print(json.dumps({'status':'READY','expected_games':len(allowed),'already_recorded':len(seen),'output':str(args.output),'candidate_sha256':manifest['candidate']['composite_sha256'],'engine_sha256':engine['composite_sha256']},ensure_ascii=False),flush=True)
        for seed in seeds:
            for seat in seats:
                key=f'{manifest["candidate"]["composite_sha256"]}:{manifest["opponent"]["composite_sha256"]}:{seed}:{seat}:{engine["composite_sha256"]}'
                if key in seen:continue
                if sha(__file__)!=manifest['harness']['sha256']:raise RuntimeError('HARNESS_SHA_DRIFT')
                if manifest['protocol'] and sha(manifest['protocol']['path'])!=manifest['protocol']['sha256']:raise RuntimeError('PROTOCOL_SHA_DRIFT')
                row=play(manifest,seed,seat,args,make,rules,fast)
                with out.open('a') as f:f.write(canonical(row)+'\n');f.flush();os.fsync(f.fileno())
                rows.append(row);seen.add(key);write_json(args.output/'summary.json',summary(rows,manifest))
                print(json.dumps({k:row.get(k) for k in ['status','seed','candidate_seat','calls','candidate_reward','opponent_reward','margin','outcome','elapsed_seconds','errors']},ensure_ascii=False),flush=True)
                if row['status']!='DONE':return 2
        report=summary(rows,manifest);write_json(args.output/'summary.json',report);print(json.dumps(report,ensure_ascii=False),flush=True);return 0 if report['status']=='COMPLETE' else 2
if __name__=='__main__':raise SystemExit(main())
