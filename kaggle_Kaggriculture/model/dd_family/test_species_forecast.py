"""Check the planner's species refresh against the official engine."""
from pathlib import Path
import contextlib,copy,importlib,io,json,random,sys
B=Path(__file__).resolve().parent;sys.path.insert(0,str(B/'ddai'))
import rules,species_planner as planner
with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
 engine=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
rng=random.Random(26482);checks=0
for species in planner.SPECIES:
 for _ in range(500):
  day=rng.randrange(30);tile=rules._new_animal(species,rng.randrange(day+1))
  tile.update(yield_units=rng.randrange(rules.ANIMALS[species]['max_held']+1),fed_today=bool(rng.randrange(2)),cared_today=bool(rng.randrange(2)),consecutive_unfed=rng.randrange(2),pending_care_bonus=rng.randrange(6))
  actual=copy.deepcopy(tile);farm={'tiles':[[copy.deepcopy(tile)]]}
  planner.refresh(actual,day);engine._daily_refresh_animals(farm,day);expected=farm['tiles'][0][0]
  if 'animal' in expected:assert actual==expected,(actual,expected)
  else:assert 'animal' not in actual
  checks+=1
result={'checks':checks,'species':list(planner.SPECIES),'official_engine':'1.32.7','passed':True,'scope':'daily biological refresh only; market and future opponent flow are forecasts'}
(B/'audit_ddai_refresh.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
