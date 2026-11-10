#!/usr/bin/env python3
"""MACHINE Brave: read-only, one-click browser/Sway co-observation candidate.

Separate native host from the existing transport-only probe. The host gets
no browser window ID and cannot validate a Wayland/Chromium identity. Its
only OS interaction is two bounded Sway get_tree reads via the existing
focus witness. No display actions, filenames, session data or writes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveNativeProbe import (
    ORIGIN_PATTERN, ProbeError, _canonical_uuid, read_request, write_response,
)
from MachineBraveFocusWitness import FocusWitnessError, inspect_focus

HOST_NAME = "org.postapollo.machine_brave_focus_observe"
REQUEST_KIND = "machine-brave-native-focus-observe-request-v1"
RESPONSE_KIND = "machine-brave-native-focus-observation-v1"


class FocusObserveError(ValueError):
    pass


def handle(request, *, origin, runner=None):
    if not isinstance(origin, str) or not ORIGIN_PATTERN.fullmatch(origin):
        raise FocusObserveError("INVALID CALLER FORMAT")
    if (not isinstance(request, dict)
            or set(request) != {"kind", "challenge"}
            or request["kind"] != REQUEST_KIND):
        raise FocusObserveError("INVALID READ-ONLY REQUEST")
    try:
        challenge = _canonical_uuid(request["challenge"])
    except ProbeError as exc:
        raise FocusObserveError("INVALID CHALLENGE") from exc

    try:
        witness = inspect_focus(**({"runner": runner} if runner is not None else {}))
        stable_brave = witness["status"] == "brave_focus_observed"
    except (FocusWitnessError, OSError, TypeError, ValueError):
        witness = {}
        stable_brave = False

    # The output/workspace are transient hints, never a browser-window binding.
    return {
        "kind": RESPONSE_KIND,
        "status": ("host_brave_focus_observed_unverified" if stable_brave
                   else "no_host_focus_candidate"),
        "challenge": challenge,
        "read_only": True,
        "host_brave_focus_observed": stable_brave,
        "host_focus_stable_two_reads": stable_brave,
        "observed_output": witness["output"] if stable_brave else None,
        "observed_workspace": witness["workspace"] if stable_brave else None,
        "browser_window_id": None,
        "extension_origin_argument_observed": True,
        "extension_origin_authenticated": False,
        "browser_to_sway_identity_verified": False,
        "private_window_exclusion_verified_by_host": False,
        "restart_session_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def main(argv=None, stdin=None, stdout=None):
    arguments = sys.argv[1:] if argv is None else argv
    incoming = sys.stdin.buffer if stdin is None else stdin
    outgoing = sys.stdout.buffer if stdout is None else stdout
    if len(arguments) != 1 or not ORIGIN_PATTERN.fullmatch(arguments[0]):
        return 1
    try:
        request = read_request(incoming)
        reply = handle(request, origin=arguments[0])
    except (ProbeError, FocusObserveError, OSError, TypeError, ValueError):
        reply = {
            "kind": RESPONSE_KIND, "status": "request_rejected",
            "read_only": True, "browser_to_sway_identity_verified": False,
            "restore_allowed": False, "safe_actions": [],
        }
    try:
        write_response(outgoing, reply)
    except (ProbeError, OSError):
        return 1
    return 0 if reply["status"] != "request_rejected" else 1


if __name__ == "__main__":
    sys.exit(main())
