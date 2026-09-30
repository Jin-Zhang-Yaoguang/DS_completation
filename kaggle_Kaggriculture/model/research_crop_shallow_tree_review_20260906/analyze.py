import ast,base64,collections,datetime,hashlib,json,statistics,zlib
from pathlib import Path
B=Path(__file__).resolve().parent
H=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def embedded(path,name):
 tree=ast.parse(path.read_text())
 node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
 vals=[n.value for n in ast.walk(node.value) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
 return json.loads(zlib.decompress(base64.b85decode(max(vals,key=len))).decode())
def norm(a):
 a=a or {};return {'farmer':a.get('farmer') or ['PASS'],'hands':a.get('hands') or [],'market':a.get('market') or []}
def counts(rows):
 return {'n':len(rows),'W':sum(r['outcome']=='W' for r in rows),'L':sum(r['outcome']=='L' for r in rows),'T':sum(r['outcome']=='T' for r in rows),'errors':sum(r['outcome']=='ERROR' for r in rows),'pure_win_rate':sum(r['outcome']=='W' for r in rows)/len(rows) if rows else None}
inv=json.loads((B/'replay_inventory.json').read_text());allrows=[];summaries=[];issues=[];schema_examples=[]
cached={}
if (B/'online_rows.json').exists():
 cached={(r['submission_id'],r['episode_id']):r for r in json.loads((B/'online_rows.json').read_text())}
 schema_examples=json.loads((B/'online_summary.json').read_text()).get('schema_examples',[])
for sub in json.loads((B/'submissions.json').read_text())[:4]:
 sid=sub['ref'];p=B/'snapshots'/str(sid)/'main.py';source=p.read_text();tape=embedded(p,'_ACTIONS' if sid in [56044730,56044732] else '_V120_DISTILLED_ROUTE')
 helper=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_v17_count_animals');ns={};exec(compile(ast.Module(body=[helper],type_ignores=[]),str(p),'exec'),ns)
 es=json.loads((B/f'episodes_{sid}.parsed.json').read_text())[0];es=sorted([e for e in es if 'PUBLIC' in e['type'] and 'COMPLETED' in e['state']],key=lambda e:(e['endTime'],e['id']));rows=[]
 for seq,e in enumerate(es,1):
  if (sid,e['id']) in cached:
   row=cached[(sid,e['id'])];rows.append(row);allrows.append(row);continue
  eid=e['id'];rp=B/'replays'/f'episode-{eid}-replay.json'
  if not rp.exists():rp=Path(inv['found'].get(str(eid),'/missing'))
  if not rp.exists():issues.append({'sid':sid,'episode':eid,'error':'missing'});continue
  try:d=json.loads(rp.read_text());names=[str(x).strip() for x in d['info']['TeamNames']];assert names.count('datatuu')==1;me=names.index('datatuu');opp=1-me;assert d['info']['EpisodeId']==eid;st=d['steps'];assert len(st)==720
  except Exception as ex:issues.append({'sid':sid,'episode':eid,'error':type(ex).__name__});continue
  states=[x[me].get('status') for x in st];mine=st[-1][me].get('reward');theirs=st[-1][opp].get('reward');bad=st[-1][me].get('status')!='DONE' or mine is None or theirs is None
  outcome='ERROR' if bad else 'W' if mine>theirs else 'L' if mine<theirs else 'T'
  actions=[norm(x[me].get('action')) for x in st[1:]];opactions=[norm(x[opp].get('action')) for x in st[1:]]
  procurement=collections.Counter();exact=0;matches=slots=0;opcount=collections.Counter();forbidden=0
  for t,a in enumerate(actions):
   orig=norm(tape[t]);aa=[a['farmer']]+a['hands'];bb=[orig['farmer']]+orig['hands'];exact+=aa==bb
   for k in range(max(len(aa),len(bb))):
    matches+=k<len(aa) and k<len(bb) and aa[k]==bb[k];slots+=1
   for z in aa:
    if z:opcount[z[0]]+=1
   for o in a['market']:
    if o and o[0] in ['BUY_ANIMAL','BUY_SEED'] and len(o)>=3:procurement[o[0]+':'+str(o[1])]+=o[2]
    if o and o[0]=='BUY_PRODUCT' and len(o)>1 and o[1] not in ['WHEAT','FERTILIZER']:forbidden+=1
  pert=any(o and o[0]=='BUY_PRODUCT' and len(o)>2 and o[1]=='WHEAT' and isinstance(o[2],(int,float)) and o[2]>=20 for o in opactions[0]['market'])
  row={'submission_id':sid,'episode_id':eid,'sequence':seq,'endTime':e['endTime'],'seat':me,'opponent':names[opp],'outcome':outcome,'cash':mine,'opponent_cash':theirs,'margin':None if bad else mine-theirs,'full_action_sha':H(actions),'units_sha':H([{k:a[k] for k in ['farmer','hands']} for a in actions]),'procurement_requests':dict(procurement),'procurement_hash':H(procurement),'template_exact_unit_frames':exact,'template_unit_frames':719,'template_unit_slots_match':matches,'template_unit_slots_total':slots,'opponent_opening_wheat_ge20':pert,'forbidden_buy_requests':forbidden,'request_op_counts':dict(opcount),'replay_path':str(rp),'replay_sha256':hashlib.sha256(rp.read_bytes()).hexdigest(),'configuration_sha256':H(d['configuration']),'module_version':d.get('module_version')}
  rows.append(row);allrows.append(row)
  # 在真实保存观测上，只调用已逐行检查的纯计数辅助函数，不运行候选 agent 或引擎。
  if len([x for x in schema_examples if x['submission_id']==sid])<2:
   for t in range(24,72):
    obs=dict(st[t][me].get('observation') or {});public=st[t][0].get('observation') or {};obs={**public,**obs}
    if 'farms' not in obs:continue
    actual=collections.Counter(z.get('animal') for rr in obs['farms'][me]['tiles'] for z in rr if isinstance(z,dict) and isinstance(z.get('animal'),str))
    if actual['COW']+actual['SHEEP']:
     got=ns['_v17_count_animals'](obs,me);priv=obs.get('private') or {};stored=priv.get('shed') or {};carried=priv.get('inventories') or []
     expect=[actual[a]+int(stored.get(a,0))+sum(int(x.get(a,0)) for x in carried) for a in ['COW','SHEEP']]
     if list(got)!=expect:schema_examples.append({'submission_id':sid,'episode_id':eid,'state_index':t,'observed_farm_animals':dict(actual),'helper_result':got,'expected_total':expect});break
 summary={'submission_id':sid,'score':sub['publicScore'],'submitted_utc':sub['date'],'public_list_n':len(es),'verified':counts(rows),'by_seat':{str(i):counts([r for r in rows if r['seat']==i]) for i in [0,1]},'first40':counts([r for r in rows if r['sequence']<=40]),'games41to80':counts([r for r in rows if 41<=r['sequence']<=80]),'latest40':counts(rows[-40:]),'by_opponent_opening_wheat_ge20':{str(v):counts([r for r in rows if r['opponent_opening_wheat_ge20']==v]) for v in [False,True]},'unique_full_actions':len(set(r['full_action_sha'] for r in rows)),'unique_unit_sequences':len(set(r['units_sha'] for r in rows)),'unique_procurement_requests':len(set(r['procurement_hash'] for r in rows)),'template_unit_match_fraction':sum(r['template_unit_slots_match'] for r in rows)/max(1,sum(r['template_unit_slots_total'] for r in rows)),'template_exact_frame_fraction':sum(r['template_exact_unit_frames'] for r in rows)/max(1,719*len(rows)),'forbidden_buy_requests':sum(r['forbidden_buy_requests'] for r in rows),'opponent_teams':len(set(r['opponent'] for r in rows)),'days':sorted(set(r['endTime'][:10] for r in rows))}
 summaries.append(summary)
(B/'online_rows.json').write_text(json.dumps(allrows,ensure_ascii=False,indent=2));(B/'online_summary.json').write_text(json.dumps({'analyzed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'summaries':summaries,'issues':issues,'schema_examples':schema_examples,'boundary':'Observation and action requests only. No counterfactual games, no confirmed trade attribution, no online package byte attestation.'},ensure_ascii=False,indent=2))
print(json.dumps({'summaries':summaries,'issues_n':len(issues),'schema_examples':schema_examples},ensure_ascii=False,indent=2))
