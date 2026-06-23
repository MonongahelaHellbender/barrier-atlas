# Conformance Fixtures

The conformance suite is the executable v0.1 spec seed. It targets a runner command, not this repository's unit-test internals.

```bash
python3 spec/conformance/run_conformance.py --runner "python3 tools/plugin_runner.py"
```

Each top-level fixture declares `expected_verdict` and `expected_reason_code`. Sub-barriers used by composed fixtures live in this directory too, so the composed fixtures are self-contained.

| fixture | invariant |
|---|---|
| `01-valid-rup.barrier.json` | A hash-bound RUP certificate can certify at R3. |
| `02-tampered-artifact.barrier.json` | Hash mismatch refuses before checker execution. |
| `03-missing-artifact.barrier.json` | Missing artifact refuses distinctly from hash mismatch. |
| `04-llm-signoff.barrier.json` | Non-human review can screen but not certify. |
| `05-weak-answer.barrier.json` | Weak empirical answers refuse. |
| `06-rung-laundering.barrier.json` | A composed claim cannot declare a stronger rung than its weakest certified part. |
| `07-weak-subbarrier.barrier.json` | Deferred sub-barriers propagate as deferred composites. |
| `08-unknown-checker.barrier.json` | Unknown checker kinds are unverifiable here, not certified. |
| `09-atomic-rung-over-ceiling.barrier.json` | Atomic checker kinds cannot over-declare their rung. |
| `10-external-rup.barrier.json` | A hash-pinned external RUP plugin can certify a valid staged artifact. |
| `11-checker-hash-mismatch.barrier.json` | The runner refuses a manifest whose entrypoint hash does not match. |
| `12-liar-tampered-artifact.barrier.json` | A malicious plugin cannot certify a tampered artifact. |
| `13-liar-illegal-rung.barrier.json` | A malicious plugin cannot certify a stronger returned rung. |
| `14-malformed-timeout.barrier.json` | Malformed plugin timeout emits a fail-closed record and cannot certify. |
