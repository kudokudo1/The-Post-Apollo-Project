"""Pure source-only proposal; no filesystem mutation or authorization.

Caller observations are synthetic/untrusted here. The future protected executor
must independently capture and verify them under the common operation lock.
"""
import hashlib
import json
import re

PIN = "8082bac43e3d8a0f506348e0ecee2e063d34935b"
CHECKS = {"lock_held", "protected_identity", "boot_policy_clear",
          "active_inode_excluded", "fixed_subvolume_verified",
          "external_fence_available", "legacy_entrypoints_retired"}
EXPECTED_NAMES = {"swapfile", "withdrawal.json", "withdrawal-result.json"}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()

def blocked(code):
    return {"state": "BLOCKED", "code": code, "can_execute": False}

def plan(helper, *, candidate_blob, identity, intent, outcome, snapshot,
         directory_names, boot_id, checks, existing_fence):
    """Propose archival custody, not permission to unlink or delete."""
    try:
        if candidate_blob != PIN:
            return blocked("CANDIDATE_MISMATCH")
        if existing_fence is not False:
            return blocked("RECLAIM_RECOVERY_REQUIRED")
        if (type(checks) is not dict or set(checks) != CHECKS
                or any(v is not True for v in checks.values())):
            return blocked("PROTECTED_PRECONDITIONS_UNVERIFIED")
        if (type(directory_names) is not list or len(directory_names) != len(EXPECTED_NAMES)
                or set(directory_names) != EXPECTED_NAMES):
            return blocked("UNEXPECTED_DIRECTORY_CONTENTS")
        if (type(identity) is not list or len(identity) != 4
                or any(type(row) not in (list, tuple) or len(row) != 3
                       or any(type(v) is not int or v < 0 for v in row)
                       or row[1] == 0 for row in identity)
                or len({tuple(row[:2]) for row in identity}) != 4
                or identity[0][2] != 0 or identity[2][2] != 0):
            return blocked("INVALID_IDENTITY")
        if type(intent) is not dict or type(outcome) is not dict:
            return blocked("VERIFIED_WITHDRAWAL_REQUIRED")
        observation = helper.classify_recovery(intent, outcome, identity, snapshot)
        if observation["code"] != "RECORDED_VERIFIED_INACTIVE":
            return blocked("WITHDRAWAL_NOT_VERIFIED_INACTIVE")
        # Derive the witness from the exact bound durable pair. A caller
        # cannot supply a substitute witness or bind legacy records to now.
        withdrawal_witness = helper.withdrawal_boot_witness(
            intent, outcome, identity, snapshot, boot_id)
        expected_witness = {"version": 1, "boot_id": boot_id,
                            "withdrawal_digest": digest([intent, outcome])}
        if (not helper.canonical_boot_id(boot_id)
                or type(withdrawal_witness) is not dict
                or withdrawal_witness != expected_witness):
            return blocked("CONTEMPORANEOUS_BOOT_WITNESS_REQUIRED")
        bundle = {"version": 2, "state": "RECLAIM_ARCHIVE_PROPOSAL",
                  "allocation": "managed-nvme-extension", "candidate_blob": PIN,
                  "boot_id": boot_id, "identity": [list(row) for row in identity],
                  "withdrawal_witness": withdrawal_witness,
                  "records": [intent, outcome],
                  "expected_file_bytes": identity[3][2],
                  "base_size_kib": observation["baseSizeKiB"]}
        # JSON round trip separates the proposal from mutable caller inputs.
        bundle = json.loads(json.dumps(bundle, sort_keys=True, allow_nan=False))
        return {"state": "ARCHIVE_CUSTODY_PROPOSED", "code": "REVIEW_AND_FRESH_AUTH_REQUIRED",
                "archive_digest": digest(bundle), "bundle": bundle, "can_execute": False}
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return blocked("INVALID_EVIDENCE")

def fence_state(marker_present, marker, *, archive_verified, extension_absent):
    """Conservative display classification. Never authorizes clearing a fence."""
    if marker_present is False:
        return {"state":"NO_FENCE_OBSERVED", "can_execute":False, "can_clear":False}
    if (marker_present is not True or type(marker) is not dict
            or set(marker) != {"version","state","archive_digest"}
            or type(marker["version"]) is not int or marker["version"] != 1
            or type(marker["archive_digest"]) is not str
            or re.fullmatch(r"[a-f0-9]{64}", marker["archive_digest"]) is None
            or marker["state"] not in ("PREPARED","VERIFIED_ABSENT")
            or archive_verified is not True):
        code = "UNVERIFIED_EXTERNAL_FENCE"
    elif marker["state"] == "VERIFIED_ABSENT" and extension_absent is True:
        code = "RECORDED_ABSENCE_REVIEW_REQUIRED"
    else:
        code = "RECLAIM_OUTCOME_UNVERIFIED"
    return {"state":"RECOVERY_REQUIRED", "code":code, "can_execute":False, "can_clear":False}
