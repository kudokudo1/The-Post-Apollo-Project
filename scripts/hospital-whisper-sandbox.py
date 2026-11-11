#!/usr/bin/env python3
"""Fail-closed Linux resource guard for each Hospital live Whisper inference.

This is the *child process*, not a preexec_fn in the threaded recorder.
Limits survive exec into bash and whisper-cli. A separate session owned by
hospital-live-dictation.py allows group termination at STOP/CANCEL/timeouts.
No network calls, persistent data, cgroup/system configuration or privileges.
"""
from __future__ import annotations

import os
import resource
import sys

# Conservative incident defaults for local tiny/base.en models. This is
# virtual-address space (not an exact RSS limit); fail closed if exceeded.
MAX_VIRTUAL_BYTES = 3 * 1024 * 1024 * 1024
MAX_CPU_SECONDS = 12
MAX_CORES = 2
NICE_INCREMENT = 10


def clamp_limit(which: int, requested: int) -> None:
    soft, hard = resource.getrlimit(which)
    if soft != resource.RLIM_INFINITY:
        requested = min(requested, soft)
    if hard != resource.RLIM_INFINITY:
        requested = min(requested, hard)
    resource.setrlimit(which, (requested, requested))


def apply_limits() -> None:
    # Never run an unconfined model after a resource setup failure.
    if not sys.platform.startswith("linux"):
        raise RuntimeError("LOCAL LINUX SANDBOX UNAVAILABLE")
    clamp_limit(resource.RLIMIT_AS, MAX_VIRTUAL_BYTES)
    clamp_limit(resource.RLIMIT_CPU, MAX_CPU_SECONDS)
    clamp_limit(resource.RLIMIT_CORE, 0)
    os.nice(NICE_INCREMENT)
    # Limit actual compute to two of the already allowed CPUs. This does not
    # steal or change the user's system-wide affinity / scheduling settings.
    allowed = sorted(os.sched_getaffinity(0))
    if not allowed:
        raise RuntimeError("NO ALLOWED CPUs")
    os.sched_setaffinity(0, set(allowed[:MAX_CORES]))


def main() -> int:
    if len(sys.argv) != 3:
        return 64
    helper, wav_file = sys.argv[1:3]
    if not os.path.isfile(helper) or not os.path.isfile(wav_file):
        return 66
    try:
        apply_limits()
        # The shared helper only adds CPU-only + 2-thread Whisper options when
        # explicitly run inside this resource guard; old single-clip calls
        # retain their existing command-line behavior.
        env = os.environ.copy()
        env["POST_APOLLO_STT_SAFE_MODE"] = "1"
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                     "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
            env[name] = "2"
        os.execve("/bin/bash", ["bash", helper, wav_file], env)
    except (OSError, ValueError, RuntimeError) as exc:
        print("LOCAL WHISPER SAFETY GUARD FAILED: "
              + exc.__class__.__name__, file=sys.stderr, flush=True)
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
