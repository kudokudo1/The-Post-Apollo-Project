#!/usr/bin/env python3
"""Separate opt-in title marker host for disposable MACHINE Brave only.

Chromium-supplied origin is not authenticated against local impostors.
A title marker can be spoofed by another local Sway client. The evidence
is transient, diagnostic and grants absolutely no restore authority.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineBraveNativeProbe import (
    ORIGIN_PATTERN, ProbeError, _canonical_uuid, read_request, write_response,
)
from MachineBraveTitleMarkerWitness import inspect_marker

HOST_NAME = "org.postapollo.machine_brave_title_marker"
REQUEST_KIND = "machine-brave-marker-observe-request-v1"
RESPONSE_KIND = "machine-brave-marker-observe-response-v1"


class MarkerHostError(ValueError):
    pass


def handle(request, *, origin, runner=None):
    if not isinstance(origin, str) or not ORIGIN_PATTERN.fullmatch(origin):
        raise MarkerHostError("INVALID CALLER FORMAT")
    if (not isinstance(request, dict)
            or set(request) != {"kind", "challenge"}
            or request["kind"] != REQUEST_KIND):
        raise MarkerHostError("UNSUPPORTED REQUEST")
    try:
        token = _canonical_uuid(request["challenge"])
    except ProbeError as exc:
        raise MarkerHostError("INVALID CHALLENGE") from exc
    observed = inspect_marker(
        token, **({"runner": runner} if runner is not None else {}))
    matched = observed is not None
    return {
        "kind": RESPONSE_KIND,
        "status": ("transient_title_marker_observed" if matched
                   else "marker_not_observed"),
        "challenge": token,
        "read_only_host": True,
        "marker_unique_and_stable": matched,
        "sway_container_id": observed["sway_container_id"] if matched else None,
        "output": observed["output"] if matched else None,
        "workspace": observed["workspace"] if matched else None,
        "browser_window_id": None,
        "extension_origin_authenticated": False,
        "host_private_window_exclusion_verified": False,
        "persistent_window_identity_verified": False,
        "session_capture_allowed": False,
        "restore_allowed": False,
        "safe_actions": [],
    }


def main(argv=None, stdin=None, stdout=None):
    arguments = sys.argv[1:] if argv is None else argv
    inp = sys.stdin.buffer if stdin is None else stdin
    out = sys.stdout.buffer if stdout is None else stdout
    if len(arguments) != 1 or not ORIGIN_PATTERN.fullmatch(arguments[0]):
        return 1
    try:
        request = read_request(inp)
        result = handle(request, origin=arguments[0])
    except (ProbeError, MarkerHostError, OSError, TypeError, ValueError):
        result = {"kind": RESPONSE_KIND, "status": "request_rejected",
                  "read_only_host": True, "restore_allowed": False,
                  "safe_actions": []}
    try:
        write_response(out, result)
    except (ProbeError, OSError):
        return 1
    return 1 if result["status"] == "request_rejected" else 0


if __name__ == "__main__":
    sys.exit(main())
