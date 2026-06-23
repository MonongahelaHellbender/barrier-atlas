# Checker Plugin Contract

External plugins are hash-pinned executables. They propose evidence verdicts; the
runner still owns artifact binding, checker identity, rung discipline, and the
final verdict record.

## Manifest

```json
{
  "name": "barrier-atlas-rup",
  "version": "0.1",
  "kind": "external-rup",
  "command": ["python3", "tools/checkers/rup_plugin.py"],
  "entrypoint": "tools/checkers/rup_plugin.py",
  "sha256": "<sha256 of entrypoint>"
}
```

The runner computes the hash of `entrypoint` itself. A mismatch returns
`REFUSED / CHECKER_HASH_MISMATCH` before the plugin runs.

## Invocation

```bash
<command...> --envelope <staged_envelope.json> --artifacts-dir <dir>
```

The runner verifies and stages artifacts first. Each verified artifact is copied
to `<dir>/<artifact-id>`. The staged envelope removes original artifact paths, so
the plugin should read artifacts only from `--artifacts-dir` by id. The portable
profile runs with `cwd` set to the staging directory and a scrubbed environment,
and the verdict record names that profile as `env-restricted`.

## Output

The plugin writes exactly one JSON object on stdout:

```json
{
  "verdict": "CERTIFIED|REFUSED|DEFERRED|UNVERIFIABLE-HERE",
  "detail": "human-readable reason",
  "rung": "R0|R1|R2|R3|R4|R5",
  "checker": { "name": "...", "version": "..." }
}
```

Exit code `0` means a verdict was produced, including `REFUSED`. Nonzero exit,
timeout, invalid JSON, illegal verdict, illegal rung, or unavailable required
sandbox becomes `UNVERIFIABLE-HERE`, never `CERTIFIED`.

## Sandbox Profile

An envelope may set `"requires_sandbox": true` inside `checker`. In v0.1's
portable profile, a required real sandbox is unavailable and the runner emits
`UNVERIFIABLE-HERE / SANDBOX_UNAVAILABLE`. Ordinary plugin runs use
`env-restricted`: cwd is the staging directory, the environment is scrubbed, and
the record says so. This is not a real OS sandbox.

## Boundary

A hash-pinned plugin is trusted for its evidence verdict at its rung. The runner
does not re-derive that evidence. A known malicious plugin can still claim
`CERTIFIED` on a structurally valid envelope; the controls are identity, artifact
binding, rung ceilings, sandbox-profile transparency, and quorum discipline, not
proof of plugin honesty.
