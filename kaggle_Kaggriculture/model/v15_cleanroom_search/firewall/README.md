# V15 clean-room firewall

This directory defines an auditable information firewall between the strategy
generator and the private evaluator. It does **not** claim OS-level isolation. All
agents share a filesystem, so an agent that deliberately ignores its instructions
can still read other project files. For a security boundary, run the generator as a
separate OS user/container/VM containing only the sealed inputs. Within the current
shared workspace, this is the strongest practical, fail-closed protocol.

## Boundary and roles

The orchestrator creates one dedicated generator with `fork_turns="none"`. The
generator may see only:

1. a curated copy of official rules;
2. its own prior work;
3. a score-only feedback file;
4. its fresh output directory.

The evaluator alone may see model identities, model code, replays, individual game
rows, seeds/sources, opponent actions, margins, failure modes, and hidden-panel
contents. Evaluator-private paths must never be placed below a generator allowlist
root. The evaluator reducer emits a new fixed-schema feedback object rather than
redacting a private report in place.

The same dedicated generator can revise its own strategy after receiving sanitized
aggregate scores. If it is replaced, the replacement must again use
`fork_turns="none"` and may inherit only a sealed copy of the prior generator's own
workspace—not the parent conversation.

## Required sequence

1. Copy official rules into a clean directory. Copy only generator-authored prior
   work into a separate directory. Put at most one validated public feedback JSON in
   a third directory. Create an empty output directory.
2. Run `seal-inputs`. It rejects overlapping roots, links, mutable permissions,
   non-regular files, and a non-empty output directory, then hashes the complete
   input closure.
3. Spawn the generator with `fork_turns="none"`, the prompt template, the four exact
   roots, the policy hash, and the input-seal hash. Do not give it the repository
   root or a broad working directory. Shell discovery, Git inspection, and network
   access are prohibited.
4. The generator writes the single-file runtime plus its deterministic package and
   audit records: `main.py`, `submission.tar.gz`, `submission_manifest.json`,
   `package_qa_report.json`, `generation_attestation.json`,
   `generation_log.jsonl`, and `strategy_note.md`.
   The archive itself contains exactly `main.py`; therefore the no-import rule and
   the clean-room packaging contract are both satisfied.
5. The evaluator runs `audit-candidate` with an evaluator-private denylist. Before
   reading candidate files, it recomputes every file row and closure hash in all
   three sealed read roots and rechecks the input-seal and policy hashes; any input
   addition, removal, or byte change fails closed. The scanner then rejects imports,
   dynamic code, runtime I/O, introspection escapes, symlinks/hardlinks, extra files,
   malformed logs, undeclared reads, manifest/hash mismatches, and leaked denylist
   terms. Reports contain only hashed denylist hits.
6. Before every game process, the evaluator re-runs `verify-candidate-seal`; a hash
   mismatch aborts the evaluation. Full game data remains under an evaluator-private
   root.
7. The evaluator runs `reduce-feedback`. Only anonymous aggregate rates and gate
   decisions cross the boundary; individual results and identity mappings never do.
8. A finalist may consume the hidden panel once. `reserve-hidden` uses exclusive
   creation and treats reservation itself as consumption. A crash is not retryable.
   `complete-hidden` adds a separate immutable receipt; it never releases the lock.

## Public feedback contract

The generator receives exactly these rate fields:

- `anchor_1_pure_win_rate`
- `anchor_2_pure_win_rate`
- `pool_equal_lineage_score_rate`
- `pool_source_cluster_ci_lower`
- `parent_paired_uplift`
- `parent_paired_uplift_ci_lower`

Labels are anonymous and stable. The public object contains no W/T/L counts, names,
game IDs, seeds, source clusters, per-opponent rows, margins, timestamps, file paths,
or free text. A SHA-256 content seal binds it to the candidate, policy, and opaque
private-result receipt. SHA-256 gives integrity/auditability, not writer
authentication; use an evaluator-held signing key in a separate process if malicious
tampering is in scope.

## What the audit can and cannot prove

It proves that the declared inputs, candidate closure, structured log, attestation,
public feedback, and hidden-panel lock are mutually consistent at audit time. It
does not prove that the self-declared read log is complete, that an agent never read
another shared path, or that strategy ideas were not covertly communicated. Those
claims require OS isolation or independent process telemetry. Therefore any failed
attestation, undeclared access, scanner warning, mutated seal, or interrupted hidden
run is a permanent fail-closed rejection—not something to waive after seeing a
score.

## CLI sketch

```text
python firewall.py seal-inputs \
  --official-rules /clean/rules \
  --own-prior-work /clean/own_prior \
  --score-feedback /clean/feedback \
  --output-root /clean/output \
  --seal /evaluator_private/input_seal.json

python firewall.py audit-candidate \
  --output-root /clean/output \
  --input-seal /evaluator_private/input_seal.json \
  --denylist /evaluator_private/denylist.json \
  --seal /evaluator_private/candidate_seal.json

python firewall.py verify-candidate-seal \
  --output-root /clean/output \
  --seal /evaluator_private/candidate_seal.json
```

Run the tests without executing any games:

```text
python -m unittest discover -s tests -v
```
