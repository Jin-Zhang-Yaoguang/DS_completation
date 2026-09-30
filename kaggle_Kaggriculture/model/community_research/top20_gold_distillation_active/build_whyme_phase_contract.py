#!/usr/bin/env python3
"""Strip diagnostic actions and retain the six-hour semantic phase contract."""
from __future__ import annotations
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/"whyme_role_option_contract_diagnostic.json"
output=HERE/"whyme_role_phase_contract.json"
payload=json.loads(source.read_text(encoding="utf-8"))
for row in payload["days"].values():
    width6=(row.get("market_window_budgets") or {}).get("6",{})
    for key in ("market_diagnostic","market_day_budget","market_phase_budgets","market_window_budgets"):
        row.pop(key,None)
    row["market_window_budgets"]={"6":width6}
payload["schema"]="kaggriculture-top20-whyme-six-hour-phase-hmoe-v1"
payload["runtime_contract"]={"unit_move_actions_stored":False,"unit_action_source":"state_recovered_daily_option_queue",
                             "market_action_source":"six_hour_semantic_resource_budget",
                             "market_tape":False,"step_lookup":False,"future_features":False}
payload.pop("market_order_count",None)
output.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
print(json.dumps({"output":str(output),"days":len(payload["days"]),"teacher":payload["source"]["teacher"]},ensure_ascii=False))
