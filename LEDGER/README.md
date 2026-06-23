# Barrier Atlas Ledger

`tools/atlas_log.py` maintains an append-only Merkle ledger of signed verdict
records. Generated ledger state lives here when a release chooses to publish
attested verdicts:

- `entries.jsonl` - append-only signed verdict entries;
- `checkpoint.json` - signed tree size and Merkle root;
- `proofs/*.proof.json` - inclusion proofs for logged records.

No private signing key belongs in this repository. A committed checkpoint is a
public witness: Git and GitHub make later history rewrites visible, but this is
not a Rekor service and does not prove the signing key was well governed.
