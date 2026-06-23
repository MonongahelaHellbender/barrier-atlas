# Threat Model

v0.1 makes the runner the small trusted base. Checkers can supply evidence verdicts, but the runner owns artifact binding, verdict vocabulary, rung ceilings, min-trust composition, and final verdict records.

| adversary controls | v0.1 guarantee | result |
|---|---|---|
| Artifact bytes | Hash mismatch is detected before checker execution. | `REFUSED` |
| Artifact path | Absolute paths, traversal, private machine paths, and symlink escapes are rejected for `artifacts[].path`. | `REFUSED` |
| Checker output | Non-JSON, illegal verdicts, or process failure cannot certify. | `UNVERIFIABLE-HERE` |
| Buggy or malicious checker returns `CERTIFIED` | Runner still enforces artifact hashes and rung rules. | `REFUSED` where structure fails |
| Envelope declares a stronger composed rung than earned | Min-trust calculation rejects it. | `REFUSED` |
| Atomic barrier declares a stronger rung than its checker can earn | Runner-owned checker ceiling rejects it. | `REFUSED` |
| Toolchain absent | No certification is minted. | `UNVERIFIABLE-HERE` |
| Non-human review says an empirical answer is adequate | Non-human review can screen only, never certify correctness. | `DEFERRED` |
| Named human verdict | Attributable and auditable, not mechanically verified. | Human trust base is explicit |

Non-guarantees:

- v0.1 is not a sandbox.
- v0.1 does not prove empirical claims true.
- v0.1 does not verify human expertise.
- v0.1 does not fetch or authenticate remote artifacts.
- v0.1 does not make broad AI-system safety claims.
