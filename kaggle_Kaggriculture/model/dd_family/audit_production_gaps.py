"""Attribute live production shortfalls without altering baseline decisions."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,hashlib,io,json,sys
B=Path(__file__).resolve().parent

def run(seed):
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(B/'ddam'));import main,rules,action_space as a
    policy=main.Agent();row=json.loads((B/'ddm/training_manifest.json').read_text())['episodes'][35];raw=json.loads(Path(row['path']).read_text());teacher=row['seat']
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');p=B/op['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==op['sha256'];other=get_last_callable(p.read_text(),path=str(p))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);counts=collections.Counter();missed=[];escape=[];wither=[];daily=[];route_first=None
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        ref=raw['steps'][t][0]['observation']['farms'][teacher];farm=obs[0]['farms'][0];expected_positions=[ref['farmer'],*ref['hands']];positions=[farm['farmer'],*farm['hands']]
        if len(positions)<len(expected_positions):counts['missing_worker_turns']+=len(expected_positions)-len(positions)
        for i,(actual,wanted) in enumerate(zip(positions,expected_positions)):
            if actual!=wanted:
                counts['route_mismatch_unit_turns']+=1
                if route_first is None:route_first={'step':t,'unit':i,'actual':actual,'expected':wanted}
        action=policy.act(obs[0]);shadow=copy.deepcopy(obs[0]);units=[action['farmer'],*action['hands']]
        for i,order in enumerate(units):rules._apply_unit_action(shadow['farms'][0],shadow['private'],i,order,10,t//24,24,100)
        if t%24==23:
            for y,line in enumerate(shadow['farms'][0]['tiles']):
                for x,tile in enumerate(line):
                    if not isinstance(tile,dict):continue
                    detail={'step':t,'xy':[x,y],'tile':copy.deepcopy(tile),'cash':farm['money'],'shed_wheat':shadow['private']['shed'].get('WHEAT',0),'bag_wheat':[inv.get('WHEAT',0) for inv in shadow['private']['inventories']]}
                    if tile.get('animal') and not tile.get('fed_today'):
                        counts['unfed_animal_days']+=1
                        if tile.get('consecutive_unfed',0)>=1:escape.append(detail)
                    if tile.get('crop') and not tile.get('watered_today'):
                        counts['unwatered_crop_days']+=1
                        if tile.get('consecutive_unwatered',0)>=1:wither.append(detail)
        env.step([action,other(obs[1])])
        expected_after=raw['steps'][t+1][0]['observation']['farms'][teacher]
        source_actions=raw['steps'][t+1][teacher]['action'];source_units=[source_actions['farmer'],*source_actions.get('hands',[])]
        actual_after=env.state[0].observation.farms[0]
        for i,order in enumerate(source_units):
            if order[0] not in ['PLANT','PLACE'] or i>=len(expected_positions):continue
            x,y=expected_positions[i];tile=expected_after['tiles'][y][x]
            if not isinstance(tile,dict):continue
            field='crop' if order[0]=='PLANT' else 'animal'
            if tile.get(field)!=order[1]:continue
            actual=actual_after['tiles'][y][x];group=policy.animal_program['events']['unit'].get(f'{t}:{i}');wanted=policy.choices[group] if field=='animal' and group is not None else order[1]
            counts['planned_'+field+'_investments']+=1
            if not isinstance(actual,dict) or actual.get(field)!=wanted:
                counts['missed_'+field+'_investments']+=1;missed.append({'step':t,'unit':i,'xy':[x,y],'field':field,'expected':wanted,'actual':actual,'requested_action':units[i] if i<len(units) else None,'cash':farm['money'],'seeds':obs[0]['private']['seeds'],'shed':obs[0]['private']['shed']})
        if t%24==22:
            tiles=[z for line in actual_after['tiles'] for z in line if isinstance(z,dict)];ref_tiles=[z for line in expected_after['tiles'] for z in line if isinstance(z,dict)]
            daily.append({'day':t//24,'actual_animals':sum(bool(z.get('animal')) for z in tiles),'teacher_animals':sum(bool(z.get('animal')) for z in ref_tiles),'actual_crops':sum(bool(z.get('crop')) for z in tiles),'teacher_crops':sum(bool(z.get('crop')) for z in ref_tiles)})
    own,opp=[float(s.reward) for s in env.state]
    baseline=next(r for r in [json.loads(l) for l in (B/'joint_production_ddaw/games.jsonl').read_text().splitlines()] if r['id']=='baseline' and r['seed']==seed);assert (own,opp)==(baseline['own_cash'],baseline['opponent_cash'])
    return {'seed':seed,'margin':own-opp,'counts':dict(counts),'first_route_mismatch':route_first,'missed_investments':missed,'animal_escapes':escape,'crop_withers':wither,'daily':daily}

if __name__=='__main__':
    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,[919270004,919270007,919270008,919270019]))
    (B/'audit_production_gaps.json').write_text(json.dumps(rows,indent=2)+'\n')
    for r in rows:print(json.dumps({k:v for k,v in r.items() if k not in ['daily','missed_investments','animal_escapes','crop_withers']}),flush=True)
