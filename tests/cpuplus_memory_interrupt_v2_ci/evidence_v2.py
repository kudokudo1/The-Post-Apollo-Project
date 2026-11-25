"""Pure evidence candidate classifier. No native provenance or authority."""
import uuid

PIN = "5f6e6d800dcf41c1f0f7330fdb248dfd2177104f"
ORDER = ("SYSCALL_ENTER", "UNUSE_ENTER", "SIGNAL_GENERATE",
         "UNUSE_RETURN", "SYSCALL_EXIT", "SIGNAL_DELIVER")
VALUES = (168, 0, 15, -4, -4, 15)
COUNTERS = {"buffer_overrun", "commit_overrun", "dropped_events",
            "entry_probe_missed", "return_probe_missed"}

def canonical_boot(value):
    try:
        return type(value) is str and str(uuid.UUID(value)) == value and uuid.UUID(value).int != 0
    except (ValueError, AttributeError, TypeError):
        return False

def classify(events, *, candidate_blob, boot_id, observed_boot_id,
             actor_verified, signal_target_verified, probe_loss_verified,
             loss, sender_pid):
    def unknown(code):
        return {"state": "UNKNOWN", "code": code, "can_execute": False}
    if candidate_blob != PIN:
        return unknown("CANDIDATE_MISMATCH")
    if not canonical_boot(boot_id) or not canonical_boot(observed_boot_id) or boot_id != observed_boot_id:
        return unknown("BOOT_UNVERIFIED")
    if actor_verified is not True or signal_target_verified is not True:
        return unknown("ACTOR_OR_SIGNAL_TARGET_UNVERIFIED")
    # A collector must independently establish counter provenance. Missing
    # fprobe accounting is not interchangeable with zero trace buffer loss.
    if probe_loss_verified is not True:
        return unknown("PROBE_LOSS_UNVERIFIED")
    if (type(loss) is not dict or set(loss) != COUNTERS
            or any(type(v) is not int or v != 0 for v in loss.values())):
        return unknown("TRACE_LOSS_OR_ACCOUNTING_INVALID")
    if type(sender_pid) is not int or sender_pid <= 0:
        return unknown("SIGNAL_SENDER_UNVERIFIED")
    if type(events) is not list or len(events) != len(ORDER):
        return unknown("BOUNDARY_MISSING_OR_REPEATED")
    actor = None
    previous = -1
    for event, kind, value in zip(events, ORDER, VALUES):
        if type(event) is not dict or set(event) != {
                "kind", "time_ns", "target_pid", "target_start_ticks", "emitter_pid", "value"}:
            return unknown("INVALID_EVENT")
        if any(type(event[k]) is not int for k in
               ("time_ns", "target_pid", "target_start_ticks", "emitter_pid", "value")):
            return unknown("INVALID_EVENT")
        if event["kind"] != kind or event["value"] != value:
            return unknown("BOUNDARY_OR_RETURN_MISMATCH")
        current = (event["target_pid"], event["target_start_ticks"])
        if min(current) <= 0 or event["time_ns"] <= previous:
            return unknown("ORDER_OR_IDENTITY_INVALID")
        if actor is not None and actor != current:
            return unknown("ACTOR_CHANGED")
        actor, previous = current, event["time_ns"]
        if sender_pid == actor[0]:
            return unknown("SENDER_TARGET_COLLISION")
        expected_emitter = sender_pid if kind == "SIGNAL_GENERATE" else actor[0]
        if event["emitter_pid"] != expected_emitter:
            return unknown("EMITTER_MISMATCH")
    # Input provenance is not proved by this function. Even an exact match
    # does not establish causation, recovery state or permission to execute.
    return {"state": "INTERRUPTED_RETURN_OBSERVED",
            "code": "ORDERED_TRACE_AND_DELIVERY_CANDIDATE", "can_execute": False}
