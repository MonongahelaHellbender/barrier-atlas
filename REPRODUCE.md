# Reproduce

Barrier Atlas runners are designed to run on a clean Python 3.12+ checkout with
no runtime dependencies beyond the standard library. The Phase E signing and
ledger tests are post-run attestation checks and require `cryptography`.

## Local

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements-signing.txt
sh tools/reproduce.sh
```

This runs:

- toolchain-lock audit;
- Python syntax checks;
- spec validation;
- conformance fixtures;
- signed verdict / ledger / in-toto attestation probes;
- deterministic invariant fuzzing;
- one-directional safety tests;
- full atlas re-check.

## Docker

```bash
docker build -t barrier-atlas-repro .
docker run --rm barrier-atlas-repro
```

The Docker path reproduces the same bare-runner guarantees as GitHub Actions. In
that environment the Lean-dependent `lratcheck` and `lean-axioms` barriers may
honestly report `UNVERIFIABLE-HERE`; they must not report `REFUSED`.
The image installs `requirements-signing.txt` only for the post-run attestation
tools; the runner code remains stdlib-only.

## Optional External Tooling

`tools/TOOLCHAIN.lock` records the expected Python floor and optional external
checker identity. If `LRATCHECK_BIN` is set, or if the sibling
`lean-verification-journey` binary exists at the default path, `tools/toolchain_check.py`
checks its SHA-256 against the lock. If the binary is absent, the atlas degrades
to `UNVERIFIABLE-HERE` for those barriers rather than certifying.
