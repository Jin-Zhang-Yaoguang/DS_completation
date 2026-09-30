"""OPT01 纯 AST 和文件哈希检查；不定义加载或运行候选。"""
import ast
from copy import deepcopy
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(node):
    return ast.dump(node, include_attributes=False)


def functions(tree):
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


class RestoreOuterCopies(ast.NodeTransformer):
    def __init__(self):
        self.flags = 0
        self.arguments = 0

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("default_schedule", "default_check"):
            flag = node.targets[0].id
            expected = ast.parse(("schedule" if flag == "default_schedule" else "check") + " is None", mode="eval").body
            if dump(node.value) != dump(expected):
                raise AssertionError("DEFAULT_FLAG_NOT_ORIGINAL_NONE_PARAMETER")
            self.flags += 1
            return None
        return self.generic_visit(node)

    def visit_IfExp(self, node):
        if isinstance(node.test, ast.Name) and node.test.id in ("default_schedule", "default_check"):
            self.arguments += 1
            return self.visit(node.orelse)
        return self.generic_visit(node)


def main():
    preservation = json.loads((HERE / "p0_preservation.json").read_bytes())
    old_path, new_path = HERE / "p0/integration_prototype.py", HERE / "integration_prototype.py"
    old, new = ast.parse(old_path.read_bytes()), ast.parse(new_path.read_bytes())
    compile(new, str(new_path), "exec")
    old_functions, new_functions = functions(old), functions(new)
    changed = [name for name in old_functions if dump(old_functions[name]) != dump(new_functions[name])]
    route_name = "_r10_route_admission_route_admission"
    restore = RestoreOuterCopies()
    normalized = restore.visit(deepcopy(new_functions[route_name]))
    module_old = ast.parse((HERE / "p0/route_admission.py").read_bytes())
    module_new = ast.parse((HERE / "route_admission.py").read_bytes())
    module_changed = [name for name in functions(module_old) if dump(functions(module_old)[name]) != dump(functions(module_new)[name])]
    parent_path = next(Path(path) for path in preservation["original_sources"] if path.endswith("candidates/V125-R9/main.py"))
    parent = functions(ast.parse(parent_path.read_bytes()))
    parent_changed = [name for name in parent if dump(parent[name]) != dump(new_functions[name])]
    bindings = [node.name for node in new.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))]
    drift = [path for path, expected in preservation["original_sources"].items() if sha(Path(path)) != expected]
    snapshot_drift = [path for path, expected in preservation["p0_snapshot"].items() if sha(HERE / "p0" / path) != expected]
    untouched = ["inline_modules.py", "integration_helpers.py", "calendar_compiler.py", "scheduler.py", "checker.py"]
    values = {}
    for node in new.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("PARAMS", "CANDIDATE_ID"):
            values[node.targets[0].id] = ast.literal_eval(node.value)
    old_params = next(ast.literal_eval(node.value) for node in old.body if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "PARAMS" for target in node.targets))
    prohibited = [node.func.id for node in ast.walk(new) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "__import__", "open")]
    checks = {
        "syntax_compile_only": True,
        "p0_source_exact940": sha(old_path) == "940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0",
        "original_sources_unchanged": not drift,
        "p0_source_and_timeout_snapshots_unchanged": not snapshot_drift,
        "five_copied_dependencies_byte_identical": all((HERE / name).read_bytes() == (HERE / "p0" / name).read_bytes() for name in untouched),
        "only_route_function_changes_from_p0": changed == [route_name],
        "two_exact_original_none_flags": restore.flags == 2,
        "three_conditional_outer_copies": restore.arguments == 3,
        "restoring_only_three_copies_and_flags_equals_p0_route_ast": dump(normalized) == dump(old_functions[route_name]),
        "pure_module_only_route_function_changed": module_changed == ["route_admission"],
        "old_r9_top_functions_count45": len(parent) == 45,
        "old_r9_44_functions_unchanged": parent_changed == ["economic_plan_prefix"],
        "economic_ast_exact_p0": dump(new_functions["economic_plan_prefix"]) == dump(old_functions["economic_plan_prefix"]),
        "params_exact_p0": values["PARAMS"] == old_params,
        "cid_only_opt01_prototype": values["CANDIDATE_ID"] == "V125-R10-OPT01-PROTOTYPE",
        "agent_last_static_callable_definition": bindings[-1] == "agent",
        "agent_defined_exactly_once": sum(node.name == "agent" for node in new.body if isinstance(node, ast.FunctionDef)) == 1,
        "no_dynamic_execution_or_filesystem_calls_in_candidate": not prohibited,
    }
    for name in ("route_admission.py", "build_candidate.py", "integration_prototype.py"):
        diff = "".join(difflib.unified_diff((HERE / "p0" / name).read_text().splitlines(keepends=True), (HERE / name).read_text().splitlines(keepends=True), fromfile="P0/" + name, tofile="OPT01/" + name))
        (HERE / (name + ".diff")).write_text(diff)
    result = {"schema": "r10-opt01-static-checks-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": sha(new_path), "route_sha256": sha(HERE / "route_admission.py"),
              "passed": sum(checks.values()), "total": len(checks), "checks": checks,
              "p0_changed_functions": changed, "r9_changed_functions": parent_changed,
              "original_source_drift": drift, "p0_snapshot_drift": snapshot_drift,
              "counts": {"candidate_definition_loads": 0, "new_state": 0, "internal_economic": 0, "agent": 0, "solver": 0, "checker": 0, "engine": 0},
              "boundary": "末callable仅静态定义顺序核对；真实get_last_callable定义加载及行为/耗时对照均待根授权工程控制。"}
    (HERE / "static_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("source_sha256", "route_sha256", "passed", "total", "original_source_drift", "counts")}, ensure_ascii=False))
    assert all(checks.values())


if __name__ == "__main__":
    main()
