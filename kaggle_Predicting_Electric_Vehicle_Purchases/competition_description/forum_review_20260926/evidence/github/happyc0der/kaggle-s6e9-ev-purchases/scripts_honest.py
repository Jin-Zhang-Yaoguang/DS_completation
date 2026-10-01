"""Honest CV: fixed rounds/epochs (no per-fold selection on the validation rows)."""
import sys
from src.cv import run
from src.features.static import GROUPS
from src.features.target_enc import TESpec
INC, COM = "Annual_Income_USD", "Daily_Commute_km"
full = GROUPS["raw"] + GROUPS["inc_stats"] + GROUPS["com_stats"] + GROUPS["digits"]
def temulti(m=3):
    return [TESpec((INC,), m=m), TESpec((COM,), m=m), TESpec((INC,), m=m, binwidth=100), TESpec((INC,), m=m, binwidth=500),
            TESpec((INC,), m=m, binwidth=2000), TESpec((COM,), m=m, binwidth=1), TESpec((COM,), m=m, binwidth=5)]
stage = sys.argv[1]
if stage == "gbdt":
    run("H_lgb_k10", full, te_specs=temulti(3), static_version="v2", params={"_fixed_rounds": 850}, ref="lgb_full_temulti_m3")
    run("H_lgb_k20", full, te_specs=temulti(3), static_version="v2", n_folds=20, params={"_fixed_rounds": 850}, ref="lgb_m3_k20")
    run("H_xgb_k10", full, te_specs=temulti(3), model="xgb", static_version="v2", params={"max_bin": 1024, "_fixed_rounds": 850}, ref="xgb_m3_teseed0")
    run("H_cb_k10", full, te_specs=temulti(3), model="cb", static_version="v2", params={"learning_rate": 0.08, "depth": 8, "_fixed_rounds": 330}, ref="cb_m3_plain")
elif stage == "nn":
    te1 = [TESpec((INC,), m=10), TESpec((COM,), m=10)]
    te_multi = te1 + [TESpec((INC,), m=10, binwidth=100), TESpec((INC,), m=10, binwidth=500),
                      TESpec((INC,), m=10, binwidth=2000), TESpec((COM,), m=10, binwidth=1), TESpec((COM,), m=10, binwidth=5)]
    ic = ("Environmental_Concern_Level", "Number_of_Cars_Owned", "Charging_Stations_Near_Home", "Charging_Stations_Near_Work", "Age")
    E9 = dict(lr=1e-3, min_count=10**9, extra_cats=ic, emb_cat=6, wd=3e-4, drop=0.4, fixed_epochs=22)
    run("H_nn_k10_s0", full, te_specs=te_multi, model="nn", params=E9, static_version="v2", ref="nn_E9_s0")
    run("H_nn_k20_s0", full, te_specs=te_multi, model="nn", params=E9, static_version="v2", n_folds=20, ref="nn_E9_k20_s0")
    run("H_nn_k10_s1", full, te_specs=te_multi, model="nn", params={**E9, "seed": 1}, static_version="v2", ref="nn_E9_s1")
