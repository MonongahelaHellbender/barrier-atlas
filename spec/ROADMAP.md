# Spec Roadmap

v0.1 deliberately stops at the small, reviewable runner/envelope/conformance core.

Implemented seed layers:

- Ed25519 detached signatures over verdict-record cores;
- a git-witnessed Merkle checkpoint ledger;
- in-toto style pipeline attestation mapping;

Next layers, not implemented here:

- role-based human sign-off;
- remote artifact resolution;
- real OS sandboxing for plugin execution;
- Sigstore/Rekor-backed transparency and keyless identity;
- translations to other high-assurance domains.

The translation target remains bounded assurance claims: explicit artifacts, explicit trust base, and fail-closed gates.
