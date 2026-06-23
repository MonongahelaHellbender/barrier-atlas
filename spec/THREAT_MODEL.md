# Threat Model

v0.1 makes the runner the small trusted base. Checkers can supply evidence verdicts, but the runner owns artifact binding, verdict vocabulary, rung ceilings, min-trust composition, and final verdict records.

| adversary controls | v0.1 guarantee | result |
|---|---|---|
| Artifact bytes | Hash mismatch is detected before checker execution. | `REFUSED` |
| Artifact path | Absolute paths, traversal, private machine paths, and symlink escapes are rejected for `artifacts[].path`. | `REFUSED` |
| Checker output | Non-JSON, illegal verdicts, or process failure cannot certify. | `UNVERIFIABLE-HERE` |
| External checker manifest | Missing or malformed manifests cannot dispatch. | `REFUSED` |
| External checker identity | Entrypoint hash mismatch is detected before execution. | `REFUSED` |
| External checker timeout | Timeout cannot certify. | `UNVERIFIABLE-HERE` |
| Malformed checker configuration | Bad timeout values emit one fail-closed record rather than crashing or normalizing to certification. | `UNVERIFIABLE-HERE` |
| Required real sandbox unavailable | The runner refuses to dispatch instead of silently using a weaker profile. | `UNVERIFIABLE-HERE` |
| Quorum member fails or lies | Failed members do not count toward the quorum threshold. | `REFUSED` |
| Quorum clone / duplicate checker hash | Counted members must have distinct entrypoint hashes; duplicate extras do not poison a quorum already met by distinct hashes. | `REFUSED` when distinct threshold is not met |
| Buggy or malicious checker returns `CERTIFIED` | Runner still enforces artifact hashes and rung rules. | `REFUSED` where structure fails |
| Hash-pinned malicious checker on a valid envelope | Runner cannot re-derive the evidence; identity and rung ceiling are the controls. | May propose `CERTIFIED` at its rung |
| Envelope declares a stronger composed rung than earned | Min-trust calculation rejects it. | `REFUSED` |
| Atomic barrier declares a stronger rung than its checker can earn | Runner-owned checker ceiling rejects it. | `REFUSED` |
| Toolchain absent | No certification is minted. | `UNVERIFIABLE-HERE` |
| Non-human review says an empirical answer is adequate | Non-human review can screen only, never certify correctness. | `DEFERRED` |
| Named human verdict | Attributable and auditable, not mechanically verified. | Human trust base is explicit |
| Verdict record tamper after signing | Recomputed `record_core_sha256` or Ed25519 verification fails. | `RECORD_CORE_MISMATCH` / `SIGNATURE_INVALID` |
| Past ledger entry tamper | Recomputed Merkle root no longer matches the signed checkpoint. | `LOG_ROOT_MISMATCH` |
| Never-logged record claims inclusion | Missing or mismatched inclusion proof fails verification. | `LOG_INCLUSION_MISSING` |

Trusted-base additions in Phase D:

- `tools/sandbox.py` is trusted to apply the recorded process profile. The portable
  `env-restricted` profile scrubs environment and cwd but is not a real OS sandbox.
- Quorum independence is asserted by distinct entrypoint hashes and member metadata;
  it is not proof of semantic independence.

Trusted-base additions in Phase E:

- The Ed25519 private key is trusted to represent the signer. The code can verify
  key possession, not whether the key was governed well.
- `tools/atlas_log.py` is trusted to compute the Merkle tree and checkpoint. GitHub
  witnessing means committed history rewrites are visible; it is not a Rekor-style
  public transparency service.

Non-guarantees:

- v0.1's portable profile is not a real OS sandbox.
- v0.1 does not prove a hash-pinned plugin is honest.
- v0.1 does not prove hash-distinct quorum members are semantically independent.
- v0.1 does not prove empirical claims true.
- v0.1 does not verify human expertise.
- v0.1 does not fetch or authenticate remote artifacts.
- v0.1 does not make broad AI-system safety claims.
- v0.1 does not provide key custody, revocation, timestamp authority, or Sigstore
  identity binding.

Phase C added no runtime trusted base. Phase D's composite-aware fuzzer now samples
composed, multi-region, and quorum cases, shrinking the coverage residual. It is
still a fuzzer, not a proof of the runner.
