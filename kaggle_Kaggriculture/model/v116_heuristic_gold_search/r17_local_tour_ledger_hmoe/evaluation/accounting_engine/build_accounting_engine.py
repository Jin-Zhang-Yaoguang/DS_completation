#!/usr/bin/env python3
"""Build an evaluator-only accounting fork of the frozen 1.32.7 kagsim.

The authoritative simulator is never edited.  This script verifies its source
hashes, copies the minimal build inputs below this directory, applies exact
fail-closed patches, and builds a separately named ``kagsim_accounting``
extension with one compiler process.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parents[3]
SOURCE_ROOT = (
    MODEL_ROOT
    / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
)
GENERATED_ROOT = HERE / "_generated" / "src"
MODULE_ROOT = HERE / "_module"
BUILD_TEMP = HERE / "_build" / "temp"
DEPENDENCY_ROOT = HERE / "_deps"
MANIFEST = HERE / "build_manifest.json"

EXPECTED_SOURCE_HASHES = {
    "sim/sim.hpp": "bcaf73c91cfe673199f985c0e7a70c204e6319a4f934a42272baf7edb3ce8096",
    "sim/pyrandom.hpp": "6745682729ff1cc0fee2a9727b4092dce2ddbc83e35058787bdd78c7ca592e5b",
    "python/kagsim.cpp": "f84a68e8b38922fc9f7114416fab2f7bda52a3072a64a2da0cd923b261141a64",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"fail closed: patch {label!r} expected once, found {count}")
    return source.replace(old, new, 1)


def verify_sources() -> dict[str, str]:
    observed: dict[str, str] = {}
    for relative, expected in EXPECTED_SOURCE_HASHES.items():
        path = SOURCE_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"fail closed: missing authoritative source {path}")
        observed[relative] = sha256(path)
        if expected is not None and observed[relative] != expected:
            raise RuntimeError(
                f"fail closed: source drift for {relative}: "
                f"expected {expected}, got {observed[relative]}"
            )
    return observed


def patch_sim(source: str) -> str:
    source = replace_once(
        source,
        """    int32_t discarded[N_ITEMS] = {0};
    int32_t produced[N_ITEMS] = {0};
    int32_t sold_units[N_ITEMS] = {0};
    double  sell_revenue = 0;   // coins actually received from SELLs
    double  total_spend = 0;    // coins actually paid out
""",
        """    int32_t discarded[N_ITEMS] = {0};
    int32_t produced[N_ITEMS] = {0};
    int32_t sold_units[N_ITEMS] = {0};
    double  sell_revenue = 0;   // coins actually received from SELLs
    double  total_spend = 0;    // coins actually paid out

    // Evaluator-only accounting.  These fields are cumulative, never read by
    // the interpreter and never serialized into an agent observation.
    int32_t bought_units[N_ITEMS] = {0};
    int32_t consumed_units[N_ITEMS] = {0};
    int32_t bought_seed_units[N_CROPS] = {0};
    int32_t planted_seed_units[N_CROPS] = {0};
    int32_t discarded_explicit[N_ITEMS] = {0};
    int32_t discarded_end_of_day[N_ITEMS] = {0};
    int32_t successful_hires = 0;
""",
        "accounting fields",
    )
    source = replace_once(
        source,
        """                f.discarded[it] += inv[it] - take;
                f.inv_erase(idx, it);
""",
        """                f.discarded[it] += inv[it] - take;
                f.discarded_explicit[it] += inv[it] - take;
                f.inv_erase(idx, it);
