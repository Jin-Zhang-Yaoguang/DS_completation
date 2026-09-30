"""P2 仅做 AST/源哈希检查；不定义加载或运行候选。"""
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


def definitions(tree):
    return {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


class ProjectFullBranch(ast.NodeTransformer):
    """只用于静态证明：选取full分支并移除新mode输入域守卫。"""
    def visit_FunctionDef(self, node):
        kept = [(arg, value) for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults) if arg.arg != "evidence_mode"]
        node.args.kwonlyargs = [arg for arg, _ in kept]
        node.args.kw_defaults = [value for _, value in kept]
        return self.generic_visit(node)

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "compact":
            return None
        return self.generic_visit(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id.endswith("_need"):
            reasons = {n.value for n in node.value.args if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            if reasons & {"INVALID_EVIDENCE_MODE", "COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS", "CACHE_EVIDENCE_MODE_MISMATCH"}:
                return None
        return self.generic_visit(node)

    def visit_If(self, node):
        if isinstance(node.test, ast.Name) and node.test.id == "compact":
            return [self.visit(n) for n in node.orelse]
        return self.generic_visit(node)


def assigned_value(tree, name):
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == name for t in n.targets))


def calls(fn, name):
    return [n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name]


def main():
    oldpath, path = HERE / "p1/integration_prototype.py", HERE / "integration_prototype.py"
    oldtree, tree = ast.parse(oldpath.read_bytes()), ast.parse(path.read_bytes())
    compile(tree, str(path), "exec")
    old, new = definitions(oldtree), definitions(tree)
    changed = [name for name in old if dump(old[name]) != dump(new[name])]
    added = sorted(set(new) - set(old))
    route_name = "_r10_route_admission_route_admission"
    projected = ProjectFullBranch().visit(deepcopy(new[route_name]))
    expected_changed = {route_name, "_r10_route_admission_PlanRouteCache", "_r10_integration_new_context", "_r10_integration_try_route"}
    preserved = json.loads((HERE / "p1_preservation.json").read_bytes())
    drift = [p for p, expected in preserved["original_sources"].items() if sha(Path(p)) != expected]
    snapshot_drift = [p for p, expected in preserved["p1_snapshot"].items() if sha(HERE / "p1" / p) != expected]
    unchanged_files = ["inline_modules.py", "calendar_compiler.py", "scheduler.py", "checker.py"]
    parent_path = next(Path(p) for p in preserved["original_sources"] if p.endswith("candidates/V125-R9/main.py"))
    parent = definitions(ast.parse(parent_path.read_bytes()))
    parent_functions = {n: v for n, v in parent.items() if isinstance(v, ast.FunctionDef)}
    parent_changed = [n for n, fn in parent_functions.items() if dump(fn) != dump(new[n])]
    legacy_copy = lambda fn: next(n for n in ast.walk(fn) if isinstance(n, ast.Assign) and
        any(isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == "legacy_fields_unchanged" for t in n.targets))
    commit = lambda fn: [n for n in ast.walk(fn) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and
        isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "update" and dump(n.value.func.value) == dump(ast.parse("cache.entries", mode="eval").body)]
    context_cache = calls(new["_r10_integration_new_context"], "_r10_route_admission_PlanRouteCache")[0]
    context_route = calls(new["_r10_integration_try_route"], route_name)[0]
    mode = lambda call: next(ast.literal_eval(k.value) for k in call.keywords if k.arg == "evidence_mode")
    forbidden = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("eval", "exec", "open", "__import__")]
    checks = {
        "syntax_compile_only": True,
        "p1_source_exact_e39": sha(oldpath) == "e39c7064ad404e3f79078cca97fde85dce4d496ac53cca5867347f0d8a235d42",
        "all_original_p0_p1_sources_and_attachments_unchanged": not drift,
        "p1_snapshot_unchanged": not snapshot_drift,
        "inliner_calendar_scheduler_checker_exact_p1": all((HERE / p).read_bytes() == (HERE / "p1" / p).read_bytes() for p in unchanged_files),
        "only_route_cache_and_two_integration_definitions_changed": set(changed) == expected_changed,
        "only_three_compact_helpers_added": added == sorted("_r10_route_admission_" + n for n in ("_compact_stats_copy", "_compact_entry", "_compact_public_stats")),
        "projected_full_route_ast_exact_p1": dump(projected) == dump(old[route_name]),
        "legacy_fields_unchanged_snapshot_ast_exact_p1": dump(legacy_copy(new[route_name])) == dump(legacy_copy(old[route_name])),
        "schedule_call_ast_exact_p1": [dump(n) for n in calls(new[route_name], "schedule")] == [dump(n) for n in calls(old[route_name], "schedule")],
        "checker_call_ast_exact_p1": [dump(n) for n in calls(new[route_name], "check")] == [dump(n) for n in calls(old[route_name], "check")],
        "single_original_staged_commit": len(commit(new[route_name])) == 1 and [dump(n) for n in commit(new[route_name])] == [dump(n) for n in commit(old[route_name])],
        "context_explicit_compact_mode": mode(context_cache) == "production_compact_v1",
        "route_explicit_compact_mode": mode(context_route) == "production_compact_v1",
        "economic_ast_exact_p1": dump(new["economic_plan_prefix"]) == dump(old["economic_plan_prefix"]),
        "old_r9_45_functions_44_unchanged": len(parent_functions) == 45 and parent_changed == ["economic_plan_prefix"],
        "params_exact_p1": assigned_value(tree, "PARAMS") == assigned_value(oldtree, "PARAMS"),
        "cid_opt02_prototype": assigned_value(tree, "CANDIDATE_ID") == "V125-R10-OPT02-PROTOTYPE",
        "agent_last_static_callable": list(new)[-1] == "agent",
        "no_dynamic_execution_or_filesystem_calls": not forbidden,
    }
    for name in ("route_admission.py", "integration_helpers.py", "build_candidate.py", "integration_prototype.py"):
        (HERE / (name + ".diff")).write_text("".join(difflib.unified_diff((HERE / "p1" / name).read_text().splitlines(keepends=True), (HERE / name).read_text().splitlines(keepends=True), fromfile="P1/" + name, tofile="P2/" + name)))
    result = {"schema": "r10-opt02-static-checks-v1", "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": sha(path), "route_sha256": sha(HERE / "route_admission.py"),
              "passed": sum(checks.values()), "total": len(checks), "checks": checks,
              "changed_definitions": changed, "added_helpers": added,
              "original_source_drift": drift, "p1_snapshot_drift": snapshot_drift,
              "counts": {"candidate_definition_loads": 0, "new_state": 0, "internal_economic": 0, "agent": 0, "solver": 0, "checker": 0, "engine": 0},
              "boundary": "full静态投影忽略新增mode输入域检查；实际完整接口/计划/状态/隔离/耗时待登记工程。"}
    (HERE / "static_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("source_sha256", "route_sha256", "passed", "total", "original_source_drift", "counts")}, ensure_ascii=False))
    assert all(checks.values()), checks


if __name__ == "__main__":
    main()
