#!/usr/bin/env python3
"""Small plugin sandbox abstraction for Barrier Atlas v0.1.

The portable default is an environment-restricted subprocess with cwd set to the
staging directory. A real OS sandbox is intentionally not silently assumed:
envelopes that require one fail closed unless such a profile is explicitly
available in this environment.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ENV_RESTRICTED = "env-restricted"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SandboxProfile:
    profile: str
    required: bool
    available: bool

    def record(self) -> dict:
        return {"profile": self.profile, "required": self.required}


def choose_profile(require_real: bool = False) -> SandboxProfile:
    """Select the best available sandbox profile.

    `env-restricted` is always available and records a weaker, portable profile:
    the plugin runs from the staged directory with a scrubbed environment. It is
    not treated as a real OS sandbox. A future bwrap/nsjail profile can replace
    this without changing the runner contract.
    """
    if require_real:
        return SandboxProfile(UNAVAILABLE, True, False)
    return SandboxProfile(ENV_RESTRICTED, False, True)


def _minimal_env() -> dict[str, str]:
    path_parts = [
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]
    current_python = shutil.which("python3")
    if current_python:
        current_python_dir = str(Path(current_python).parent)
        if current_python_dir not in path_parts:
            path_parts.insert(0, current_python_dir)
    return {
        "PATH": os.pathsep.join(path_parts),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
    }


def run(
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
    profile: SandboxProfile,
) -> subprocess.CompletedProcess[str]:
    if not profile.available:
        raise RuntimeError("sandbox profile is unavailable")
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=_minimal_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
