# V15 generator artifact schema

The output root must contain exactly these seven regular files:

1. `main.py`
2. `submission.tar.gz`
3. `submission_manifest.json`
4. `package_qa_report.json`
5. `generation_attestation.json`
6. `generation_log.jsonl`
7. `strategy_note.md`

There is no separate `candidate_manifest.json`.

## Submission manifest

```json
{
  "schema": "kaggriculture-v15-submission-manifest-1",
  "attempt_id": "attempt_001",
  "entrypoint": "main.py",
  "archive_sha256": "<64 lowercase hex>",
  "files": [{"path": "main.py", "sha256": "<64 lowercase hex>", "size_bytes": 0}],
  "candidate_sha256": "<SHA-256 of canonical compact JSON for the files array>"
}
```

The gzip/tar archive must contain only `main.py`. Its tar member must have mtime,
uid, and gid equal to zero; empty uname/gname; mode `0644`; and identical bytes to
the output `main.py`.

## Package QA claim

```json
{
  "schema": "kaggriculture-v15-package-qa-1",
  "attempt_id": "attempt_001",
  "candidate_sha256": "<same value as the manifest>",
  "syntax_checked": true,
  "callable_loader_passed": true,
  "self_play_smoke_passed": true,
  "generator_claim_only": true
}
```

## Attestation

```json
{
  "schema": "kaggriculture-v15-generator-attestation-1",
  "attempt_id": "attempt_001",
  "policy_sha256": "<launch value>",
  "input_seal_sha256": "<launch value>",
  "fork_turns": "none",
  "history_inherited": false,
  "network_accessed": false,
  "filesystem_discovery_used": false,
  "shell_discovery_used": false,
  "outside_allowlist_read": false,
  "individual_games_read": false,
  "replays_or_episodes_read": false,
  "opponent_actions_read": false,
  "historical_model_source_or_design_read": false,
  "model_pool_identity_mapping_read": false,
  "all_reads_declared": true
}
```

## Structured generation log

Each JSONL row has schema `kaggriculture-v15-generation-log-event-1` and a
contiguous integer `seq` starting at 1. Free-text fields are forbidden. Valid rows:

- Session start (must be first): `schema, seq, event="session_start", attempt_id,
  policy_sha256, input_seal_sha256, fork_turns="none", history_inherited=false`.
- Declared input read: `schema, seq, event="read", class, path, sha256`. Class is one
  of `official_rules`, `own_prior_work`, `score_feedback`, or `generator_output`.
- Output write: `schema, seq, event="write", class="generator_output", path,
  sha256`. Do not log the final log file itself because a self-hash is impossible.
- Candidate sealed: `schema, seq, event="candidate_sealed", candidate_sha256`.
- Session end (must be last): `schema, seq, event="session_end",
  all_reads_declared=true`.

At minimum, declare every official-rules file actually read, the `main.py` write,
the candidate-sealed event, and the session end. If a feedback file is present in
the sealed feedback root, it must be declared read.

`strategy_note.md` may contain only a first-principles description of the generated
policy. It must not mention private opponents, historical strategies, paths, seeds,
replays, or loss diagnostics.
