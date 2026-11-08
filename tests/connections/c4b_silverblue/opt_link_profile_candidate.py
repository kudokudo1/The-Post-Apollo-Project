#!/usr/bin/env python3
"""C4b ONLY: pure adversarial MODEL of a proposed Silverblue /opt exception.

NOT an OS probe, policy selector, service entrypoint, or acceptance gate.
Never import this from the C3b checker or running guest. The C3b/C3c
security owner must explicitly approve any change to its origin predicate.
All outcomes are test-only observations with every authorization bit false.
"""
from __future__ import annotations

import re

PROFILE = "C4B_OFFLINE_SILVERBLUE_44_CANDIDATE_ONLY"
LITERAL_OPT_LINK = "var/opt"
RESOLVED_OPT = "/var/opt"
GUARDED_PATHS = (
    "/", "/var", "/var/opt",
    "/var/opt/postapollo-c2o-venv",
    "/var/opt/postapollo-c2o-venv/bin",
    "/opt/postapollo-c2o-venv",
    "/opt/postapollo-c2o-venv/bin",
)
CONTEXT_KEYS = {
    "profile", "fedora_release", "ostree_booted", "ostree_ref",
    "network_interfaces", "opt_before", "opt_after",
    "dirs_before", "dirs_after",
}
LINK_KEYS = {
    "owner", "group", "mode", "directory", "symlink",
    "target", "resolved", "device", "inode",
}
DIRECTORY_KEYS = {"owner", "mode", "directory", "symlink"}
DENIED_FLAGS = {
    "hostAuthenticated": False, "credentialPresent": False,
    "grantActive": False, "canApprove": False, "canUseApi": False,
}


def refusal(status: str) -> dict:
    return {"status": status, **DENIED_FLAGS}


def _integer(value: object) -> bool:
    return type(value) is int


def _safe_dir(value: object) -> bool:
    return (
        type(value) is dict
        and set(value) == DIRECTORY_KEYS
        and _integer(value["owner"])
        and value["owner"] == 0
        and _integer(value["mode"])
        and 0 <= value["mode"] <= 0o7777
        and (value["mode"] & 0o022) == 0
        and value["directory"] is True
        and value["symlink"] is False
    )


def _safe_link(value: object) -> bool:
    # Symlink mode 0777 is nominal and NOT the resolved target's mode.
    return (
        type(value) is dict
        and set(value) == LINK_KEYS
        and _integer(value["owner"]) and value["owner"] == 0
        and _integer(value["group"]) and value["group"] == 0
        and _integer(value["mode"]) and value["mode"] == 0o777
        and value["directory"] is False and value["symlink"] is True
        and value["target"] == LITERAL_OPT_LINK
        and value["resolved"] == RESOLVED_OPT
        and _integer(value["device"]) and value["device"] > 0
        and _integer(value["inode"]) and value["inode"] > 0
    )


def evaluate_candidate(evidence: object) -> dict:
    """Test-only proposed layout predicate; NEVER grants C3b OS-origin success.

    This pure function cannot verify that supplied evidence came from the OS.
    A future OWNER-APPROVED C3b change would require an independent, bounded
    OS read, path-component-wise lstat and two snapshots around D-Bus queries.
    """
    if type(evidence) is not dict or set(evidence) != CONTEXT_KEYS:
        return refusal("C4B_CANDIDATE_INVALID_EVIDENCE")
    e = evidence
    if (
        e["profile"] != PROFILE
        or type(e["fedora_release"]) is not str
        or re.fullmatch(r"Fedora release 44(?: .*)?", e["fedora_release"]) is None
        or e["ostree_booted"] is not True
        or type(e["ostree_ref"]) is not str
        or "silverblue" not in e["ostree_ref"].lower()
        or type(e["network_interfaces"]) is not list
        or e["network_interfaces"] != []
    ):
        return refusal("C4B_CANDIDATE_NOT_OFFLINE_SILVERBLUE_44")
    if not _safe_link(e["opt_before"]) or not _safe_link(e["opt_after"]):
        return refusal("C4B_CANDIDATE_UNTRUSTED_OPT_LINK")
    if e["opt_before"] != e["opt_after"]:
        return refusal("C4B_CANDIDATE_OPT_LINK_CHANGED")
    before, after = e["dirs_before"], e["dirs_after"]
    if (
        type(before) is not dict or type(after) is not dict
        or set(before) != set(GUARDED_PATHS)
        or set(after) != set(GUARDED_PATHS)
    ):
        return refusal("C4B_CANDIDATE_INVALID_DIRECTORY_CHAIN")
    for path in GUARDED_PATHS:
        if not _safe_dir(before[path]) or not _safe_dir(after[path]):
            return refusal("C4B_CANDIDATE_UNPROTECTED_DIRECTORY")
        if before[path] != after[path]:
            return refusal("C4B_CANDIDATE_DIRECTORY_CHAIN_CHANGED")
    # Never return a C3b-compatible PASS marker or permission to use an API.
    return refusal("C4B_SILVERBLUE_OPT_LAYOUT_CANDIDATE_ONLY")