""",
        "explicit discard",
    )
    source = replace_once(
        source,
        """                    if (f.inv_take(idx, u.arg, 1)) {
                        Tile t{};
""",
        """                    if (f.inv_take(idx, u.arg, 1)) {
                        f.consumed_units[u.arg] += 1;
                        Tile t{};
""",
        "animal placement consumption",
    )
    source = replace_once(
        source,
        """                f.seeds[u.arg] -= 1;
                const CropDef& cd = CROPS[u.arg];
""",
        """                f.seeds[u.arg] -= 1;
                f.planted_seed_units[u.arg] += 1;
                const CropDef& cd = CROPS[u.arg];
""",
        "planted seed",
    )
    source = replace_once(
        source,
        """                if (!f.inv_take(idx, FERTILIZER, 1)) return;
                tile.fertilized_until_day = std::max<int16_t>(tile.fertilized_until_day,
""",
        """                if (!f.inv_take(idx, FERTILIZER, 1)) return;
                f.consumed_units[FERTILIZER] += 1;
                tile.fertilized_until_day = std::max<int16_t>(tile.fertilized_until_day,
""",
        "fertilizer consumption",
    )
    source = replace_once(
        source,
        """                if (!f.inv_take(idx, WHEAT, 1)) return;
                tile.fed_today = true;
""",
        """                if (!f.inv_take(idx, WHEAT, 1)) return;
                f.consumed_units[WHEAT] += 1;
                tile.fed_today = true;
""",
        "feed consumption",
    )
    source = replace_once(
        source,
        """                f.shed[item] += 1; f.shed_total += 1;
                st.market.inventory[item] -= 1;
                return true;
            case M_BUY_SEED:
""",
        """                f.shed[item] += 1; f.shed_total += 1;
                f.bought_units[item] += 1;
                st.market.inventory[item] -= 1;
                return true;
            case M_BUY_SEED:
""",
        "product purchase",
    )
    source = replace_once(
        source,
        """                f.money -= price; f.total_spend += price; f.seeds[item] += 1;
                return true;
""",
        """                f.money -= price; f.total_spend += price; f.seeds[item] += 1;
                f.bought_seed_units[item] += 1;
                return true;
""",
        "seed purchase",
    )
    source = replace_once(
        source,
        """                f.money -= price; f.total_spend += price;
                f.shed[item] += 1; f.shed_total += 1;
                return true;
""",
        """                f.money -= price; f.total_spend += price;
                f.shed[item] += 1; f.shed_total += 1;
                f.bought_units[item] += 1;
                return true;
""",
        "animal purchase",
    )
    source = replace_once(
        source,
        """        f.money -= cost; f.total_spend += cost;
        f.hires_today += 1;
""",
        """        f.money -= cost; f.total_spend += cost;
        f.hires_today += 1;
        f.successful_hires += 1;
""",
        "successful hire",
    )
    source = replace_once(
        source,
        """                f.discarded[it] += f.inv[u][it] - take;
                f.inv_erase(u, it);
""",
        """                f.discarded[it] += f.inv[u][it] - take;
                f.discarded_end_of_day[it] += f.inv[u][it] - take;
                f.inv_erase(u, it);
""",
        "end of day discard",
    )
    return source


def patch_binding(source: str) -> str:
    source = replace_once(
        source,
        "PYBIND11_MODULE(kagsim, m)",
        "PYBIND11_MODULE(kagsim_accounting, m)",
        "module name",
    )
    accounting_method = r'''    py::dict accounting(int player) const {
        if (player < 0 || player > 1)
            throw std::out_of_range("player must be 0 or 1");
        const Farm& f = sim.st.farms[player];
        py::dict produced, sold, discarded, discarded_explicit, discarded_eod;
        py::dict bought, consumed, shed, carried, total_inventory;
        for (int i = 0; i < N_ITEMS; ++i) {
            int carried_n = 0;
            for (int u = 0; u < f.n_units; ++u) carried_n += f.inv[u][i];
            produced[ITEM_NAMES[i]] = static_cast<int>(f.produced[i]);
            sold[ITEM_NAMES[i]] = static_cast<int>(f.sold_units[i]);
            discarded[ITEM_NAMES[i]] = static_cast<int>(f.discarded[i]);
            discarded_explicit[ITEM_NAMES[i]] = static_cast<int>(f.discarded_explicit[i]);
            discarded_eod[ITEM_NAMES[i]] = static_cast<int>(f.discarded_end_of_day[i]);
            bought[ITEM_NAMES[i]] = static_cast<int>(f.bought_units[i]);
            consumed[ITEM_NAMES[i]] = static_cast<int>(f.consumed_units[i]);
            shed[ITEM_NAMES[i]] = static_cast<int>(f.shed[i]);
            carried[ITEM_NAMES[i]] = carried_n;
            total_inventory[ITEM_NAMES[i]] = static_cast<int>(f.shed[i]) + carried_n;
        }
        py::dict bought_seeds, planted_seeds;
        for (int i = 0; i < N_CROPS; ++i) {
            bought_seeds[ITEM_NAMES[i]] = static_cast<int>(f.bought_seed_units[i]);
            planted_seeds[ITEM_NAMES[i]] = static_cast<int>(f.planted_seed_units[i]);
        }
        py::dict out;
        out["schema"] = "kagsim-accounting-v1";
        out["engine_version"] = "1.32.7";
        out["step"] = sim.st.step;
        out["produced"] = produced;
        out["sold_units"] = sold;
        out["sell_revenue"] = f.sell_revenue;
        out["total_spend"] = f.total_spend;
        out["discarded"] = discarded;
        out["discarded_explicit"] = discarded_explicit;
        out["discarded_end_of_day"] = discarded_eod;
        out["bought_units"] = bought;
        out["consumed_units"] = consumed;
        out["bought_seed_units"] = bought_seeds;
        out["planted_seed_units"] = planted_seeds;
        out["successful_hires"] = f.successful_hires;
        out["shed"] = shed;
        out["carried"] = carried;
        out["total_inventory"] = total_inventory;
        out["money"] = f.money;
        out["hands"] = f.n_units - 1;
        return out;
    }
'''
    source = replace_once(
        source,
        """    void step(const py::handle& a, const py::handle& b) {
""",
        accounting_method + """    void step(const py::handle& a, const py::handle& b) {
""",
        "accounting method",
    )
    source = replace_once(
        source,
        """        .def("observe", &Game::observe, py::arg("player"),
             "The observation dict the real interpreter hands this seat "
             "at the current step.")
        .def("step", &Game::step, py::arg("action_a"), py::arg("action_b"),
""",
        """        .def("observe", &Game::observe, py::arg("player"),
             "The observation dict the real interpreter hands this seat "
             "at the current step.")
        .def("accounting", &Game::accounting, py::arg("player"),
             "Evaluator-only cumulative accounting; never included in observe().")
        .def("step", &Game::step, py::arg("action_a"), py::arg("action_b"),
""",
        "accounting binding",
    )
    source = replace_once(
        source,
        """    m.attr("__version__") = "0.4.0";
    m.attr("ENGINE_VERSION") = "1.32.7";
""",
        """    m.attr("__version__") = "0.4.0-accounting.1";
    m.attr("ENGINE_VERSION") = "1.32.7";
    m.attr("INSTRUMENTATION_SCHEMA") = "kagsim-accounting-v1";
""",
        "module metadata",
    )
    return source


def write_generated_sources() -> dict[str, str]:
    (GENERATED_ROOT / "sim").mkdir(parents=True, exist_ok=True)
    (GENERATED_ROOT / "python").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_ROOT / "sim/pyrandom.hpp", GENERATED_ROOT / "sim/pyrandom.hpp")

    sim = patch_sim((SOURCE_ROOT / "sim/sim.hpp").read_text(encoding="utf-8"))
    binding = patch_binding((SOURCE_ROOT / "python/kagsim.cpp").read_text(encoding="utf-8"))
    (GENERATED_ROOT / "sim/sim.hpp").write_text(sim, encoding="utf-8")
    (GENERATED_ROOT / "python/kagsim_accounting.cpp").write_text(binding, encoding="utf-8")
    setup_source = '''from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

setup(
    name="kagsim-accounting-local",
    version="0.4.0.1",
    ext_modules=[Pybind11Extension(
        "kagsim_accounting", ["python/kagsim_accounting.cpp"],
        cxx_std=17, extra_compile_args=["-O3"])],
    cmdclass={"build_ext": build_ext},
)
'''
    (GENERATED_ROOT / "setup.py").write_text(setup_source, encoding="utf-8")
    return {
        "sim/sim.hpp": sha256(GENERATED_ROOT / "sim/sim.hpp"),
        "sim/pyrandom.hpp": sha256(GENERATED_ROOT / "sim/pyrandom.hpp"),
        "python/kagsim_accounting.cpp": sha256(
            GENERATED_ROOT / "python/kagsim_accounting.cpp"
        ),
        "setup.py": sha256(GENERATED_ROOT / "setup.py"),
    }


def build() -> Path:
    original_hashes = verify_sources()
    patched_hashes = write_generated_sources()
    MODULE_ROOT.mkdir(parents=True, exist_ok=True)
    BUILD_TEMP.mkdir(parents=True, exist_ok=True)
    for pattern in ("kagsim_accounting*.so", "kagsim_accounting*.pyd"):
        for stale in MODULE_ROOT.glob(pattern):
            stale.unlink()
    command = [
        sys.executable,
        "setup.py",
        "build_ext",
        "--force",
        "--build-lib",
        str(MODULE_ROOT),
        "--build-temp",
        str(BUILD_TEMP),
    ]
    environment = os.environ.copy()
    environment["MAX_JOBS"] = "1"
    environment["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
    if DEPENDENCY_ROOT.is_dir():
        prior = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = str(DEPENDENCY_ROOT) + (
            os.pathsep + prior if prior else ""
        )
    subprocess.run(command, cwd=GENERATED_ROOT, env=environment, check=True)
    modules = sorted(MODULE_ROOT.glob("kagsim_accounting*.so")) + sorted(
        MODULE_ROOT.glob("kagsim_accounting*.pyd")
    )
    if len(modules) != 1:
        raise RuntimeError(f"fail closed: expected one accounting module, got {modules}")
    module = modules[0]
    payload: Mapping[str, object] = {
        "schema": "kagsim-accounting-build-v1",
        "engine_version": "1.32.7",
        "module_name": "kagsim_accounting",
        "compiler_processes": 1,
        "local_build_dependency_root": str(DEPENDENCY_ROOT),
        "source_root": str(SOURCE_ROOT),
        "original_source_hashes": original_hashes,
        "patched_source_hashes": patched_hashes,
        "module_path": str(module),
        "module_sha256": sha256(module),
        "command": command,
        "status": "BUILT_NOT_VALIDATED",
    }
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return module


if __name__ == "__main__":
    build()
