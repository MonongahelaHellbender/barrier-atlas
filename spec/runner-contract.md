# Runner Contract

The v0.1 runner consumes one barrier envelope and emits one JSON verdict record.

```bash
<runner-command> --envelope path/to/barrier.json
```

The reference implementation is:

```bash
python3 tools/spec_runner.py --envelope path/to/barrier.json
```

The runner owns:

- containment and hash checks for `artifacts[].path`;
- atomic checker rung ceilings;
- min-trust composition for `composed` and `multi-region`;
- verdict vocabulary validation;
- stable verdict record generation.

The runner ignores `expected_verdict` and `expected_reason_code`; those fields belong only to conformance fixtures.

`record_core_sha256` is computed from structured fields only: schema version, envelope id/hash, sorted artifact ids/hashes/verified bits, checker identity, raw checker verdict, final verdict, final rung, and reason code. It excludes `detail` and any timestamp so the core hash is reproducible across machines.
