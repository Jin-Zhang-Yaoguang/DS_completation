#!/usr/bin/env python3
"""Fail-closed audit utilities for the V15 clean-room generator.

This module never runs a Kaggriculture game or imports a candidate.  It validates
filesystem closures, static source, score-only feedback, and one-shot panel locks.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
POLICY_PATH = HERE / "generator_policy.json"
FEEDBACK_SCHEMA_PATH = HERE.parent / "cleanroom" / "score_only_feedback.schema.json"

INPUT_SEAL_SCHEMA = "kaggriculture-v15-cleanroom-input-seal-1"
CANDIDATE_SEAL_SCHEMA = "kaggriculture-v15-cleanroom-candidate-seal-1"
ATTESTATION_SCHEMA = "kaggriculture-v15-generator-attestation-1"
LOG_SCHEMA = "kaggriculture-v15-generation-log-event-1"
MANIFEST_SCHEMA = "kaggriculture-v15-submission-manifest-1"
QA_SCHEMA = "kaggriculture-v15-package-qa-1"
PRIVATE_RESULT_SCHEMA = "kaggriculture-v15-private-evaluation-1"
PUBLIC_FEEDBACK_SCHEMA = "kaggriculture-v15-score-only-feedback-v1"
DENYLIST_SCHEMA = "kaggriculture-v15-private-denylist-1"
HIDDEN_RESERVE_SCHEMA = "kaggriculture-v15-hidden-panel-reservation-1"
HIDDEN_COMPLETE_SCHEMA = "kaggriculture-v15-hidden-panel-completion-1"

ATTEMPT_RE = re.compile(r"^attempt_[0-9]{3}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
REQUIRED_OUTPUTS = {
    "main.py",
    "submission.tar.gz",
    "submission_manifest.json",
    "package_qa_report.json",
    "generation_attestation.json",
    "generation_log.jsonl",
    "strategy_note.md",
}
RATE_FIELDS = {
    "primary_anchor_pure_win_rate": (0.0, 1.0),
    "secondary_anchor_pure_win_rate": (0.0, 1.0),
    "lineage_equal_pool_score_rate": (0.0, 1.0),
    "lineage_equal_pool_score_ci95_low": (0.0, 1.0),
    "paired_uplift_rate": (-1.0, 1.0),
    "paired_uplift_ci95_low": (-1.0, 1.0),
}
PUBLIC_FEEDBACK_KEYS = {
    "schema",
    "attempt_id",
    "integrity_passed",
    *RATE_FIELDS,
    "overall_passed",
}
GENERIC_FORBIDDEN_TEXT = (
    "episodes_index",
    "replay_download",
    "agent_log",
    "submissionid",
    "kaggle_kaggriculture/model/",
    "kaggle_kaggriculture/model_data/",
    "/users/",
)
FORBIDDEN_NAMES = {
    "__builtins__",
    "__import__",
    "builtins",
    "breakpoint",
    "compile",
    "ctypes",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "help",
    "importlib",
    "inspect",
    "io",
    "locals",
    "marshal",
    "open",
    "os",
    "pathlib",
    "pickle",
    "pkgutil",
    "requests",
    "setattr",
    "socket",
    "subprocess",
    "sys",
    "urllib",
    "vars",
}
FORBIDDEN_ATTRIBUTES = {
    "__builtins__",
    "__class__",
    "__code__",
    "__globals__",
    "__loader__",
    "__mro__",
    "__spec__",
    "__subclasses__",
    "connect",
    "glob",
    "iterdir",
    "listdir",
    "open",
    "popen",
    "read",
    "read_bytes",
    "read_text",
    "recv",
    "rglob",
    "scandir",
    "send",
    "system",
    "urlopen",
    "walk",
    "write",
    "write_bytes",
    "write_text",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_object(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _strict_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(f"{label} keys differ: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")


def _safe_relative(raw: str) -> str:
    pure = PurePosixPath(raw)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"unsafe relative path: {raw!r}")
    return str(pure)


def _roots_overlap(roots: Mapping[str, Path]) -> None:
    items = list(roots.items())
    for index, (left_name, left) in enumerate(items):
        for right_name, right in items[index + 1 :]:
            if left == right or left in right.parents or right in left.parents:
                raise ValueError(f"allowlist roots overlap: {left_name}, {right_name}")


def regular_file_rows(root: Path, *, immutable_inputs: bool) -> list[dict[str, Any]]:
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"root is not a real directory: {root}")
    rows: list[dict[str, Any]] = []
    for base, directories, files in os.walk(root, followlinks=False):
        base_path = Path(base)
        for name in directories:
            child = base_path / name
            if child.is_symlink():
                raise ValueError(f"symlink directory rejected: {child}")
        for name in files:
            path = base_path / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                raise ValueError(f"non-regular file rejected: {path}")
            if info.st_nlink != 1:
                raise ValueError(f"hardlinked file rejected: {path}")
            if immutable_inputs and info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
                raise ValueError(f"group/other writable input rejected: {path}")
            relative = path.relative_to(root).as_posix()
            rows.append({"path": _safe_relative(relative), "sha256": sha256_file(path), "size_bytes": info.st_size})
    return sorted(rows, key=lambda row: row["path"])


def _closure(rows: Iterable[Mapping[str, Any]]) -> str:
    return sha256_object([{"path": row["path"], "sha256": row["sha256"], "size_bytes": row["size_bytes"]} for row in rows])


def validate_public_feedback(value: Mapping[str, Any]) -> None:
    schema = load_json(FEEDBACK_SCHEMA_PATH)
    if set(schema.get("properties", {})) != PUBLIC_FEEDBACK_KEYS or schema.get("additionalProperties") is not False:
        raise ValueError("score-only feedback schema drifted from firewall contract")
    _strict_keys(value, PUBLIC_FEEDBACK_KEYS, "public feedback")
    if value.get("schema") != PUBLIC_FEEDBACK_SCHEMA or not ATTEMPT_RE.fullmatch(str(value.get("attempt_id", ""))):
        raise ValueError("public feedback schema or attempt_id rejected")
    if type(value.get("integrity_passed")) is not bool or type(value.get("overall_passed")) is not bool:
        raise ValueError("public feedback booleans rejected")
    for field, (lower, upper) in RATE_FIELDS.items():
        number = value.get(field)
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not lower <= float(number) <= upper:
            raise ValueError(f"public feedback rate rejected: {field}")
    expected = bool(
        value["integrity_passed"]
        and value["primary_anchor_pure_win_rate"] >= 0.65
        and value["lineage_equal_pool_score_rate"] >= 0.65
        and value["lineage_equal_pool_score_ci95_low"] >= 0.60
        and value["paired_uplift_ci95_low"] > 0.10
    )
    if value["overall_passed"] is not expected:
        raise ValueError("public feedback overall_passed is inconsistent with fixed gates")


def seal_inputs(official_rules: Path, own_prior_work: Path, score_feedback: Path, output_root: Path, seal_path: Path) -> dict[str, Any]:
    roots = {
        "official_rules": official_rules.resolve(strict=True),
        "own_prior_work": own_prior_work.resolve(strict=True),
        "score_feedback": score_feedback.resolve(strict=True),
        "generator_output": output_root.resolve(strict=True),
    }
    _roots_overlap(roots)
    if any(output_root.iterdir()):
        raise ValueError("generator output must be empty before input seal")
    classes: dict[str, Any] = {}
    for name in ("official_rules", "own_prior_work", "score_feedback"):
        rows = regular_file_rows(roots[name], immutable_inputs=True)
        classes[name] = {"root": str(roots[name]), "files": rows, "closure_sha256": _closure(rows)}
    feedback_files = classes["score_feedback"]["files"]
    if len(feedback_files) > 1:
        raise ValueError("score_feedback must contain zero or one file")
    if feedback_files:
        validate_public_feedback(load_json(roots["score_feedback"] / feedback_files[0]["path"]))
    policy_hash = sha256_file(POLICY_PATH)
    core = {
        "schema": INPUT_SEAL_SCHEMA,
        "policy_sha256": policy_hash,
        "read_classes": classes,
        "generator_output_root": str(roots["generator_output"]),
    }
    payload = {**core, "seal_sha256": sha256_object(core)}
    write_exclusive(seal_path.resolve(), payload)
    return payload


def verify_input_seal(input_seal_path: Path, output_root: Path) -> dict[str, Any]:
    """Recompute every sealed read root before candidate bytes are audited."""

    input_seal = load_json(input_seal_path)
    _strict_keys(
        input_seal,
        {
            "schema",
            "policy_sha256",
            "read_classes",
            "generator_output_root",
            "seal_sha256",
        },
        "input seal",
    )
    unsigned = {key: value for key, value in input_seal.items() if key != "seal_sha256"}
    if (
        input_seal["schema"] != INPUT_SEAL_SCHEMA
        or input_seal["seal_sha256"] != sha256_object(unsigned)
        or input_seal["policy_sha256"] != sha256_file(POLICY_PATH)
    ):
        raise ValueError("input seal rejected or policy changed")

    root = output_root.resolve(strict=True)
    if Path(str(input_seal["generator_output_root"])).resolve() != root:
        raise ValueError("input seal output root changed")
    read_classes = input_seal["read_classes"]
    if not isinstance(read_classes, Mapping):
        raise ValueError("input seal read_classes must be an object")
    expected_classes = {"official_rules", "own_prior_work", "score_feedback"}
    _strict_keys(read_classes, expected_classes, "input seal read classes")

    roots = {"generator_output": root}
    current_by_class: dict[str, list[dict[str, Any]]] = {}
    for name in sorted(expected_classes):
        group = read_classes[name]
        if not isinstance(group, Mapping):
            raise ValueError(f"sealed input class must be an object: {name}")
        _strict_keys(group, {"root", "files", "closure_sha256"}, f"sealed input class {name}")
        sealed_root = Path(str(group["root"])).resolve(strict=True)
        roots[name] = sealed_root
        current = regular_file_rows(sealed_root, immutable_inputs=True)
        current_by_class[name] = current
        if current != group["files"] or _closure(current) != group["closure_sha256"]:
            raise ValueError(f"sealed input closure changed: {name}")
    _roots_overlap(roots)

    feedback_files = current_by_class["score_feedback"]
    if len(feedback_files) > 1:
        raise ValueError("score_feedback must contain zero or one file")
    if feedback_files:
        validate_public_feedback(
            load_json(roots["score_feedback"] / feedback_files[0]["path"])
        )
    return input_seal


class SourceAudit(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[dict[str, Any]] = []
        self.agent_defined = False

    def reject(self, node: ast.AST, category: str) -> None:
        self.violations.append({"category": category, "line": int(getattr(node, "lineno", 0) or 0)})

    def visit_Import(self, node: ast.Import) -> None:
        self.reject(node, "import_forbidden")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.reject(node, "import_forbidden")

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name == "agent":
            self.agent_defined = True
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if node.name == "agent":
            self.agent_defined = True
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in FORBIDDEN_NAMES:
            self.reject(node, "runtime_escape_name")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in FORBIDDEN_ATTRIBUTES or (node.attr.startswith("__") and node.attr.endswith("__")):
            self.reject(node, "runtime_escape_attribute")
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        value = node.value
        if isinstance(value, bytes) and len(value) > 64:
            self.reject(node, "encoded_payload_literal")
        if isinstance(value, str):
            if value in FORBIDDEN_NAMES or value in FORBIDDEN_ATTRIBUTES or (value.startswith("__") and value.endswith("__")):
                self.reject(node, "runtime_escape_literal")
            if len(value) > 2048:
                self.reject(node, "oversized_string_literal")
            compact = re.sub(r"\s+", "", value)
            if len(compact) >= 128 and (re.fullmatch(r"[0-9a-fA-F]+", compact) or re.fullmatch(r"[A-Za-z0-9+/=]+", compact)):
                self.reject(node, "encoded_payload_literal")


def _scan_text(path: Path, denylist_path: Path | None) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    folded = text.casefold()
    hits: list[dict[str, Any]] = []
    for token in GENERIC_FORBIDDEN_TEXT:
        if token.casefold() in folded:
            hits.append({"category": "forbidden_path_or_artifact_reference", "term_sha256": sha256_bytes(token.encode()), "path": path.name})
    if denylist_path is not None:
        raw = load_json(denylist_path)
        _strict_keys(raw, {"schema", "terms"}, "denylist")
        if raw["schema"] != DENYLIST_SCHEMA or not isinstance(raw["terms"], list):
            raise ValueError("private denylist rejected")
        for row in raw["terms"]:
            _strict_keys(row, {"category", "value"}, "denylist term")
            category, token = str(row["category"]), str(row["value"])
            if not SLUG_RE.fullmatch(category) or len(token) < 2:
                raise ValueError("private denylist term rejected")
            if token.casefold() in folded:
                hits.append({"category": category, "term_sha256": sha256_bytes(token.casefold().encode()), "path": path.name})
    return hits


def _validate_manifest(root: Path) -> tuple[dict[str, Any], str]:
    manifest = load_json(root / "submission_manifest.json")
    _strict_keys(manifest, {"schema", "attempt_id", "entrypoint", "archive_sha256", "files", "candidate_sha256"}, "submission manifest")
    if manifest["schema"] != MANIFEST_SCHEMA or not ATTEMPT_RE.fullmatch(str(manifest["attempt_id"])) or manifest["entrypoint"] != "main.py":
        raise ValueError("submission manifest header rejected")
    rows = manifest["files"]
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("runtime closure must contain exactly main.py")
    row = rows[0]
    _strict_keys(row, {"path", "sha256", "size_bytes"}, "submission manifest file")
    if row["path"] != "main.py" or row["sha256"] != sha256_file(root / "main.py") or row["size_bytes"] != (root / "main.py").stat().st_size:
        raise ValueError("main.py differs from submission manifest")
    candidate_sha = _closure(rows)
    if manifest["candidate_sha256"] != candidate_sha or manifest["archive_sha256"] != sha256_file(root / "submission.tar.gz"):
        raise ValueError("manifest closure/archive hash mismatch")
    with tarfile.open(root / "submission.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        if len(members) != 1 or _safe_relative(members[0].name) != "main.py" or not members[0].isfile() or members[0].issym() or members[0].islnk():
            raise ValueError("runtime archive must contain one regular main.py")
        member = members[0]
        if member.mtime != 0 or member.uid != 0 or member.gid != 0 or member.uname or member.gname or stat.S_IMODE(member.mode) != 0o644:
            raise ValueError("runtime archive metadata is not deterministic")
        stream = archive.extractfile(members[0])
        if stream is None or sha256_bytes(stream.read(2_097_153)) != row["sha256"]:
            raise ValueError("archived main.py differs from manifest")
    return manifest, candidate_sha


def _validate_qa(root: Path, attempt_id: str, candidate_sha: str) -> None:
    qa = load_json(root / "package_qa_report.json")
    _strict_keys(qa, {"schema", "attempt_id", "candidate_sha256", "syntax_checked", "callable_loader_passed", "self_play_smoke_passed", "generator_claim_only"}, "package QA")
    if qa != {
        "schema": QA_SCHEMA,
        "attempt_id": attempt_id,
        "candidate_sha256": candidate_sha,
        "syntax_checked": True,
        "callable_loader_passed": True,
        "self_play_smoke_passed": True,
        "generator_claim_only": True,
    }:
        raise ValueError("package QA claim rejected")


def _validate_attestation(root: Path, input_seal: Mapping[str, Any], attempt_id: str) -> None:
    value = load_json(root / "generation_attestation.json")
    expected_keys = {
        "schema", "attempt_id", "policy_sha256", "input_seal_sha256", "fork_turns",
        "history_inherited", "network_accessed", "filesystem_discovery_used",
        "shell_discovery_used", "outside_allowlist_read", "individual_games_read",
        "replays_or_episodes_read", "opponent_actions_read",
        "historical_model_source_or_design_read", "model_pool_identity_mapping_read",
        "all_reads_declared",
    }
    _strict_keys(value, expected_keys, "generator attestation")
    if value["schema"] != ATTESTATION_SCHEMA or value["attempt_id"] != attempt_id or value["policy_sha256"] != input_seal["policy_sha256"] or value["input_seal_sha256"] != input_seal["seal_sha256"] or value["fork_turns"] != "none":
        raise ValueError("generator attestation identity rejected")
    required_false = expected_keys - {"schema", "attempt_id", "policy_sha256", "input_seal_sha256", "fork_turns", "all_reads_declared"}
    if any(value[key] is not False for key in required_false) or value["all_reads_declared"] is not True:
        raise ValueError("generator attestation does not fail closed")


def _load_log(path: Path) -> list[dict[str, Any]]:
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank generation log line: {number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError("generation log row must be an object")
        records.append(value)
    if not records:
        raise ValueError("generation log is empty")
    return records


def _validate_log(root: Path, input_seal: Mapping[str, Any], attempt_id: str, candidate_sha: str) -> None:
    records = _load_log(root / "generation_log.jsonl")
    if [row.get("seq") for row in records] != list(range(1, len(records) + 1)):
        raise ValueError("generation log sequence is not contiguous")
    sealed_files = {
        (class_name, row["path"]): row["sha256"]
        for class_name, group in input_seal["read_classes"].items()
        for row in group["files"]
    }
    saw_rules = False
    saw_main_write = False
    for index, row in enumerate(records):
        event = row.get("event")
        if row.get("schema") != LOG_SCHEMA:
            raise ValueError("generation log schema rejected")
        if event == "session_start":
            _strict_keys(row, {"schema", "seq", "event", "attempt_id", "policy_sha256", "input_seal_sha256", "fork_turns", "history_inherited"}, "session_start")
            if index != 0 or row["attempt_id"] != attempt_id or row["policy_sha256"] != input_seal["policy_sha256"] or row["input_seal_sha256"] != input_seal["seal_sha256"] or row["fork_turns"] != "none" or row["history_inherited"] is not False:
                raise ValueError("session_start rejected")
        elif event == "read":
            _strict_keys(row, {"schema", "seq", "event", "class", "path", "sha256"}, "read event")
            class_name = str(row["class"])
            relative = _safe_relative(str(row["path"]))
            # A generator may spell a root-relative declaration either as
            # ``README.md`` or ``official_rules/README.md``.  The class already
            # selects the sealed root, so strip exactly one matching prefix;
            # all other prefixes remain outside the closure and are rejected.
            prefix = class_name + "/"
            if relative.startswith(prefix):
                relative = _safe_relative(relative[len(prefix) :])
            if class_name == "generator_output":
                path = root / relative
                if not path.is_file() or row["sha256"] != sha256_file(path):
                    raise ValueError("generator_output read is not final/hash-bound")
            elif sealed_files.get((class_name, relative)) != row["sha256"]:
                raise ValueError("read event is outside or differs from sealed inputs")
            saw_rules |= class_name == "official_rules"
        elif event == "write":
            _strict_keys(row, {"schema", "seq", "event", "class", "path", "sha256"}, "write event")
            relative = _safe_relative(str(row["path"]))
            path = root / relative
            if row["class"] != "generator_output" or relative not in REQUIRED_OUTPUTS or not path.is_file() or row["sha256"] != sha256_file(path):
                raise ValueError("write event rejected")
            saw_main_write |= relative == "main.py"
        elif event == "candidate_sealed":
            _strict_keys(row, {"schema", "seq", "event", "candidate_sha256"}, "candidate_sealed")
            if row["candidate_sha256"] != candidate_sha:
                raise ValueError("candidate_sealed hash rejected")
        elif event == "session_end":
            _strict_keys(row, {"schema", "seq", "event", "all_reads_declared"}, "session_end")
            if index != len(records) - 1 or row["all_reads_declared"] is not True:
                raise ValueError("session_end rejected")
        else:
            raise ValueError(f"generation log event rejected: {event!r}")
    if records[0]["event"] != "session_start" or records[-1]["event"] != "session_end" or not saw_rules or not saw_main_write or not any(row["event"] == "candidate_sealed" for row in records):
        raise ValueError("generation log required events absent")
    feedback_rows = input_seal["read_classes"]["score_feedback"]["files"]
    if feedback_rows and not any(row.get("event") == "read" and row.get("class") == "score_feedback" for row in records):
        raise ValueError("sealed score feedback was not declared read")


def audit_candidate(output_root: Path, input_seal_path: Path, denylist_path: Path | None, seal_path: Path) -> dict[str, Any]:
    root = output_root.resolve(strict=True)
    input_seal = verify_input_seal(input_seal_path, root)
    rows = regular_file_rows(root, immutable_inputs=False)
    names = {row["path"] for row in rows}
    policy = load_json(POLICY_PATH)
    candidate_policy = policy["candidate"]
    if set(candidate_policy.get("required_files", [])) != REQUIRED_OUTPUTS or candidate_policy.get("forbid_all_imports") is not True or candidate_policy.get("runtime_archive_members") != ["main.py"]:
        raise ValueError("candidate policy drifted from firewall implementation")
    if names != REQUIRED_OUTPUTS or len(rows) > int(candidate_policy["maximum_files"]):
        raise ValueError(f"candidate output closure rejected: {sorted(names)}")
    if any(row["size_bytes"] > int(candidate_policy["maximum_file_bytes"]) for row in rows) or sum(row["size_bytes"] for row in rows) > int(candidate_policy["maximum_total_bytes"]):
        raise ValueError("candidate size limit exceeded")
    manifest, candidate_sha = _validate_manifest(root)
    attempt_id = manifest["attempt_id"]
    _validate_qa(root, attempt_id, candidate_sha)
    _validate_attestation(root, input_seal, attempt_id)
    _validate_log(root, input_seal, attempt_id, candidate_sha)
    source = (root / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="main.py")
    source_audit = SourceAudit()
    source_audit.visit(tree)
    if not source_audit.agent_defined:
        source_audit.violations.append({"category": "agent_callable_absent", "line": 0})
    leakage = _scan_text(root / "main.py", denylist_path) + _scan_text(root / "strategy_note.md", denylist_path)
    if source_audit.violations or leakage:
        raise ValueError(json.dumps({"static_categories": source_audit.violations, "leakage_hashes": leakage}, sort_keys=True))
    core = {
        "schema": CANDIDATE_SEAL_SCHEMA,
        "verdict": "PASS",
        "passed": True,
        "attempt_id": attempt_id,
        "candidate_sha256": candidate_sha,
        "candidate_archive_sha256": manifest["archive_sha256"],
        "candidate_serving_sha256": sha256_file(root / "main.py"),
        "policy_sha256": input_seal["policy_sha256"],
        "input_seal_sha256": input_seal["seal_sha256"],
        "input_seal_file_sha256": sha256_file(input_seal_path),
        "output_root": str(root),
        "files": rows,
        "checks": {
            "fork_turns_none_attested": True,
            "allowlist_reads_declared": True,
            "archive_exactly_main": True,
            "zero_imports": True,
            "runtime_io_absent": True,
            "private_denylist_clear": True,
            "package_qa_is_generator_claim_only": True,
        },
    }
    payload = {**core, "seal_sha256": sha256_object(core)}
    write_exclusive(seal_path.resolve(), payload)
    return payload


def verify_candidate_seal(output_root: Path, seal_path: Path) -> dict[str, Any]:
    seal = load_json(seal_path)
    if seal.get("schema") != CANDIDATE_SEAL_SCHEMA or seal.get("seal_sha256") != sha256_object({key: value for key, value in seal.items() if key != "seal_sha256"}) or Path(seal.get("output_root", "")).resolve() != output_root.resolve(strict=True):
        raise ValueError("candidate seal rejected")
    current = regular_file_rows(output_root.resolve(), immutable_inputs=False)
    if current != seal.get("files") or _closure([row for row in current if row["path"] == "main.py"]) != seal.get("candidate_sha256"):
        raise ValueError("candidate bytes changed after seal")
    return seal


def reduce_feedback(private_result_path: Path, output_path: Path) -> dict[str, Any]:
    private = load_json(private_result_path)
    base_keys = {"schema", "attempt_id", "candidate_sha256", "integrity_passed", "anchors", "pool", "parent"}
    if set(private) not in {frozenset(base_keys), frozenset(base_keys | {"private_details"})}:
        raise ValueError("private evaluation keys rejected")
    if private["schema"] != PRIVATE_RESULT_SCHEMA or not ATTEMPT_RE.fullmatch(str(private["attempt_id"])) or not SHA_RE.fullmatch(str(private["candidate_sha256"])):
        raise ValueError("private evaluation header rejected")
    anchors = private["anchors"]
    _strict_keys(anchors, {"primary", "secondary"}, "private anchors")
    for label in ("primary", "secondary"):
        _strict_keys(anchors[label], {"games", "pure_win_rate"}, f"private {label}")
        if anchors[label]["games"] != 200:
            raise ValueError("each direct anchor must have exactly 200 games")
    _strict_keys(private["pool"], {"lineage_equal_score_rate", "source_cluster_ci95_low"}, "private pool")
    _strict_keys(private["parent"], {"paired_uplift_rate", "paired_uplift_ci95_low"}, "private parent")
    payload = {
        "schema": PUBLIC_FEEDBACK_SCHEMA,
        "attempt_id": private["attempt_id"],
        "integrity_passed": private["integrity_passed"],
        "primary_anchor_pure_win_rate": anchors["primary"]["pure_win_rate"],
        "secondary_anchor_pure_win_rate": anchors["secondary"]["pure_win_rate"],
        "lineage_equal_pool_score_rate": private["pool"]["lineage_equal_score_rate"],
        "lineage_equal_pool_score_ci95_low": private["pool"]["source_cluster_ci95_low"],
        "paired_uplift_rate": private["parent"]["paired_uplift_rate"],
        "paired_uplift_ci95_low": private["parent"]["paired_uplift_ci95_low"],
        "overall_passed": False,
    }
    payload["overall_passed"] = bool(
        payload["integrity_passed"]
        and payload["primary_anchor_pure_win_rate"] >= 0.65
        and payload["lineage_equal_pool_score_rate"] >= 0.65
        and payload["lineage_equal_pool_score_ci95_low"] >= 0.60
        and payload["paired_uplift_ci95_low"] > 0.10
    )
    validate_public_feedback(payload)
    write_exclusive(output_path.resolve(), payload)
    receipt_core = {
        "schema": "kaggriculture-v15-feedback-receipt-1",
        "attempt_id": private["attempt_id"],
        "candidate_sha256": private["candidate_sha256"],
        "policy_sha256": sha256_file(POLICY_PATH),
        "private_result_sha256": sha256_file(private_result_path),
        "public_feedback_sha256": sha256_file(output_path),
    }
    receipt = {**receipt_core, "seal_sha256": sha256_object(receipt_core)}
    write_exclusive(output_path.with_suffix(output_path.suffix + ".receipt.json"), receipt)
    return payload


def reserve_hidden(lock_dir: Path, panel_manifest: Path, candidate_seal: Path, evaluator: Path) -> dict[str, Any]:
    lock_dir = lock_dir.resolve()
    lock_dir.mkdir(parents=True, exist_ok=True)
    reserve_path = lock_dir / "hidden_panel.reserved.json"
    core = {
        "schema": HIDDEN_RESERVE_SCHEMA,
        "status": "CONSUMED_ON_RESERVATION",
        "panel_manifest_sha256": sha256_file(panel_manifest),
        "candidate_seal_sha256": sha256_file(candidate_seal),
        "evaluator_sha256": sha256_file(evaluator),
        "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload = {**core, "seal_sha256": sha256_object(core)}
    write_exclusive(reserve_path, payload)
    return payload


def complete_hidden(lock_dir: Path, result: Path) -> dict[str, Any]:
    lock_dir = lock_dir.resolve(strict=True)
    reserve_path = lock_dir / "hidden_panel.reserved.json"
    reserve = load_json(reserve_path)
    if reserve.get("schema") != HIDDEN_RESERVE_SCHEMA or reserve.get("seal_sha256") != sha256_object({key: value for key, value in reserve.items() if key != "seal_sha256"}):
        raise ValueError("hidden reservation rejected")
    core = {
        "schema": HIDDEN_COMPLETE_SCHEMA,
        "reservation_file_sha256": sha256_file(reserve_path),
        "result_sha256": sha256_file(result),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload = {**core, "seal_sha256": sha256_object(core)}
    write_exclusive(lock_dir / "hidden_panel.completed.json", payload)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    seal = commands.add_parser("seal-inputs")
    seal.add_argument("--official-rules", type=Path, required=True)
    seal.add_argument("--own-prior-work", type=Path, required=True)
    seal.add_argument("--score-feedback", type=Path, required=True)
    seal.add_argument("--output-root", type=Path, required=True)
    seal.add_argument("--seal", type=Path, required=True)
    audit = commands.add_parser("audit-candidate")
    audit.add_argument("--output-root", type=Path, required=True)
    audit.add_argument("--input-seal", type=Path, required=True)
    audit.add_argument("--denylist", type=Path)
    audit.add_argument("--seal", type=Path, required=True)
    verify = commands.add_parser("verify-candidate-seal")
    verify.add_argument("--output-root", type=Path, required=True)
    verify.add_argument("--seal", type=Path, required=True)
    feedback = commands.add_parser("reduce-feedback")
    feedback.add_argument("--private-result", type=Path, required=True)
    feedback.add_argument("--output", type=Path, required=True)
    reserve = commands.add_parser("reserve-hidden")
    reserve.add_argument("--lock-dir", type=Path, required=True)
    reserve.add_argument("--panel-manifest", type=Path, required=True)
    reserve.add_argument("--candidate-seal", type=Path, required=True)
    reserve.add_argument("--evaluator", type=Path, required=True)
    complete = commands.add_parser("complete-hidden")
    complete.add_argument("--lock-dir", type=Path, required=True)
    complete.add_argument("--result", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "seal-inputs":
        result = seal_inputs(args.official_rules, args.own_prior_work, args.score_feedback, args.output_root, args.seal)
    elif args.command == "audit-candidate":
        result = audit_candidate(args.output_root, args.input_seal, args.denylist, args.seal)
    elif args.command == "verify-candidate-seal":
        result = verify_candidate_seal(args.output_root, args.seal)
    elif args.command == "reduce-feedback":
        result = reduce_feedback(args.private_result, args.output)
    elif args.command == "reserve-hidden":
        result = reserve_hidden(args.lock_dir, args.panel_manifest, args.candidate_seal, args.evaluator)
    else:
        result = complete_hidden(args.lock_dir, args.result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
