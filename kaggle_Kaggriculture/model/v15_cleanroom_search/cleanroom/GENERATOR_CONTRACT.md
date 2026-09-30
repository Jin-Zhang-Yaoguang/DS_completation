# V15 Clean-room Strategy Generator Contract

## Objective

Create a new Kaggriculture agent from the official game rules and environment API only.
The candidate is evaluated by an opaque service.  The generator must not inspect any
historical agent, replay, loss trace, opponent action, model-pool identity, or evaluator
implementation.

The incumbent parent is an opaque policy named `P0`.  Its source and construction are
not available to the generator.  The candidate must be independently implemented and
must not import or wrap `P0`.

## Allowed inputs

The generator may read only files that the orchestrator has copied into the three
sealed read roots (`official_rules`, `own_prior_work`, and `score_feedback`), plus
its fresh `generator_output` root. In particular:

1. A curated copy of this contract and its score schema.
2. A sealed copy of its own earlier attempt files, if any.
3. Curated copies of these official Kaggriculture environment files:
   - `.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/README.md`
   - `.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py`
   - `.venv/lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.json`
4. A curated copy of `kaggle_Kaggriculture/playground/game_rules.html`.
5. The current attempt's score-only feedback JSON after evaluation.
6. Curated documentation copied into `official_rules` before its closure is sealed.

The source repository, installed-package directories, parent conversation, and broad
working directory are not allowlisted even when they contain one of the source files
named above.

The generator may run syntax tests, raw-loader tests, and self-play using only policies
created inside the current attempt directory.  It may not run or inspect opaque anchors
or model-pool policies.

## Forbidden inputs and actions

The generator must not read, search, import, copy, summarize, or infer from:

- any path below `kaggle_Kaggriculture/model/` outside this V15 clean-room candidate
  attempt and this contract;
- `kaggle_Kaggriculture/model_data/`, downloaded Episodes, Replay, logs, community
  research, experiment reports, leaderboards, or prior candidate diagnostics;
- the V15 evaluator, model registry, hidden panel, lineage map, task list, raw game rows,
  model identifiers, or opponent-specific metrics;
- Git history or filesystem-wide searches intended to discover historical strategies;
- web/forum strategy discussions or any other model's source code.

Candidate code must be a single self-contained file and must not contain any import,
absolute path, runtime file/process/network access, dynamic execution/introspection,
or reference to forbidden paths and model IDs.

## Score-only feedback

The evaluator may return only the fields defined by `score_only_feedback.schema.json`:

- aggregate direct-anchor win rates;
- lineage-equal pool score rate and its source-cluster confidence lower bound;
- candidate-versus-parent paired uplift and its confidence lower bound;
- aggregate integrity status and overall pass/fail.

It must not return per-game rows, seed IDs, opponent names, lineage identities, margins,
actions, states, trigger counts, failure examples, or explanations of how the candidate
lost.

## Candidate deliverables

Each attempt must contain:

- `main.py` with the final top-level callable named `agent`;
- `submission.tar.gz`, containing exactly `main.py`, and
  `submission_manifest.json` with deterministic member hashes;
- `package_qa_report.json`, explicitly marked as a generator claim until the private
  evaluator repeats package QA;
- `generation_attestation.json` listing every file intentionally read and affirming that
  the forbidden-input boundary was respected;
- `generation_log.jsonl` using the firewall's fixed, free-text-free event schema;
- `strategy_note.md` explaining the policy from first principles without mentioning any
  historical model or feedback beyond the allowed scalar fields.

The evaluation service, not the generator, decides whether an attempt advances.
