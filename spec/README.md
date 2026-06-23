# Barrier Atlas Spec v0.1

A refusal-first certification envelope for bounded scientific and AI-assurance claims.

The spec separates claims, artifacts, checker behavior, trust rungs, and final verdicts. The runner is the small trusted base: it binds artifacts by hash, rejects path escapes, enforces rung ceilings and min-trust composition, and emits a reproducible verdict record.

v0.1 also supports hash-pinned external checker plugins and quorum claims. Plugins
propose verdicts; the runner still owns artifact binding, checker identity, sandbox
profile recording, rung discipline, quorum thresholds, and the final verdict.

## Run

```bash
python3 spec/validate.py
python3 spec/conformance/run_conformance.py --runner "python3 tools/plugin_runner.py"
python3 tests/test_invariant_fuzz.py
```

## Pieces

- `envelope-v0.1.schema.json` describes the envelope shape.
- `verdict-semantics.md` defines verdicts and reason codes.
- `THREAT_MODEL.md` names what the runner does and does not defend.
- `DESIGN_CLAIMS_AND_LIMITS.md` states what v0.1 earns, trusts, and does not claim.
- `runner-contract.md` defines the runner CLI and verdict record.
- `checker-plugin-contract.md` defines the external plugin contract.
- `conformance/` is the executable spec seed.
- `conformance/CONFORMANCE.md` defines implementation-independent runner conformance.

## AI-Assurance Interpretation

| atlas concept | AI-assurance interpretation |
|---|---|
| artifact | model, eval transcript, dataset slice, proof/certificate, policy artifact |
| claim scope | bounded safety or evaluation claim |
| rung | declared assurance level and trusted base |
| refusal | gate failure, not product failure |
| deferred | awaiting human or higher-rung review |
| named human verdict | attributable assessor judgment |

## What This Is Not

v0.1 is not a broad standard, not a guarantee about AI-system safety, not a security-product credential, and not a production certification system. The portable plugin profile is `env-restricted`, not a real OS sandbox: running an external plugin still executes code on the host. It is a small runner/envelope/conformance seed that makes bounded claims more inspectable and easier to refuse honestly.
