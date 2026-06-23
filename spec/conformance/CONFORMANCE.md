# Conformance Contract

A v0.1-conformant runner is an implementation that accepts:

```bash
<runner> --envelope path/to/envelope.barrier.json
```

and emits exactly one JSON verdict record on stdout.

## Required Behavior

A conformant runner must:

- pass every top-level fixture in `spec/conformance/fixtures`;
- match each fixture's `expected_verdict`;
- match each fixture's `expected_reason_code`;
- emit a deterministic `record_core_sha256` when run twice on the same fixture;
- use only reason codes from `spec/verdict-semantics.md`;
- never produce `CERTIFIED` for artifact tamper, path rejection, rung laundering,
  unknown checkers, manifest hash mismatch, malformed timeout, or illegal plugin
  verdict/rung output;
- never count duplicated checker hashes as independent quorum members, while still
  allowing a quorum when enough distinct certifying hashes are present;
- never certify when a checker requires a real sandbox profile that is unavailable.

The harness is implementation-independent:

```bash
python3 spec/conformance/run_conformance.py --runner "<runner command>"
```

## Build-Your-Own Runner Checklist

1. Parse the envelope.
2. Verify `artifacts[].path` containment and `sha256` before dispatch.
3. Enforce runner-owned rung ceilings before trusting a checker.
4. Dispatch the checker.
5. Validate checker output against the verdict vocabulary.
6. Refuse rung laundering and min-trust violations.
7. Enforce quorum threshold and hash-distinct counted members for `quorum`.
8. Record the plugin sandbox profile and refuse unavailable required profiles.
9. Emit a verdict record whose structured core hash is deterministic.

## Non-Guarantees

Conformance does not prove a runner is formally verified. It does not prove a
hash-pinned plugin is honest on a structurally valid envelope. It does not prove
hash-distinct quorum members are semantically independent. The portable
`env-restricted` profile is not a real OS sandbox. It is an executable spec seed:
strong enough to criticize, extend, and compare implementations, but not a broad
certification standard.
