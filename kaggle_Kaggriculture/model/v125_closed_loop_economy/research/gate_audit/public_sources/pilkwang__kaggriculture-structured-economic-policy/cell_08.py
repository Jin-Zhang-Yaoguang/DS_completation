import ast

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable

source_text = MAIN_PATH.read_text(encoding="utf-8")
compile(ast.parse(source_text), str(MAIN_PATH), "exec")
schedule_agent = get_last_callable(source_text, path=str(MAIN_PATH))
assert callable(schedule_agent)

verification = {}
for seat in (0, 1):
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": 217 + seat},
        debug=True,
    )
    players = [str(MAIN_PATH), "starter"]
    if seat == 1:
        players.reverse()
    env.run(players)
    final = env.steps[-1]
    assert len(env.steps) == 720
    assert all(str(player.status) == "DONE" for player in final)
    verification[f"seat_{seat}"] = {
        "schedule_bank": float(final[seat].reward),
        "starter_bank": float(final[1 - seat].reward),
    }
print(verification)
