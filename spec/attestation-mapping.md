# Attestation Mapping

Phase E adds post-run attestations for verdict records. The runner still emits a
plain JSON record; signing and logging are separate steps.

## Signed Payload

`tools/sign_record.py` signs the canonical `record_core` bytes, the same
structured payload whose SHA-256 is stored as `record_core_sha256`.

The detached signature object is:

```json
{
  "signature_version": "0.1",
  "alg": "ed25519",
  "record_core_sha256": "...",
  "sig": "...base64...",
  "key_id": "ed25519:...",
  "signed_at": "..."
}
```

`detail`, timestamps, and other explanatory free text are not part of
`record_core`. Changing a signed core field produces `RECORD_CORE_MISMATCH`;
using the wrong key produces `SIGNATURE_INVALID`.

## Transparency Ledger

`tools/atlas_log.py append` stores the signed record in a Merkle tree and writes:

- `LEDGER/entries.jsonl`;
- `LEDGER/checkpoint.json`;
- `LEDGER/proofs/<record_core_sha256>.proof.json`.

The checkpoint signs `{ tree_size, root_hash }`. Committing the checkpoint gives
a zero-infrastructure witness: Git and GitHub make history rewrites visible. The
limit is explicit: this is a git-witnessed log, not a globally distributed
transparency service.

## in-toto Shape

`tools/to_intoto.py` maps a verdict record to an in-toto Statement:

- `_type`: `https://in-toto.io/Statement/v1`;
- `subject`: one entry per verified artifact, with its SHA-256 digest;
- `predicateType`: `https://github.com/MonongahelaHellbender/barrier-atlas/spec/predicate/verdict/v0.1`;
- `predicate`: the `record_core` fields plus `record_core_sha256`.

A SLSA-aware consumer can read this as: "this runner emitted this verdict for
these artifact bytes under this checker identity and trust rung." It cannot infer
that the claim is universally true, that the signing key is institutionally
trusted, or that a plugin's semantics are honest beyond the rung and manifest
identity recorded by the runner.
