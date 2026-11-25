"""Source-only evidence gate for a future disposable kernel trace fixture.

No tracing, signals, swap commands, host I/O or authorization. Inputs are
normalized observations, NOT proof of provenance. Native collector must
independently establish actual events, actor identity and loss-free capture.
"""
import signal

PIN = "6bac8be7b1de6883f480a95944d6ba1130852270"
KINDS = ("SYSCALL_ENTER", "UNUSE_ENTER", "SIGNAL_GENERATE",
         "UNUSE_RETURN", "SYSCALL_EXIT")

def classify(events, *, trace_complete, actor_verified, candidate_blob):
    def unknown(code):
        return {"state": "UNKNOWN", "code": code, "can_execute": False}
    if trace_complete is not True or actor_verified is not True:
        return unknown("TRACE_OR_ACTOR_UNVERIFIED")
    if candidate_blob != PIN:
        return unknown("CANDIDATE_MISMATCH")
    if type(events) is not list or len(events) != len(KINDS):
        return unknown("BOUNDARY_MISSING_OR_REPEATED")
    actor = None
    previous = -1
    for event, expected in zip(events, KINDS):
        if type(event) is not dict or set(event) != {"kind", "time_ns", "pid", "start_ticks", "value"}:
            return unknown("INVALID_EVENT")
        if event["kind"] != expected:
            return unknown("BOUNDARY_ORDER")
        if any(type(event[k]) is not int for k in ("time_ns", "pid", "start_ticks", "value")):
            return unknown("INVALID_EVENT")
        if event["time_ns"] <= previous or event["pid"] <= 0 or event["start_ticks"] <= 0:
            return unknown("INVALID_ORDER_OR_IDENTITY")
        current = (event["pid"], event["start_ticks"])
        if actor is not None and current != actor:
            return unknown("ACTOR_CHANGED")
        actor, previous = current, event["time_ns"]
    # Exact Linux x86_64 syscall number, observed function entry, and an
    # explicitly targeted SIGTERM generation. Do not substitute SIGKILL death
    # or a successful syscall followed by a signal for an interrupted return.
    if [e["value"] for e in events[:3]] != [168, 0, int(signal.SIGTERM)]:
        return unknown("UNEXPECTED_BOUNDARY")
    # Conservatively require EINTR at BOTH function return and syscall exit.
    # Kernel restart codes, no exit, success and other errors are UNKNOWN.
    if events[3]["value"] != -4 or events[4]["value"] != -4:
        return unknown("INTERRUPTED_RETURN_NOT_OBSERVED")
    return {"state": "INTERRUPTED_RETURN_OBSERVED", "code": "ORDERED_TRACE_CANDIDATE",
            "can_execute": False}
