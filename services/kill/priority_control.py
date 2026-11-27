#!/usr/bin/env python3
"""K9a: identity-bound leader-thread nice primitive, not an authority issuer.

Only a future KillStore guarded caller may turn an operator review into a
request. This module does not provide a UI route, sudo, capability grant,
automatic retry, or process-group mutation. The numeric PID syscall is not
atomic with pidfd liveness/identity checks.
"""
import argparse
import json
import os
import resource
import select

from resource_capability_probe import birth_identity, bounded_read

SCHEMA = "post-apollo-kill-priority-v1"


def nice_value(value):
    return type(value) is int and -20 <= value <= 19


def reversible_range(original, current, requested, soft):
    # Linux's unprivileged priority-raise floor: 20 - RLIMIT_NICE.
    # A real permission/LSM decision remains with the kernel.
    return (all(nice_value(x) for x in (original, current, requested))
            and type(soft) is int and 1 <= soft <= 40
            and min(original, current, requested) >= 20 - soft)


def snapshot(pid, birth, comm, poll):
    def alive():
        if poll.poll(0):
            raise ValueError("original process exited")
        state, identity = birth_identity(pid)
        if state != "observed" or identity != (comm, birth) or poll.poll(0):
            raise ValueError("process identity changed")

    alive()
    uid = os.geteuid()
    if uid == 0 or uid != os.getuid():
        raise ValueError("privileged or mixed caller unsupported")
    state, body = bounded_read(f"/proc/{pid}/status")
    if state != "observed":
        raise ValueError("target credentials unavailable")
    uids = next((line.split()[1:] for line in body.splitlines()
                 if line.startswith("Uid:")), [])
    if uids != [str(uid)] * 4:
        raise ValueError("same-user target required")
    if os.readlink("/proc/self/ns/user") != os.readlink(f"/proc/{pid}/ns/user"):
        raise ValueError("same user namespace required")
    scheduler = os.sched_getscheduler(pid)
    if scheduler not in (os.SCHED_OTHER, os.SCHED_BATCH):
        raise ValueError("scheduler outside initial scope")
    current = os.getpriority(os.PRIO_PROCESS, pid)
    soft, hard = resource.prlimit(pid, resource.RLIMIT_NICE)
    if not nice_value(current):
        raise ValueError("invalid nice readback")
    alive()
    return {"nice": current, "soft": soft, "hard": hard,
            "scheduler": scheduler, "uid": uid}


def execute(req):
    reply = {"schema": SCHEMA, "state": "refused", "attempted": False}
    fd = None
    try:
        if not isinstance(req, dict):
            raise ValueError("invalid request")
        serial, pid, birth, comm, operation = (req.get(k) for k in
                                               ("serial", "pid", "startTicks", "comm", "operation"))
        if (type(serial) is not int or serial <= 0 or type(pid) is not int or pid <= 1
                or type(birth) is not int or birth <= 0 or not isinstance(comm, str)
                or not comm or operation not in ("capture", "apply", "restore")):
            raise ValueError("invalid identity or operation")
        reply.update(serial=serial, pid=pid, startTicks=birth, comm=comm, operation=operation)
        fd = os.pidfd_open(pid, 0)
        poll = select.poll()
        poll.register(fd, select.POLLIN)
        before = snapshot(pid, birth, comm, poll)
        reply["before"] = before
        if operation == "capture":
            reply["state"] = "observed"
            return reply

        original, expected, target, expected_soft = (req.get(k) for k in
                                ("original", "expected", "target", "expectedSoft"))
        if not all(nice_value(x) for x in (original, expected, target)):
            raise ValueError("invalid baseline or target")
        if operation == "restore" and target != original:
            raise ValueError("restore must use original value")
        if type(expected_soft) is not int or before["soft"] != expected_soft:
            raise ValueError("priority permission evidence changed")
        if before["nice"] != expected:
            raise ValueError("external nice change")
        if req.get("expectedSnapshot") != before:
            raise ValueError("captured priority evidence changed")
        if target == expected:
            reply.update(state="unchanged", after=before, original=original)
            return reply
        if not reversible_range(original, expected, target, before["soft"]):
            raise ValueError("reversible priority range not established")
        # Last complete check before the numeric-PID syscall. There remains
        # a race between this check and setpriority; never claim atomicity.
        if snapshot(pid, birth, comm, poll) != before:
            raise ValueError("priority evidence changed before mutation")
        reply["attempted"] = True
        os.setpriority(os.PRIO_PROCESS, pid, target)
        after = snapshot(pid, birth, comm, poll)
        if after != dict(before, nice=target):
            raise ValueError("priority readback or permission evidence changed")
        reply.update(state="restored" if operation == "restore" else "applied",
                     after=after, original=original)
    except (OSError, ValueError, TypeError, AttributeError, OverflowError) as exc:
        reply.update(state="unknown" if reply["attempted"] else "refused", error=str(exc))
    finally:
        if fd is not None:
            os.close(fd)
    return reply


def main():
    parser = argparse.ArgumentParser(description="Guarded leader-thread nice primitive")
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    try:
        request = json.loads(args.request)
    except ValueError:
        request = None
    print(json.dumps(execute(request), separators=(",", ":")))


if __name__ == "__main__":
    main()
