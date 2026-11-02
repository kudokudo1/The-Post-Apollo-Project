#!/usr/bin/env python3
"""Disposable real-Quickshell Identity Organizations smoke, CI/explicit run.

This harness NEVER starts the user's default config or edits their XDG files.
It gives an isolated qs process its own HOME/cache/state/config/runtime roots,
launches ONLY the repo's unmounted IdentityNativeDisplaySmokeV0.qml and
supplies synthetic, token-free Organizations snapshots through a 0600 socket.

Requires qs in PATH and Qt offscreen platform support. Intended for a
disposable Linux CI container. No real identity, browser, network,
enterprise data, login, sudo, host restart or production session exists.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "identity"))

from private_context_ipc_v0 import PrivateContextSocket

SCHEMA = "post-apollo.identity.desktop-context-display.v0"
EXPECTED = {
    "ready": "IDENTITY_NATIVE_SMOKE_PASS_READY",
    "signed-out": "IDENTITY_NATIVE_SMOKE_PASS_SIGNED_OUT",
    "missing": "IDENTITY_NATIVE_SMOKE_PASS_MISSING",
    "revoke": "IDENTITY_NATIVE_SMOKE_PASS_REVOKE",
}


def synthetic(status: str) -> dict[str, object]:
    """All identifiers are plainly synthetic and all grant lists empty."""
    return {
        "schema": SCHEMA,
        "status": status,
        "organizations": ([
            {"organizationId": "synthetic_llc_a", "kind": "llc",
             "scopeGrants": []},
            {"organizationId": "synthetic_nonprofit", "kind": "nonprofit",
             "scopeGrants": []},
        ] if status == "READY" else []),
        "portfolios": ([
            {"portfolioId": "synthetic_portfolio",
             "organizationIds": ["synthetic_llc_a", "synthetic_nonprofit"]},
        ] if status == "READY" else []),
        "canSwitchOrganization": False,
    }


def run(scenario: str) -> None:
    if scenario not in EXPECTED:
        raise ValueError("Unknown synthetic-only smoke scenario")
    qs = shutil.which("qs")
    if qs is None:
        raise RuntimeError("quickshell/qs was not installed in disposable CI")
    root_config = ROOT / "IdentityNativeDisplaySmokeV0.qml"
    if not root_config.is_file():
        raise RuntimeError("Unmounted smoke root unavailable")

    with tempfile.TemporaryDirectory(prefix="id-native-v0-") as tmp:
        base = Path(tmp)
        # Every Quickshell write location points into the disposable test
        # directory. This is NOT the operator's XDG_RUNTIME_DIR.
        xdg = base / "runtime"
        xdg.mkdir(mode=0o700)
        directory = xdg / "post-apollo-identity-v0"
        directory.mkdir(mode=0o700)
        env = os.environ.copy()
        for key, sub in (
            ("HOME", "home"), ("XDG_CACHE_HOME", "cache"),
            ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state"),
            ("XDG_DATA_HOME", "data"),
        ):
            target = base / sub
            target.mkdir(mode=0o700)
            env[key] = str(target)
        env.update({
            "XDG_RUNTIME_DIR": str(xdg),
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "QS_DISABLE_FILE_WATCHER": "1",
            "POST_APOLLO_IDENTITY_NATIVE_SMOKE": "CI_DISPOSABLE_ONLY",
            "POST_APOLLO_IDENTITY_NATIVE_SCENARIO": scenario,
            # Never connect to an existing desktop/session compositor.
            "WAYLAND_DISPLAY": "",
            "DISPLAY": "",
            "QT_LOGGING_RULES": "qt.qpa.*=false",
        })

        calls = [0]

        def provider() -> dict[str, object]:
            calls[0] += 1
            status = ("SIGNED_OUT" if scenario == "signed-out" else "READY")
            if scenario == "revoke" and calls[0] > 1:
                status = "SIGNED_OUT"
            return synthetic(status)

        # The fixture contains no credentials and cannot sign in or choose a
        # tenant. The reader CLI still runs as a REAL child of real Quickshell.
        def execute_qs() -> None:
            proc = subprocess.run(
                [qs, "-p", str(root_config), "--no-color"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors="replace",
                timeout=22,
                check=False,
            )
            output = proc.stdout or ""
            if (proc.returncode != 0
                    or EXPECTED[scenario] not in output
                    or "IDENTITY_NATIVE_SMOKE_TIMEOUT" in output):
                # CI error messages are intentionally brief: no request path,
                # shell stdout payload, credentials or environment leaked.
                diagnostic = [
                    line for line in output.splitlines()
                    if ("ERROR" in line or "Error:" in line
                        or "WARN" in line or "Failed" in line)
                ]
                raise AssertionError(
                    f"Real Quickshell synthetic {scenario} failed: "
                    f"exit={proc.returncode}, expected_marker={EXPECTED[scenario]}, "
                    f"diagnostic_count={len(diagnostic)}, "
                    f"diagnostic_tail={diagnostic[-5:]}"
                )
            print(f"PASS native Quickshell / scenario={scenario} / tokenless")

        if scenario == "missing":
            execute_qs()
        else:
            with PrivateContextSocket(
                runtime_directory=directory,
                snapshot_provider=provider,
                clock=lambda: int(time.time()),
            ):
                execute_qs()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=tuple(EXPECTED), required=True)
    args = parser.parse_args()
    run(args.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
