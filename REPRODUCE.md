# Reproduce

Barrier Atlas is designed to run on a clean Python 3.12+ checkout with no runtime
dependencies beyond the standard library.

## Local

```bash
sh tools/reproduce.sh
```

This runs:

- toolchain-lock audit;
- Python syntax checks;
- spec validation;
- conformance fixtures;
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

## Optional External Tooling

`tools/TOOLCHAIN.lock` records the expected Python floor and optional external
checker identity. If `LRATCHECK_BIN` is set, or if the sibling
`lean-verification-journey` binary exists at the default path, `tools/toolchain_check.py`
checks its SHA-256 against the lock. If the binary is absent, the atlas degrades
to `UNVERIFIABLE-HERE` for those barriers rather than certifying.
