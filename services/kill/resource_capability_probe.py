#!/usr/bin/env python3
"""K8c: on-demand, read-only Linux resource capability observation.

This reports evidence, NOT authorization or successful actuation. It does not
open write handles, issue resource mutations, start persistent monitoring, or
infer per-process network attribution from a network namespace counter.
"""
import argparse
import errno
import json
import os
import resource
import sys

MAX_READ = 8192
CATEGORIES = ("cpu", "memory", "swap", "disk", "threads", "gpu", "network")
CGROUP_FILES = {
    "cpu": ("cpu.max", "cpu.weight", "cpuset.cpus.effective"),
    "memory": ("memory.max", "memory.high"),
    "swap": ("memory.swap.max",),
    "disk": ("io.max", "io.weight"),
    "threads": ("pids.max",),
}

def status(error):
    if isinstance(error, PermissionError):
        return "permission_denied"
    if isinstance(error, FileNotFoundError):
        return "missing"
    return "unavailable"

def bounded_read(path):
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_READ + 1)
        if len(data) > MAX_READ:
            return "oversize", None
        return "observed", data.decode("utf-8", "replace")
    except OSError as error:
        return status(error), None

def birth_identity(pid):
    state, raw = bounded_read(f"/proc/{pid}/stat")
    if state != "observed" or raw is None:
        return state, None
    try:
        end = raw.rindex(")")
        name = raw[raw.index("(") + 1:end]
        fields = raw[end + 2:].split()
        born = int(fields[19])
        if born <= 0 or fields[0] == "Z":
            return "stale", None
        return "observed", (name, born)
    except (ValueError, IndexError):
        return "invalid", None

def source_observation(path):
    result, _ = bounded_read(path)
    return result

def cgroup_directory(pid):
    state, body = bounded_read(f"/proc/{pid}/cgroup")
    if state != "observed":
        return state, None
    try:
        membership = next(line[3:] for line in body.splitlines() if line.startswith("0::"))
    except StopIteration:
        return "not_cgroup_v2", None
    root = os.path.realpath("/sys/fs/cgroup")
    if source_observation(os.path.join(root, "cgroup.controllers")) != "observed":
        return "not_cgroup_v2", None
    if not membership.startswith("/") or "\x00" in membership:
        return "invalid", None
    destination = os.path.realpath(os.path.join(root, membership.lstrip("/")))
    if not (destination == root or destination.startswith(root + os.sep)):
        return "invalid", None
    return "observed", destination

def drm_fdinfo(pid):
    directory = f"/proc/{pid}/fdinfo"
    try:
        names = os.listdir(directory)
    except OSError as error:
        return status(error)
    # Bounded scan: "not observed" is NOT evidence the process never uses GPU.
    for name in names[:64]:
        if not name.isdecimal():
            continue
        state, body = bounded_read(os.path.join(directory, name))
        if state == "observed" and any(line.startswith("drm-") for line in body.splitlines()):
            return "observed"
        if state == "permission_denied":
            return state
    return "not_observed"

def observe(pid, birth, comm):
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 1 or not isinstance(birth, int) or isinstance(birth, bool) or birth <= 0 or not isinstance(comm, str) or not comm:
        return {"schema":"post-apollo-kill-capability-k8c-v1","state":"invalid_target","resources":{}}
    first, identity = birth_identity(pid)
    if first != "observed" or identity != (comm, birth):
        return {"schema":"post-apollo-kill-capability-k8c-v1","state":"stale_or_unobservable","resources":{}}
    sources = {
        "cpu": {"process_stat":source_observation(f"/proc/{pid}/stat")},
        "memory": {"process_status":source_observation(f"/proc/{pid}/status")},
        "swap": {"process_status":source_observation(f"/proc/{pid}/status")},
        "disk": {"process_io":source_observation(f"/proc/{pid}/io")},
        "threads": {"process_status":source_observation(f"/proc/{pid}/status")},
        "gpu": {"drm_fdinfo":drm_fdinfo(pid)},
        "network": {"network_namespace":source_observation(f"/proc/{pid}/net/dev")},
    }
    try:
        os.getpriority(os.PRIO_PROCESS, pid)
        sources["cpu"]["priority_read"] = "observed"
    except (OSError, AttributeError) as error:
        sources["cpu"]["priority_read"] = status(error) if isinstance(error, OSError) else "unavailable"
    try:
        os.sched_getaffinity(pid)
        sources["cpu"]["affinity_read"] = "observed"
    except (OSError, AttributeError) as error:
        sources["cpu"]["affinity_read"] = status(error) if isinstance(error, OSError) else "unavailable"
    try:
        resource.prlimit(pid, resource.RLIMIT_AS)
        sources["memory"]["rlimit_as_read"] = "observed"
    except (OSError, AttributeError) as error:
        sources["memory"]["rlimit_as_read"] = status(error) if isinstance(error, OSError) else "unavailable"
    cstate, directory = cgroup_directory(pid)
    for group, names in CGROUP_FILES.items():
        sources[group]["cgroup_v2"] = cstate
        for name in names:
            sources[group][name] = source_observation(os.path.join(directory,name)) if directory else "unavailable"
    sources["gpu"]["per_process_gpu_control"] = "not_verified"
    sources["network"]["per_process_bandwidth_control"] = "not_verified"
    # A namespace-wide /proc/PID/net/dev counter is not per-process traffic.
    sources["network"]["per_process_attribution"] = "not_verified"
    last, identity_after = birth_identity(pid)
    if last != "observed" or identity_after != (comm, birth):
        return {"schema":"post-apollo-kill-capability-k8c-v1","state":"stale_during_observation","resources":{}}
    return {
        "schema":"post-apollo-kill-capability-k8c-v1",
        "state":"observed",
        "resources":{
            category:{
                "observation":sources[category],
                "actuation":"not_verified",
                "permission_to_change":"not_verified"
            } for category in CATEGORIES
        },
        "limits":{
            "no_syscall_mutations":True,
            "identity_is_not_atomic":True,
            "host_observation_is_not_authorization":True,
            "no_background_polling":True
        }
    }

def main():
    parser=argparse.ArgumentParser(description="On-demand read-only resource capability evidence")
    parser.add_argument("--pid",type=int,required=True)
    parser.add_argument("--start-ticks",type=int,required=True)
    parser.add_argument("--comm",required=True)
    args=parser.parse_args()
    result=observe(args.pid,args.start_ticks,args.comm)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    return 0 if result["state"]=="observed" else 2

if __name__ == "__main__":
    sys.exit(main())
