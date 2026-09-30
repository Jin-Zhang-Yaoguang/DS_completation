"""Re-execute deterministic unit commands on historical states; count actual production."""
import collections
import contextlib
import copy
import importlib
import io
import json
from analyze import P


if __name__=='__main__':
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        official=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    replay=json.loads((P/'episode-112462673-replay.json').read_text())
    counts=[collections.Counter(),collections.Counter()];totals=[collections.Counter(),collections.Counter()]
    failed_feeds=[];animal_days=[collections.Counter(),collections.Counter()];wasted=[]
    for step in range(719):
        common=replay['steps'][step][0]['observation']
        for seat in [0,1]:
            farm=copy.deepcopy(common['farms'][seat]);private=copy.deepcopy(replay['steps'][step][seat]['observation']['private'])
            act=replay['steps'][step+1][seat]['action'];cmds=[act.get('farmer') or ['PASS']]+list(act.get('hands') or [])
            demand=collections.Counter(c[1] for c in cmds if len(c)>=2 and c[0]=='PLANT')
            blocked={k for k,n in demand.items() if n>private['seeds'].get(k,0)}
            for actor,command in enumerate(cmds):
                if actor>len(farm['hands']):continue
                pos=farm['farmer'] if actor==0 else farm['hands'][actor-1]
                tile=copy.deepcopy(farm['tiles'][pos[1]][pos[0]])
                before=copy.deepcopy(private['inventories'][actor]);seeds=dict(private['seeds']);before_fed=isinstance(tile,dict) and tile.get('fed_today',False)
                effective=['PASS'] if len(command)>=2 and command[0]=='PLANT' and command[1] in blocked else command
                official._apply_unit_action(farm,private,actor,effective,10,step//24,24,100)
                after=private['inventories'][actor];op=command[0];counts[seat]['requested_'+op]+=1
                if op in ['HARVEST','COLLECT_FERTILIZER']:
                    for item,qty in after.items():totals[seat][item]+=max(0,qty-before.get(item,0))
                if op=='PLANT':counts[seat]['planted_'+command[1]]+=max(0,seeds.get(command[1],0)-private['seeds'].get(command[1],0))
                if op=='FEED':
                    now=farm['tiles'][pos[1]][pos[0]]
                    success=not before_fed and isinstance(now,dict) and now.get('fed_today',False)
                    counts[seat]['successful_feed']+=success
                    if not success:
                        reason='no_animal' if not isinstance(tile,dict) or 'animal' not in tile else ('already_fed' if before_fed else ('no_carried_wheat' if before.get('WHEAT',0)<=0 else 'other'))
                        counts[seat]['failed_feed_'+reason]+=1
                    if not success and isinstance(tile,dict) and 'animal' in tile and not before_fed:
                        failed_feeds.append(dict(step=step,seat=seat,actor=actor,pos=pos,animal=tile['animal'],consecutive_unfed=tile['consecutive_unfed'],carried_wheat=before.get('WHEAT',0),shed_wheat=private['shed'].get('WHEAT',0)))
            if step%24==23:
                for row in farm['tiles']:
                    for tile in row:
                        if isinstance(tile,dict) and 'animal' in tile:
                            prefix=tile['animal'];animal_days[seat][prefix+'_days']+=1
                            animal_days[seat][prefix+'_fed_days']+=bool(tile['fed_today'])
                            animal_days[seat][prefix+'_care_and_feed_days']+=bool(tile['fed_today'] and tile['cared_today'])
    out=dict(scope='Official deterministic unit replay on recorded pre-step states; production is actual inventory increase, not requested harvest quantity.',production=[dict(x) for x in totals],unit_counts=[dict(x) for x in counts],animal_days=[dict(x) for x in animal_days],failed_feed_requests=failed_feeds)
    (P/'unit_production_audit_v2.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
