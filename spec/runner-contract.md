# Runner Contract

The v0.1 runner consumes one barrier envelope and emits one JSON verdict record.

```bash
<runner-command> --envelope path/to/barrier.json
```

The plugin-capable reference implementation is:

```bash
python3 tools/plugin_runner.py --envelope path/to/barrier.json
```

The Phase A in-process reference runner remains available as:

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

## Post-Run Attestation

The runner does not sign records itself. Phase E tools can sign the canonical
`record_core` after the run:

```bash
python3 tools/sign_record.py --record record.json --private-key signing-private.pem --out record.sig.json
python3 tools/verify_record.py --record record.json --signature record.sig.json --public-key signing-public.pem
```

`tools/atlas_log.py` can append a signed record to a Merkle ledger and write a
signed checkpoint. `tools/to_intoto.py` converts a verdict record into an in-toto
Statement shape. These are authenticity and witness layers over the record; they
do not alter the runner verdict.

## External Plugin Dispatch

For envelopes that declare `checker.manifest`, the plugin-capable runner uses this
order:

1. Resolve and validate the manifest.
2. Compute the entrypoint hash and compare it with the manifest.
3. Verify artifact paths and hashes.
4. Enforce the declared rung against the checker-kind ceiling.
5. Stage only verified artifacts into a temporary artifact directory.
6. Run the plugin with a timeout.
7. Validate the plugin JSON verdict and returned rung.
8. Emit the final runner-owned verdict record.

The plugin may never upgrade a verdict. A `CERTIFIED` final verdict requires all
runner gates to pass and the plugin to return `CERTIFIED`.
