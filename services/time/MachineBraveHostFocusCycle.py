#!/usr/bin/env python3
"""MACHINE // Operator-triggered read-only A/B/A Sway focus continuity check.

Reads exactly two Sway tree snapshots per step. A matching A/B/A *host*
pattern is not a Brave-browser-window binding or an identity certificate.
Never writes a file, launches Brave, focuses an app, or exposes Sway IDs/PIDs.
No native messaging, session capture, browser data access, or RESTORE authority.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveFocusWitness import (
    BRAVE_APP_IDS, FocusWitnessError, _focused_leaf,
)
from MachineSwayRead import PreviewError, _read_json


STEPS = ("A1", "B1", "A2")
SWAY_TREE_CMD = ["swaymsg", "-r", "-t", "get_tree"]
STEP_SECONDS = 4


class HostCycleError(ValueError):
    pass


def _stable_focused_brave(*, runner):
    """Return an in-memory Sway identity tuple, never serialized."""
    try:
        first = _focused_leaf(_read_json(SWAY_TREE_CMD, runner))
        second = _focused_leaf(_read_json(SWAY_TREE_CMD, runner))
    except (PreviewError, FocusWitnessError) as exc:
        raise HostCycleError("SWAY OBSERVATION UNAVAILABLE") from exc
    if first is None or second is None:
        raise HostCycleError("NO FOCUSED CLIENT")
    if first != second:
        raise HostCycleError("FOCUS CHANGED BETWEEN READS")
    if first[1] not in BRAVE_APP_IDS:
        raise HostCycleError("FOCUSED CLIENT NOT BRAVE")
    return first


def inspect_cycle(*, runner=subprocess.run, pause=time.sleep, announce=None):
    """Explicit diagnostic with six read-only get_tree calls total.

    The user is asked to focus normal Brave window A, then different B,
    then A again. No compositor actions or browser API are ever invoked.
    A consistent cycle establishes only transient *host* continuity.
    """
    identities = []
    for step in STEPS:
        if announce is not None:
            announce(step)
        pause(STEP_SECONDS)
        identities.append(_stable_focused_brave(runner=runner))

    same_a = identities[0] == identities[2]
    different_b = identities[0] != identities[1]
    # The tuple includes transient Sway ID, app_id, output, and workspace.
    # All remain in local memory and are deliberately excluded from JSON.
    pattern = same_a and different_b
    return {
        "kind": "machine-sway-brave-host-focus-cycle-v1",
        "status": ("consistent_unverified_host_focus_cycle"
                   if pattern else "unbound_host_focus_cycle"),
        "observed_steps": len(STEPS),
        "read_only": True,
        "browser_window_id": None,
        "browser_to_sway_identity_verified": False,
        "extension_origin_authenticated": False,
        "private_window_exclusion_verified": False,
        "restart_session_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "action_allowed": False,
        "safe_actions": [],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args != ["inspect"]:
        print(json.dumps({"status": "error", "reason": "INVALID ACTION"}))
        return 1

    def tell(step):
        guidance = ("FIRST" if step == "A1"
                    else "DIFFERENT" if step == "B1" else "FIRST AGAIN")
        print("MACHINE // FOCUS " + guidance
              + " BRAVE WINDOW (" + step + ")"
              + " // OBSERVING IN 4 SECONDS",
              file=sys.stderr, flush=True)

    try:
        result = inspect_cycle(announce=tell)
    except (HostCycleError, OSError, TypeError, ValueError):
        print(json.dumps({
            "kind": "machine-sway-brave-host-focus-cycle-v1",
            "status": "unavailable",
            "read_only": True,
            "browser_to_sway_identity_verified": False,
            "session_capture_allowed": False,
            "restore_allowed": False,
            "action_allowed": False,
            "safe_actions": [],
        }, separators=(",", ":")))
        return 1
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
