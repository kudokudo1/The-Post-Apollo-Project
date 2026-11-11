#!/usr/bin/env python3
"""MACHINE // Read-only native Brave launch plan for a marked disposable trial.

This tool NEVER launches a browser or creates/registers a native host.
A plausible executable name and mode cannot establish vendor authenticity,
nor that Brave actually honors --user-data-dir on this Fedora installation.
After a separately approved launch, the operator MUST check brave://version.
Flatpak/container launch paths are unsupported by this native-binary planner.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveDisposableTrial import TrialError, _validate_root

SUPPORTED_NATIVE_NAMES = frozenset({
    "brave", "brave-browser", "brave-browser-stable",
    "brave-browser-beta", "brave-browser-nightly",
})


class LaunchPlanError(ValueError):
    pass


def _candidate_executable(binary, *, trial_root):
    if (not isinstance(binary, str) or not binary
            or any(ord(c) < 32 or ord(c) == 127 for c in binary)):
        raise LaunchPlanError("INVALID BROWSER EXECUTABLE")
    path = Path(binary)
    if not path.is_absolute() or path.name not in SUPPORTED_NATIVE_NAMES:
        raise LaunchPlanError("UNSUPPORTED NATIVE BROWSER PATH")
    try:
        target = path.resolve(strict=True)
        info = target.stat()
    except (OSError, RuntimeError) as exc:
        raise LaunchPlanError("BROWSER EXECUTABLE UNAVAILABLE") from exc
    if (not stat.S_ISREG(info.st_mode) or not os.access(target, os.X_OK)
            or target.is_relative_to(trial_root)
            or path.is_relative_to(trial_root)
            or "brave" not in target.name.lower()):
        raise LaunchPlanError("UNSUPPORTED NATIVE BROWSER EXECUTABLE")
    return str(path)


def plan_launch(trial_root, browser_binary):
    """Validate candidate and emit argv for operator inspection, not execution."""
    try:
        root = _validate_root(trial_root)
    except (TrialError, OSError, ValueError) as exc:
        raise LaunchPlanError("INVALID DISPOSABLE PROFILE") from exc
    binary = _candidate_executable(browser_binary, trial_root=root)
    profile = str(root / "profile")
    xdg = str(root / "xdg-config")
    expected_manifest = str(
        root / "xdg-config" / "BraveSoftware" / "Brave-Browser"
        / "NativeMessagingHosts" / "org.postapollo.machine_brave_probe.json"
    )
    return {
        "kind": "machine-brave-disposable-native-launch-preview-v1",
        "status": "operator_review_required",
        "candidate_native_binary": binary,
        "candidate_argv": [
            binary,
            "--user-data-dir=" + profile,
            "--no-first-run",
            "--no-default-browser-check",
        ],
        "expected_user_data_dir": profile,
        # The browser's native host lookup follows XDG_CONFIG_HOME,
        # *not* the --user-data-dir profile on the observed Brave RPM.
        "environment_overrides": {"XDG_CONFIG_HOME": xdg},
        "expected_native_host_manifest": expected_manifest,
        "manual_check_url": "brave://version",
        "expected_profile_path_prefix": profile + "/",
        "browser_launched_by_tool": False,
        "browser_identity_authenticated": False,
        "brave_package_verified": False,
        "profile_isolation_runtime_verified": False,
        "host_registration_used_by_browser_verified": False,
        "extension_loaded": False,
        "native_transport_tested": False,
        "browser_to_sway_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 3 or args[0] != "plan":
        return 2
    try:
        result = plan_launch(args[1], args[2])
    except (LaunchPlanError, OSError, TypeError, ValueError):
        print(json.dumps({"status": "refused", "safe_actions": []}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
