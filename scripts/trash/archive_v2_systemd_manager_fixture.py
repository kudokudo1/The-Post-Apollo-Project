#!/usr/bin/env python3
"""V2u deny-only interface for a future authenticated systemd PIDFD query.

systemd >=253 exposes Manager.GetUnitByPIDFD(h), returning unit object path,
unit ID and invocation ID. This module intentionally DOES NOT connect to
D-Bus, parse arbitrary busctl text, or claim that a test provider has
authenticated PID 1. It tests exact response/policy binding against a
kernel-held pidfd; all results remain non-authorizing.

A real manager adapter requires independent source-owner/Connections approval,
an authenticated system bus and verification of the manager's unique sender.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from scripts.trash.archive_v2_peer_lifecycle import FixturePeerLease
from scripts.trash.archive_v2_fixture_service_identity import (
    PinnedFixtureServiceFiles,
)
from scripts.trash.archive_v2_origin_checkpoint import CGROUP_SAFE
from scripts.trash.archive_v2_signed_capture import ALLOWED_OWNERS, SHA

UNIT_ID = re.compile(r"^[A-Za-z0-9_@.:-]{1,128}[.]service$")
INVOCATION = re.compile(r"^[0-9a-f]{32}$")
OBJECT_PATH = re.compile(
    r"^/org/freedesktop/systemd1/unit/[A-Za-z0-9_]{1,256}$")
MANAGER_POLICY = frozenset((
    "origin", "ownerId", "expectedUid", "expectedGid",
    "expectedUnitId", "expectedInvocationId", "expectedUnitObjectPath",
    "expectedControlGroup", "expectedFragmentPath", "expectedUnitSha256",
))
MANAGER_RESPONSE = frozenset((
    "unitId", "invocationId", "unitObjectPath", "controlGroup",
    "fragmentPath", "loadState", "activeState",
))


class ManagerOriginError(Exception):
    """Fixed fail-closed code, never raw system paths or command output."""


def _require(ok, code):
    if not ok:
        raise ManagerOriginError(code)


class SyntheticPidfdManager:
    """TEST-ONLY in-memory response provider, NEVER a trusted D-Bus client.

    It inspects a real open pidfd but fabricates the manager response for
    adversarial contract tests. No D-Bus calls, systemd control or privilege.
    """

    def __init__(self, response):
        _require(type(response) is dict and set(response) == MANAGER_RESPONSE,
                 "MANAGER_RESPONSE_SCHEMA_INVALID")
        self._response = dict(response)
        self.calls = 0

    def replace_test_response(self, response):
        _require(type(response) is dict and set(response) == MANAGER_RESPONSE,
                 "MANAGER_RESPONSE_SCHEMA_INVALID")
        self._response = dict(response)

    def get_unit_by_pidfd(self, fd):
        _require(type(fd) is int and fd >= 0,
                 "MANAGER_PIDFD_INVALID")
        try:
            st = os.fstat(fd)
        except OSError as exc:
            raise ManagerOriginError("MANAGER_PIDFD_INVALID") from exc
        _require(st.st_ino > 0 and st.st_mode != 0,
                 "MANAGER_PIDFD_INVALID")
        self.calls += 1
        return dict(self._response)


def inspect_fixture_manager_origin(
    lease, manager, policy, *, service_files, origin_policy,
    origin_witness_sha256, expected_owner,
):
    """Bind synthetic manager reply to real pidfd + V2q/V2t evidence.

    Caller supplies service policy, manager policy and synthetic response
    independently of untrusted socket payload. A matching test fixture
    remains sourceServiceVerified=false and systemdUnitVerified=false.
    """
    _require(type(lease) is FixturePeerLease,
             "MANAGER_PEER_LEASE_REQUIRED")
    _require(type(manager) is SyntheticPidfdManager,
             "MANAGER_TRUST_NOT_PROVISIONED")
    _require(type(service_files) is PinnedFixtureServiceFiles,
             "MANAGER_FILES_REQUIRED")
    _require(type(policy) is dict and set(policy) == MANAGER_POLICY
             and policy.get("origin") == "TEST_FIXTURE_ONLY",
             "MANAGER_POLICY_NOT_PROVISIONED")
    _require(type(origin_policy) is dict
             and origin_policy.get("origin") == "TEST_FIXTURE_ONLY"
             and type(origin_policy.get("expectedCgroupV2")) is str
             and type(origin_witness_sha256) is str
             and SHA.fullmatch(origin_witness_sha256),
             "MANAGER_ORIGIN_REQUIRED")
    _require(type(expected_owner) is str
             and expected_owner in ALLOWED_OWNERS
             and policy["ownerId"] == expected_owner
             and service_files.policy["ownerId"] == expected_owner
             and origin_policy.get("ownerId") == expected_owner,
             "MANAGER_OWNER_MISMATCH")
    _require(type(policy["expectedUid"]) is int
             and type(policy["expectedGid"]) is int
             and policy["expectedUid"] == service_files.policy["expectedUid"]
             and policy["expectedGid"] == service_files.policy["expectedGid"]
             and policy["expectedUid"] == origin_policy.get("expectedUid")
             and policy["expectedGid"] == origin_policy.get("expectedGid"),
             "MANAGER_UID_MISMATCH")
    _require(type(policy["expectedUnitId"]) is str
             and UNIT_ID.fullmatch(policy["expectedUnitId"])
             and type(policy["expectedInvocationId"]) is str
             and INVOCATION.fullmatch(policy["expectedInvocationId"])
             and type(policy["expectedUnitObjectPath"]) is str
             and OBJECT_PATH.fullmatch(policy["expectedUnitObjectPath"]),
             "MANAGER_UNIT_POLICY_INVALID")
    _require(type(policy["expectedControlGroup"]) is str
             and CGROUP_SAFE.fullmatch(policy["expectedControlGroup"])
             and policy["expectedControlGroup"]
                 == origin_policy["expectedCgroupV2"],
             "MANAGER_CGROUP_POLICY_INVALID")
    _require(type(policy["expectedFragmentPath"]) is str
             and policy["expectedFragmentPath"]
                 == str(service_files.root / service_files.policy["unitName"])
             and type(policy["expectedUnitSha256"]) is str
             and SHA.fullmatch(policy["expectedUnitSha256"])
             and policy["expectedUnitSha256"]
                 == service_files.policy["unitSha256"],
             "MANAGER_UNIT_FILE_POLICY_INVALID")
    lease.require_alive()
    # FixturePeerLease's pidfd refers to the original process and is NOT
    # created from caller's numeric PID. A production D-Bus client must
    # actually pass this descriptor via D-Bus UNIX_FD semantics.
    pidfd = lease.fixture_pidfd
    reply = manager.get_unit_by_pidfd(pidfd)
    _require(type(reply) is dict and set(reply) == MANAGER_RESPONSE,
             "MANAGER_RESPONSE_SCHEMA_INVALID")
    _require(all(type(reply[k]) is str for k in MANAGER_RESPONSE),
             "MANAGER_RESPONSE_SCHEMA_INVALID")
    _require(reply["unitId"] == policy["expectedUnitId"]
             and reply["invocationId"] == policy["expectedInvocationId"]
             and reply["unitObjectPath"] == policy["expectedUnitObjectPath"]
             and reply["loadState"] == "loaded"
             and reply["activeState"] == "active",
             "MANAGER_UNIT_MISMATCH")
    _require(reply["controlGroup"] == policy["expectedControlGroup"]
             and CGROUP_SAFE.fullmatch(reply["controlGroup"]),
             "MANAGER_CGROUP_MISMATCH")
    _require(reply["fragmentPath"] == policy["expectedFragmentPath"],
             "MANAGER_FRAGMENT_MISMATCH")
    current_files = service_files.require_unchanged()
    lease.require_alive()
    data = {
        "ownerId":expected_owner,
        "peerWitnessSha256":lease.peer_witness_sha256,
        "originWitnessSha256":origin_witness_sha256,
        "serviceWitnessSha256":current_files["serviceWitnessSha256"],
        "unitId":reply["unitId"],
        "invocationId":reply["invocationId"],
        "unitObjectPath":reply["unitObjectPath"],
        "controlGroupSha256":
            hashlib.sha256(reply["controlGroup"].encode("ascii")).hexdigest(),
        "fragmentSha256":policy["expectedUnitSha256"],
        "pidfdInode":os.fstat(pidfd).st_ino,
    }
    raw = json.dumps(data, sort_keys=True, ensure_ascii=True,
                     separators=(",",":"), allow_nan=False).encode("ascii")
    return {
        "state":"TEST_PIDFD_MANAGER_REPLY_MATCHED_DENY_ONLY",
        "managerWitnessSha256":hashlib.sha256(raw).hexdigest(),
        "serviceWitnessSha256":current_files["serviceWitnessSha256"],
        "ownerId":expected_owner,
        "managerFixtureMatched":True,
        "systemdUnitVerified":False,
        "sourceServiceVerified":False,
        "sourceProcessVerified":False,
        "captureAllowed":False,
        "productionAllowed":False,
    }
