# Barrier Atlas Ledger

`tools/atlas_log.py` maintains an append-only Merkle ledger of signed verdict
records. Generated ledger state lives here when a release chooses to publish
attested verdicts:

- `entries.jsonl` - append-only signed verdict entries;
- `checkpoint.json` - signed tree size and Merkle root;
- `proofs/*.proof.json` - inclusion proofs for logged records.

Each append refreshes all proof files against the latest checkpoint, so an older
record remains verifiable after later records are appended. Duplicate
`record_core_sha256` entries are refused because proof filenames are keyed by
that digest.

No private signing key belongs in this repository. Phase E v0.1 verifies record
signatures and ledger checkpoints under the same Ed25519 public key; append
refuses a checkpoint key mismatch rather than writing an unverifiable ledger. A
committed checkpoint is a public witness: Git and GitHub make later history
rewrites visible, but this is not a Rekor service and does not prove the signing
key was well governed.
