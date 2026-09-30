from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


FIREWALL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIREWALL_ROOT))
import firewall  # noqa: E402


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FirewallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.rules = self.root / "rules"
        self.prior = self.root / "prior"
        self.feedback = self.root / "feedback"
        self.output = self.root / "output"
        self.private = self.root / "private"
        for path in (self.rules, self.prior, self.feedback, self.output, self.private):
            path.mkdir()
        (self.rules / "official.txt").write_text("official game rules\n", encoding="utf-8")
        self.input_seal_path = self.private / "input_seal.json"
        self.input_seal = firewall.seal_inputs(
            self.rules, self.prior, self.feedback, self.output, self.input_seal_path
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _archive_main(self, source: bytes) -> Path:
        archive_path = self.output / "submission.tar.gz"
        with archive_path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with tarfile.open(fileobj=zipped, mode="w") as archive:
                    info = tarfile.TarInfo("main.py")
                    info.size = len(source)
                    info.mtime = 0
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(source))
        return archive_path

    def make_candidate(self, source: str = "def agent(observation, configuration):\n    return []\n", note: str = "First-principles policy.\n") -> str:
        attempt = "attempt_001"
        source_bytes = source.encode()
        (self.output / "main.py").write_bytes(source_bytes)
        archive = self._archive_main(source_bytes)
        row = {"path": "main.py", "sha256": firewall.sha256_bytes(source_bytes), "size_bytes": len(source_bytes)}
        candidate_sha = firewall._closure([row])
        manifest = {
            "schema": firewall.MANIFEST_SCHEMA,
            "attempt_id": attempt,
            "entrypoint": "main.py",
            "archive_sha256": firewall.sha256_file(archive),
            "files": [row],
            "candidate_sha256": candidate_sha,
        }
        write_json(self.output / "submission_manifest.json", manifest)
        write_json(
            self.output / "package_qa_report.json",
            {
                "schema": firewall.QA_SCHEMA,
                "attempt_id": attempt,
                "candidate_sha256": candidate_sha,
                "syntax_checked": True,
                "callable_loader_passed": True,
                "self_play_smoke_passed": True,
                "generator_claim_only": True,
            },
        )
        attestation = {
            "schema": firewall.ATTESTATION_SCHEMA,
            "attempt_id": attempt,
            "policy_sha256": self.input_seal["policy_sha256"],
            "input_seal_sha256": self.input_seal["seal_sha256"],
            "fork_turns": "none",
            "history_inherited": False,
            "network_accessed": False,
            "filesystem_discovery_used": False,
            "shell_discovery_used": False,
            "outside_allowlist_read": False,
            "individual_games_read": False,
            "replays_or_episodes_read": False,
            "opponent_actions_read": False,
            "historical_model_source_or_design_read": False,
            "model_pool_identity_mapping_read": False,
            "all_reads_declared": True,
        }
        write_json(self.output / "generation_attestation.json", attestation)
        (self.output / "strategy_note.md").write_text(note, encoding="utf-8")
        rule_row = self.input_seal["read_classes"]["official_rules"]["files"][0]
        events = [
            {
                "schema": firewall.LOG_SCHEMA, "seq": 1, "event": "session_start",
                "attempt_id": attempt, "policy_sha256": self.input_seal["policy_sha256"],
                "input_seal_sha256": self.input_seal["seal_sha256"], "fork_turns": "none",
                "history_inherited": False,
            },
            {
                "schema": firewall.LOG_SCHEMA, "seq": 2, "event": "read",
                "class": "official_rules", "path": rule_row["path"], "sha256": rule_row["sha256"],
            },
            {
                "schema": firewall.LOG_SCHEMA, "seq": 3, "event": "write",
                "class": "generator_output", "path": "main.py", "sha256": row["sha256"],
            },
            {
                "schema": firewall.LOG_SCHEMA, "seq": 4, "event": "candidate_sealed",
                "candidate_sha256": candidate_sha,
            },
            {
                "schema": firewall.LOG_SCHEMA, "seq": 5, "event": "session_end",
                "all_reads_declared": True,
            },
        ]
        (self.output / "generation_log.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in events), encoding="utf-8"
        )
        return candidate_sha

    def test_clean_candidate_passes_and_mutation_fails(self) -> None:
        candidate_sha = self.make_candidate()
        candidate_seal_path = self.private / "candidate_seal.json"
        seal = firewall.audit_candidate(self.output, self.input_seal_path, None, candidate_seal_path)
        self.assertTrue(seal["passed"])
        self.assertEqual(seal["candidate_sha256"], candidate_sha)
        firewall.verify_candidate_seal(self.output, candidate_seal_path)
        (self.output / "strategy_note.md").write_text("mutated\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after seal"):
            firewall.verify_candidate_seal(self.output, candidate_seal_path)

    def test_each_sealed_input_class_mutation_is_rejected(self) -> None:
        self.make_candidate()
        mutations = (
            ("official_rules", self.rules / "official.txt", b"mutated official rules\n", b"official game rules\n"),
            ("own_prior_work", self.prior / "added.txt", b"late prior work\n", None),
            ("score_feedback", self.feedback / "added.json", b"{}\n", None),
        )
        for class_name, path, changed, original in mutations:
            with self.subTest(class_name=class_name):
                path.write_bytes(changed)
                with self.assertRaisesRegex(
                    ValueError, f"sealed input closure changed: {class_name}"
                ):
                    firewall.audit_candidate(
                        self.output,
                        self.input_seal_path,
                        None,
                        self.private / f"candidate_seal_{class_name}.json",
                    )
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)

    def test_import_is_rejected(self) -> None:
        self.make_candidate("import os\ndef agent(observation, configuration):\n    return []\n")
        with self.assertRaisesRegex(ValueError, "import_forbidden"):
            firewall.audit_candidate(self.output, self.input_seal_path, None, self.private / "candidate_seal.json")

    def test_introspection_escape_is_rejected(self) -> None:
        self.make_candidate("def agent(observation, configuration):\n    return getattr(observation, '__class__')\n")
        with self.assertRaisesRegex(ValueError, "runtime_escape"):
            firewall.audit_candidate(self.output, self.input_seal_path, None, self.private / "candidate_seal.json")

    def test_private_identity_leak_is_hashed_and_rejected(self) -> None:
        self.make_candidate(note="secret opponent design\n")
        denylist = self.private / "denylist.json"
        write_json(denylist, {"schema": firewall.DENYLIST_SCHEMA, "terms": [{"category": "opponent_identity", "value": "secret opponent"}]})
        with self.assertRaises(ValueError) as caught:
            firewall.audit_candidate(self.output, self.input_seal_path, denylist, self.private / "candidate_seal.json")
        message = str(caught.exception)
        self.assertIn(firewall.sha256_bytes("secret opponent".encode()), message)
        self.assertNotIn("secret opponent design", message)

    def test_feedback_reducer_reconstructs_fixed_public_schema(self) -> None:
        private_result = self.private / "result.json"
        write_json(
            private_result,
            {
                "schema": firewall.PRIVATE_RESULT_SCHEMA,
                "attempt_id": "attempt_001",
                "candidate_sha256": "a" * 64,
                "integrity_passed": True,
                "anchors": {
                    "primary": {"games": 200, "pure_win_rate": 0.70},
                    "secondary": {"games": 200, "pure_win_rate": 0.66},
                },
                "pool": {"lineage_equal_score_rate": 0.68, "source_cluster_ci95_low": 0.61},
                "parent": {"paired_uplift_rate": 0.15, "paired_uplift_ci95_low": 0.11},
                "private_details": {"opponent_name": "must not cross", "game_ids": [1, 2]},
            },
        )
        public_path = self.root / "public_feedback.json"
        public = firewall.reduce_feedback(private_result, public_path)
        self.assertTrue(public["overall_passed"])
        self.assertEqual(set(public), firewall.PUBLIC_FEEDBACK_KEYS)
        self.assertNotIn("opponent", public_path.read_text(encoding="utf-8"))
        firewall.validate_public_feedback(public)

    def test_hidden_panel_reservation_and_completion_are_single_use(self) -> None:
        panel = self.private / "panel.json"
        seal = self.private / "candidate.json"
        evaluator = self.private / "evaluator.py"
        result = self.private / "hidden_result.json"
        for path in (panel, seal, evaluator, result):
            path.write_text(path.name, encoding="utf-8")
        locks = self.private / "locks"
        firewall.reserve_hidden(locks, panel, seal, evaluator)
        with self.assertRaises(FileExistsError):
            firewall.reserve_hidden(locks, panel, seal, evaluator)
        firewall.complete_hidden(locks, result)
        with self.assertRaises(FileExistsError):
            firewall.complete_hidden(locks, result)

    def test_input_symlink_is_rejected(self) -> None:
        other = self.root / "other.txt"
        other.write_text("outside", encoding="utf-8")
        linked_rules = self.root / "linked_rules"
        linked_prior = self.root / "linked_prior"
        linked_feedback = self.root / "linked_feedback"
        linked_output = self.root / "linked_output"
        for path in (linked_rules, linked_prior, linked_feedback, linked_output):
            path.mkdir()
        (linked_rules / "leak").symlink_to(other)
        with self.assertRaisesRegex(ValueError, "non-regular|symlink"):
            firewall.seal_inputs(linked_rules, linked_prior, linked_feedback, linked_output, self.private / "bad_seal.json")


if __name__ == "__main__":
    unittest.main()
