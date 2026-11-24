"""Pure M1c.3b.3 advisory status. Never runs commands or grants authority.

All samples are untrusted caller claims. A caller must bind monotonic samples
to one running observer and discard continuity after restart. No production
threshold defaults, background monitor, persistence or dispatch in this module.
"""
import math
from memory_adjustment_queue import QueueError, _int, _source, _uuid, _validate

READY_CODE = "FRESH_AUTH_AND_ROOT_CHECK_REQUIRED"
BLOCKERS = {"BASE_OR_EXTENSION_INACTIVE", "UNEXPECTED_SWAP_IDENTITY",
            "UNEXPECTED_CAPACITY", "UNSUPPORTED_TARGET", "EXTENSION_OCCUPIED",
            "RAM_HEADROOM", "BASE_HEADROOM", "MEMORY_PRESSURE",
            "OBSERVATION_UNAVAILABLE"}
EVIDENCE = {"targetGiB", "baseSizeKiB", "extensionSizeKiB", "extensionUsedKiB",
            "availableKiB", "requiredRamKiB", "baseFreeKiB", "requiredBaseFreeKiB",
            "someAvg10", "fullAvg10"}
FIELDS = {"version", "request_id", "observer_id", "source", "wall_time",
          "monotonic_ms", "operation_state", "preflight"}


def _sample(record, sample):
    if type(sample) is not dict or set(sample) != FIELDS:
        raise QueueError("INVALID_OBSERVATION")
    if type(sample["version"]) is not int or sample["version"] != 1:
        raise QueueError("INVALID_OBSERVATION_VERSION")
    if _uuid(sample["request_id"]) != record["id"]:
        raise QueueError("STALE_REQUEST")
    _uuid(sample["observer_id"])
    _source(sample["source"])
    _int(sample["wall_time"])
    _int(sample["monotonic_ms"])
    if sample["operation_state"] not in ("IDLE", "BUSY", "UNKNOWN"):
        raise QueueError("INVALID_OPERATION_STATE")
    p = sample["preflight"]
    if type(p) is not dict or set(p) != {"version", "state", "code", "evidence"}:
        raise QueueError("INVALID_PREFLIGHT")
    if type(p["version"]) is not int or p["version"] != 1 or type(p["evidence"]) is not dict:
        raise QueueError("INVALID_PREFLIGHT")
    if p["state"] == "WAITING":
        if type(p["code"]) is not str or p["code"] not in BLOCKERS:
            raise QueueError("INVALID_BLOCKER")
        return
    if p["state"] != "READY_ADVISORY" or p["code"] != READY_CODE:
        raise QueueError("INVALID_PREFLIGHT")
    e = p["evidence"]
    if set(e) != EVIDENCE:
        raise QueueError("INVALID_READY_EVIDENCE")
    for key in EVIDENCE - {"someAvg10", "fullAvg10"}:
        _int(e[key])
    for key in ("someAvg10", "fullAvg10"):
        value = e[key]
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 <= value <= 100:
            raise QueueError("INVALID_READY_EVIDENCE")
    source = sample["source"]
    if (not source["base"] or not source["extension"]
            or e["targetGiB"] != record["target_gib"]
            or e["baseSizeKiB"] != source["base"]["size_kib"]
            or e["extensionSizeKiB"] != source["extension"]["size_kib"]
            or not 0 <= record["target_gib"] * 1048576 - e["baseSizeKiB"] <= 1024
            or not record["target_gib"] or e["extensionUsedKiB"] != 0
            or e["requiredRamKiB"] <= 0 or e["availableKiB"] < e["requiredRamKiB"]
            or e["requiredBaseFreeKiB"] <= 0
            or not e["requiredBaseFreeKiB"] <= e["baseFreeKiB"] <= e["baseSizeKiB"]
            or e["fullAvg10"] != 0 or e["someAvg10"] > 1):
        raise QueueError("INCONSISTENT_READY_EVIDENCE")


def evaluate(record, sample, *, now, monotonic_ms, max_age_ms, previous=None):
    """Return a display status only; recompute each time. No saved READY.

    previous is the immediately preceding sample from the same observer.
    Two samples are necessary but are not proof of continuous stability.
    """
    def status(state, code):
        return {"state": state, "code": code, "can_execute": False}
    try:
        _validate(record)
        _int(now)
        _int(monotonic_ms)
        _int(max_age_ms, 1)
        if record["state"] != "QUEUED":
            return status(record["state"], "TERMINAL_REQUEST")
        if now < record["requested_at"]:
            return status("UNKNOWN", "CLOCK_ROLLBACK")
        if now >= record["expires_at"]:
            return status("WAITING", "EXPIRY_RECONCILIATION_REQUIRED")
        _sample(record, sample)
        if sample["source"]["boot_id"] != record["source"]["boot_id"]:
            return status("UNKNOWN", "BOOT_CHANGED")
        if sample["source"] != record["source"]:
            return status("UNKNOWN", "SOURCE_CHANGED")
        if sample["operation_state"] == "UNKNOWN":
            return status("UNKNOWN", "OPERATION_AMBIGUOUS")
        if sample["operation_state"] == "BUSY":
            return status("WAITING", "OPERATION_BUSY")
        if (not record["requested_at"] <= sample["wall_time"] <= now
                or now - sample["wall_time"] > (max_age_ms + 999) // 1000
                or not 0 <= monotonic_ms - sample["monotonic_ms"] <= max_age_ms):
            return status("UNKNOWN", "STALE_OBSERVATION")
        if sample["preflight"]["state"] == "WAITING":
            return status("WAITING", sample["preflight"]["code"])
        if previous is None:
            return status("WAITING", "CONTINUITY_REQUIRED")
        _sample(record, previous)
        if (previous["observer_id"] != sample["observer_id"]
                or previous["source"] != sample["source"]
                or previous["operation_state"] != "IDLE"
                or previous["preflight"]["state"] != "READY_ADVISORY"):
            return status("WAITING", "CONTINUITY_REQUIRED")
        if (not record["requested_at"] <= previous["wall_time"] <= sample["wall_time"]
                or not 0 < sample["monotonic_ms"] - previous["monotonic_ms"] <= max_age_ms):
            return status("UNKNOWN", "OBSERVATION_ORDER_INVALID")
        return status("READY_ADVISORY", READY_CODE)
    except (QueueError, ValueError, TypeError, KeyError, OverflowError):
        return status("UNKNOWN", "INVALID_OBSERVATION")
