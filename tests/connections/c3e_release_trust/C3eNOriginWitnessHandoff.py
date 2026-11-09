#!/usr/bin/env python3
"""C3e-N: CI-only compatibility check for two DIFFERENT trust boundaries.

C3b/C4b installed status service and C3e-L root witness are separate OS
processes with distinct credentials and lifecycle. This pure adapter checks
their *synthetic/test-supplied* evidence shapes together without EVER
converting evidence to authentication, release admission, human consent,
credential access or production readiness.

The C3b and C3e-L observations are not cryptographically joined here.
This adapter cannot tell whether a client forged either input. It must not
be used as a production authorization decision or status-authentication API.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCHEMA = "postapollo.connections.c3en-origin-witness-handoff.v1"
STATUS = "C3EN_CI_ONLY_ORIGINS_COMPATIBLE_NOT_BOUND"
SHA256 = re.compile(r"[0-9a-f]{64}")

WITNESS_KEYS = frozenset({
    "schema", "transport_peer_verified", "host_uid_observed",
    "observed_policy_epoch", "observed_release_sequence",
    "enrollment_sha256", "hostAuthenticated", "canApprove",
    "credentialActionsEnabled", "productionAuthority",
})

def load_origin():
    path = ROOT / "tests/connections/c3b_origin/C3bOriginCheck.py"
    spec = importlib.util.spec_from_file_location("c3en_readonly_c3b", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("C3EN_C3B_SOURCE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

C3B = load_origin()


def _denied(reason):
    return {
        "schema": SCHEMA,
        "status": reason,
        "installed_status_service_pid": 0,
        "separate_witness_process_pid": 0,
        "witness_floor_epoch": 0,
        "witness_floor_sequence": 0,
        "testEvidenceCompatible": False,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }


def inspect(*, installed_os_evidence, c4b_opt_proof, read_only_witness_status,
            expected_installed_pid, expected_witness_pid,
            expected_witness_enrollment_sha256, minimum_policy_epoch,
            minimum_release_sequence):
    """Check consistency of independent TEST observations, NOT real authority.

    The expected PID/digest/floor values are fixture-owned. This does not
    enforce authenticity, validate a signer, bind different namespaces or
    make a host connection. There is intentionally no approval output.
    """
    if (type(expected_installed_pid) is not int or
            expected_installed_pid <= 1 or
            type(expected_witness_pid) is not int or
            expected_witness_pid <= 1 or
            expected_installed_pid == expected_witness_pid or
            type(expected_witness_enrollment_sha256) is not str or
            SHA256.fullmatch(expected_witness_enrollment_sha256) is None or
            type(minimum_policy_epoch) is not int or
            minimum_policy_epoch < 1 or
            type(minimum_release_sequence) is not int or
            minimum_release_sequence < 1):
        return _denied("C3EN_INVALID_TEST_PINS")

    # Read-only C3b source from current main. Its 'coherent' result is
    # *always* a denial of all production actions, by design.
    result = C3B.evaluate(installed_os_evidence, c4b_opt=True,
                          opt_proof=c4b_opt_proof)
    if result.get("status") != "C3B_OS_ORIGIN_COHERENT_TEST_ONLY":
        return _denied("C3EN_INSTALLED_ORIGIN_REFUSED")
    if any(result.get(k) is not False for k in C3B.DENIED_FLAGS):
        return _denied("C3EN_ORIGIN_CLAIMED_AUTHORITY")
    if (type(installed_os_evidence) is not dict or
            installed_os_evidence.get("bus_pid") != expected_installed_pid or
            installed_os_evidence.get("main_pid") != expected_installed_pid):
        return _denied("C3EN_INSTALLED_PID_CHANGED")

    # L's read-only status represents a separate UID 0 witness.
    # Do NOT mistake the D-Bus UID (nonroot status service) for this UID 0
    # or pretend the two PIDs identify the same process.
    s = read_only_witness_status
    if (type(s) is not dict or set(s) != WITNESS_KEYS or
            s.get("schema") !=
                "postapollo.connections.c3el.host-observation.v1" or
            s.get("transport_peer_verified") is not True or
            type(s.get("host_uid_observed")) is not int or
            s["host_uid_observed"] != 0 or
            s.get("hostAuthenticated") is not False or
            s.get("canApprove") is not False or
            s.get("credentialActionsEnabled") is not False or
            s.get("productionAuthority") is not False):
        return _denied("C3EN_WITNESS_STATUS_UNTRUSTED")
    if (type(s.get("observed_policy_epoch")) is not int or
            type(s.get("observed_release_sequence")) is not int or
            s["observed_policy_epoch"] < minimum_policy_epoch or
            s["observed_release_sequence"] < minimum_release_sequence or
            s.get("enrollment_sha256") !=
                expected_witness_enrollment_sha256):
        return _denied("C3EN_WITNESS_FLOOR_OR_ENROLLMENT_REFUSED")

    # IMPORTANT: this success is ONLY a compatibility check between
    # test-controlled observations; no cryptographic cross-process binding
    # is present. That limitation is the point of the next installed-host
    # and signed-attestation integration gate.
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "installed_status_service_pid": expected_installed_pid,
        "separate_witness_process_pid": expected_witness_pid,
        "witness_floor_epoch": s["observed_policy_epoch"],
        "witness_floor_sequence": s["observed_release_sequence"],
        "testEvidenceCompatible": True,
        "hostAuthenticated": False,
        "canApprove": False,
        "credentialActionsEnabled": False,
        "productionAuthority": False,
    }
