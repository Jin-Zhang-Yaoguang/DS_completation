#!/usr/bin/env python3
"""Generate and compile an isolated kagsim_scenario extension.

The upstream kagsim.cpp, sim headers, and shared objects are read-only inputs.
All generated source, objects, extension binaries, and manifests live below
this replay_arena directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent.parent
CPPSIM_ROOT = (MODEL_ROOT / "community_research" / "2026-08-26" / "live_cli" /
               "external_repos" / "kaggriculture-cppsim")
UPSTREAM_CPP = CPPSIM_ROOT / "python" / "kagsim.cpp"
SIM_INCLUDE = CPPSIM_ROOT / "sim"
GENERATED_CPP = HERE / "kagsim_scenario.cpp"
BUILD_DIR = HERE / "build"
MANIFEST = HERE / "build_manifest.json"


METHOD_ANCHOR = "    py::dict observe(int player) const {"
BINDING_ANCHOR = "        .def(\"observe\", &Game::observe, py::arg(\"player\"),"
MODULE_ANCHOR = "PYBIND11_MODULE(kagsim, m) {"
INCLUDE_ANCHOR = '#include "../sim/sim.hpp"'
STREAM_CLASS_ANCHOR = '    py::class_<Stream>(m, "Stream")'
GAME_CLASS_ANCHOR = '    py::class_<Game>(m, "Game")'

FORCE_METHOD = r'''    void force_shops_now(const std::vector<std::string>& shop_names) {
        if (shop_names.size() > MAX_SHOP_INSTANCES)
            throw std::invalid_argument("too many forced shop instances");
        // A runtime prefix replaces any constructor-level schedule.  This is
        // called by scenario_runner only after a completed environment step.
        forced_shop_ids.clear();
        forced_unlock_steps.clear();
        sim.st.n_shops = static_cast<int>(shop_names.size());
        for (size_t out = 0; out < shop_names.size(); ++out) {
            int found = -1;
            for (int i = 0; i < N_SHOPS; ++i) {
                if (shop_names[out] == SHOP_NAMES[i]) { found = i; break; }
            }
            if (found < 0)
                throw std::invalid_argument("unknown forced shop: " + shop_names[out]);
            sim.st.shops[out] = static_cast<uint8_t>(found);
        }
    }
'''

FORCE_BINDING = '''        .def("force_shops", &Game::force_shops_now, py::arg("shops"),
             "Replace the currently visible unlocked-shop prefix. The caller "
             "must invoke this after step and before the next observation.")
'''


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def original_artifacts() -> list[Path]:
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    return sorted(path for path in CPPSIM_ROOT.rglob(f"kagsim*{suffix}") if path.is_file())


def artifact_hashes() -> dict[str, str]:
    return {str(path.relative_to(CPPSIM_ROOT)): sha256(path) for path in original_artifacts()}


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"expected exactly one {label} anchor, found {count}")
    return source.replace(old, new, 1)


def generate_source() -> dict[str, Any]:
    upstream = UPSTREAM_CPP.read_text(encoding="utf-8")
    source = upstream
    source = replace_once(source, INCLUDE_ANCHOR, '#include "sim.hpp"', "sim include")
    source = replace_once(source, MODULE_ANCHOR,
                          "PYBIND11_MODULE(kagsim_scenario, m) {", "module")
    source = replace_once(source, STREAM_CLASS_ANCHOR,
                          '    py::class_<Stream>(m, "Stream", py::module_local())',
                          "Stream module-local binding")
    source = replace_once(source, GAME_CLASS_ANCHOR,
                          '    py::class_<Game>(m, "Game", py::module_local())',
                          "Game module-local binding")
    source = replace_once(source, METHOD_ANCHOR, FORCE_METHOD + METHOD_ANCHOR,
                          "Game method")
    source = replace_once(source, BINDING_ANCHOR, FORCE_BINDING + BINDING_ANCHOR,
                          "Game binding")
    compile_note = (
        "// GENERATED MECHANICALLY by replay_arena/build_scenario.py.\n"
        "// Upstream source is never modified.\n"
    )
    source = compile_note + source
    temporary = GENERATED_CPP.with_name(GENERATED_CPP.name + ".tmp")
    temporary.write_text(source, encoding="utf-8")
    os.replace(temporary, GENERATED_CPP)
    return {
        "upstream_cpp_sha256": sha256(UPSTREAM_CPP),
        "generated_cpp_sha256": sha256(GENERATED_CPP),
        "mechanical_changes": [
            "include path redirected through read-only include_dirs",
            "PYBIND11 module renamed kagsim -> kagsim_scenario",
            "Stream/Game bindings isolated with py::module_local()",
            "Game.force_shops(list) runtime prefix binding injected",
        ],
    }


def find_pybind11_include() -> Path:
    candidates: list[Path] = []
    configured = os.environ.get("PYBIND11_INCLUDE")
    if configured:
        candidates.append(Path(configured))
    purelib = Path(sysconfig.get_paths()["purelib"])
    candidates.append(purelib / "pybind11" / "include")
    candidates.extend(sorted((Path.home() / ".cache" / "uv" / "archive-v0")
                             .glob("*/pybind11/include")))
    for candidate in candidates:
        if (candidate / "pybind11" / "pybind11.h").is_file():
            return candidate.resolve()
    raise RuntimeError(
        "pybind11 headers not found; set PYBIND11_INCLUDE to a directory "
        "containing pybind11/pybind11.h"
    )


def compile_extension() -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".so"
    output = BUILD_DIR / f"kagsim_scenario{suffix}"
    compiler = os.environ.get("CXX") or str(sysconfig.get_config_var("CXX") or "clang++").split()[0]
    command = [
        compiler,
        "-O3",
        "-shared",
        "-std=c++17",
        "-fvisibility=hidden",
        f"-I{find_pybind11_include()}",
        f"-I{sysconfig.get_paths()['include']}",
        f"-I{SIM_INCLUDE}",
        str(GENERATED_CPP),
        "-o",
        str(output),
    ]
    if sys.platform == "darwin":
        command[3:3] = ["-undefined", "dynamic_lookup"]
    else:
        command.insert(3, "-fPIC")
    subprocess.run(command, check=True, cwd=HERE)
    if not output.is_file():
        raise RuntimeError(f"scenario extension was not produced: {output}")
    return output


def build() -> dict[str, Any]:
    before_source = sha256(UPSTREAM_CPP)
    before_sos = artifact_hashes()
    generation = generate_source()
    extension = compile_extension()
    after_source = sha256(UPSTREAM_CPP)
    after_sos = artifact_hashes()
    unchanged = before_source == after_source and before_sos == after_sos
    if not unchanged:
        raise RuntimeError("upstream kagsim source or shared object changed during scenario build")
    payload = {
        "schema": "v116-replay-arena-build-v1",
        "module": "kagsim_scenario",
        "engine_version_expected": "1.32.7",
        "python_ext_suffix": sysconfig.get_config_var("EXT_SUFFIX"),
        "upstream": {
            "root": str(CPPSIM_ROOT),
            "cpp": str(UPSTREAM_CPP),
            "cpp_sha256_before": before_source,
            "cpp_sha256_after": after_source,
            "shared_objects_before": before_sos,
            "shared_objects_after": after_sos,
            "unchanged": unchanged,
        },
        "generated": {
            **generation,
            "extension": str(extension),
            "extension_sha256": sha256(extension),
        },
    }
    temporary = MANIFEST.with_name(MANIFEST.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    os.replace(temporary, MANIFEST)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-manifest", action="store_true")
    args = parser.parse_args()
    payload = build()
    if args.print_manifest:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["generated"]["extension"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
