# Mutation Survivor Policy

Phase C starts mutation testing as a non-blocking developer audit. The runtime
runner remains stdlib-only; mutation tooling is optional and must not be imported
by `tools/spec_runner.py` or `tools/plugin_runner.py`.

## Current Status

- Blocking CI guard: `python3 tests/test_invariant_fuzz.py` runs 2000 deterministic
  cases over artifact binding, path containment, rung ceilings, timeout parsing,
  manifest identity, plugin verdict/rung validation, arbitrary external plugin
  outputs, composed min-trust, multi-region min-trust, and quorum independence.
- Optional mutation command: `tools/run_mutation.sh`.
- Full mutmut scoring is not yet a required CI gate.

## Safety-Relevant Functions

Every survivor touching one of these functions must be killed by a regression
test or justified as equivalent:

- `tools/spec_runner.py`: `_resolve_artifact_path`, `_verify_artifacts`,
  `_stronger_than`, `_evaluate_composed`, `_evaluate_multi_region`, `evaluate`,
  `_record_core`, `make_record`.
- `tools/plugin_runner.py`: `_safe_repo_path`, `_load_manifest`,
  `_artifact_source_map`, `_stage_artifacts`, `_run_plugin`,
  `_evaluate_quorum`, `evaluate`, `_record_env`.
- `tools/sandbox.py`: `choose_profile`, `run`.

## Survivor Ledger

No safety-relevant survivor is accepted without a written justification here.

| date | tool | target | survivor | disposition |
|---|---|---|---|---|
| 2026-06-23 | deterministic invariant fuzzer | runner structural + composite gates | none observed in 2000-case Phase D run | blocking CI guard |
| 2026-06-23 | targeted fault injection | composed min-trust fuzzer coverage | Phase D atom pool used plugin-only `external-rup` atoms, so composed sub-barriers bailed as `UNKNOWN_CHECKER` before reaching min-trust | fixed by switching composed fuzz atoms to in-process `rup-python`; composed, multi-region, and quorum injected faults now all CAUGHT |
