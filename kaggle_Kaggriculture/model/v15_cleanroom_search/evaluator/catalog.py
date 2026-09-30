"""Frozen inventory input for historical submissions that exceeded Rating 2000.

The values below are transcribed from a fresh official Kaggle CLI snapshot:

    kaggle competitions submissions -c kaggriculture -v --page-size 100

Snapshot time: 2026-08-24T22:00:30+08:00.  A repeated submission of identical
serving bytes is represented once, with every qualifying submission id kept as
evidence.  After exact-serving de-duplication, hidden retains every version;
development deterministically uses the highest historical publicScore version
in each pre-registered behaviour lineage.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalModel:
    catalog_key: str
    display_name: str
    archive: str
    expected_archive_sha256: str
    qualifying_submissions: tuple[tuple[int, float], ...]
    behaviour_lineage: str

    @property
    def peak_public_score(self) -> float:
        return max(score for _, score in self.qualifying_submissions)


SNAPSHOT = {
    "schema": "kaggriculture-v15-cli-submission-snapshot-1",
    "captured_at": "2026-08-24T22:00:30+08:00",
    "command": "kaggle competitions submissions -c kaggriculture -v --page-size 100",
    "threshold": "publicScore > 2000",
}


MODELS: tuple[HistoricalModel, ...] = (
    HistoricalModel(
        "v1_adaptive",
        "v1_adaptive_market",
        "kaggle_Kaggriculture/model/v1_adaptive_market/submission.tar.gz",
        "918509335c5bd09c6e816c22a42275d81b3bb2c686666963237dc9c63d93eacf",
        ((55575950, 2727.5), (55612135, 2488.0)),
        "adaptive_market_guard",
    ),
    HistoricalModel(
        "v2_survival",
        "v2_survival_guard",
        "kaggle_Kaggriculture/model/v2_survival_guard/submission.tar.gz",
        "dc7dbd150dbebbad88686d75242f377e87f020eba67b9a3f5163059e82bd655e",
        ((55578745, 2576.9),),
        "adaptive_market_guard",
    ),
    HistoricalModel(
        "v3_bc_ppo",
        "v3_bc_ppo_hybrid",
        "kaggle_Kaggriculture/model/v3_bc_ppo_hybrid/submission.tar.gz",
        "c6eaae2bb494da9bbab745bdf8cd2988b4f9638230179b32027b0e4b979905de",
        ((55585467, 2261.1),),
        "bc_ppo_executor",
    ),
    HistoricalModel(
        "v4_rule",
        "v4_rule_hybrid",
        "kaggle_Kaggriculture/model/v4_rule_hybrid/submission.tar.gz",
        "9c82f7311a2b3bf0c1686ed27c361214257739e1edc2c54355f0ad769be95b70",
        ((55592200, 2295.3),),
        "rule_hybrid",
    ),
    HistoricalModel(
        "v5_rule",
        "v5_rule_hybrid",
        "kaggle_Kaggriculture/model/v5_rule_hybrid/submission.tar.gz",
        "982ba04e20c28a6f949fe00d778c2d2d5170ee526d6220271130af1dd49a314c",
        ((55593180, 2368.6),),
        "rule_hybrid",
    ),
    HistoricalModel(
        "v5_ppo_topdays",
        "v5_ppo_v2_topdays",
        "kaggle_Kaggriculture/model/v5_ppo_v2_league/v5_ppo_v2_topdays/submission.tar.gz",
        "819443380c8fffbe4f8befd7e6c75daba52958d8bcac41407f88dc3d36ad7696",
        ((55612090, 2219.4),),
        "ppo_topday_residual",
    ),
    HistoricalModel(
        "v8_kawa",
        "v8_kawa_lead2_slot",
        "kaggle_Kaggriculture/model/v8_kawa_lead2_slot/submission.tar.gz",
        "f8f188e6d470809f3e2a14741f0daef075739922804988450e8b279922e2829f",
        ((55647343, 2066.1),),
        "kawa_market_microstructure",
    ),
    HistoricalModel(
        "v9_anti_mirror",
        "v9_anti_mirror",
        "kaggle_Kaggriculture/model/v9_anti_mirror/submission.tar.gz",
        "3e206004a25473299d45065c01624e1fe9565b9764143c2c1084a4ab6600eb12",
        ((55649391, 2079.3),),
        "kawa_market_microstructure",
    ),
    HistoricalModel(
        "r002_fixed",
        "v12_incumbent_r002",
        "kaggle_Kaggriculture/model/v12_incumbent_r002/submission.tar.gz",
        "6ff786cbba1a6440f844f9c77da934f6dd10b55e43f57b2bd852753cd21ae136",
        ((55713359, 2034.4),),
        "learned_router_incumbent",
    ),
    HistoricalModel(
        "a2_fixed",
        "v12a2_no_shop_gate",
        "kaggle_Kaggriculture/model/v12a2_no_shop_gate/submission.tar.gz",
        "e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8",
        ((55713355, 2429.0),),
        "a2_router_residual",
    ),
    HistoricalModel(
        "v13c_fixed",
        "v13c_a2_v8_no_wool_throttle",
        "kaggle_Kaggriculture/model/v13c_a2_v8_no_wool_throttle/submission.tar.gz",
        "ef279bbc937c73027ce17293aba19eeaa419563d2093880487ec9849400af0c1",
        ((55719781, 2062.9),),
        "a2_router_residual",
    ),
)


PARENT_CATALOG_KEY = "a2_fixed"
PRIMARY_ANCHOR_CATALOG_KEY = "a2_fixed"
SECONDARY_ANCHOR_CATALOG_KEY = "r002_fixed"
