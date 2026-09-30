from pathlib import Path
import json,sys
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddw';sys.path.insert(0,str(D));import main,action_space as a
agent=main.Agent();program=agent.animal_program;agent.choices={i:g['original'] for i,g in enumerate(program['groups'])};checked=0
for key,g in program['events']['unit'].items():
 t,i=map(int,key.split(':'));tok=int(agent.arr['unit_tokens'][t,agent.config['fixed_prototype'],i]);assert agent.unit_token(t,i,tok)==tok,(key,g);checked+=1
for key,g in program['events']['market'].items():
 t,i=map(int,key.split(':'));tok=int(agent.arr['market_tokens'][t,agent.config['fixed_prototype'],i]);assert a.MARKET_TOKENS[tok]=='BUY_ANIMAL:'+agent.choices[g];checked+=1
assert program['animals_placed']==sum(g['count'] for g in program['groups'])==24
assert all(n==0 for n in program['stock_unused'].values())
for kind,events in program['events'].items():
 for key,g in events.items():assert program['groups'][g]['first_step']<=int(key.split(':')[0])
r={'checked_action_bindings':checked,'all_animals_placed':24,'unused_animals':0,'baseline_identity':True,'decisions_before_all_bound_tasks':True}
(B/'audit_animal_program.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
