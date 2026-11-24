#!/usr/bin/env python3
"""H4b: explicit AMD DRM client and device observation, not model attribution."""
import argparse
from contextlib import ExitStack
from dataclasses import dataclass
import json
import os
import re
import stat
import sys
import time

import cgroup_observation_i5 as I5
import runtime_membership_i6 as I6
import process_observation_i4 as I4

SCHEMA = "post-apollo.forest.heart-drm-client.h4b"
MAX_WINDOW_NS = 1_000_000_000
MAX_FD = 2**31 - 1
_BDF = re.compile(rb"[0-9a-f]{4}:[0-9a-f]{2}:[0-1][0-9a-f]\.[0-7]\Z")
_FIELDS = (b"drm-driver", b"drm-pdev", b"drm-client-id",
           b"drm-resident-vram", b"drm-memory-vram")
_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC


@dataclass(frozen=True, slots=True)
class Client:
    bdf: bytes
    client_id: int
    resident: int


def _memory(raw):
    fields = raw.split()
    if not 1 <= len(fields) <= 2:
        raise I5.CgroupRefusal("INVALID_DRM_MEMORY")
    scale = {b"KiB": 1024, b"MiB": 1024**2}
    multiplier = 1 if len(fields) == 1 else scale.get(fields[1])
    value = I5._number(fields[0])
    if multiplier is None or value > I5.MAX_NUMBER // multiplier:
        raise I5.CgroupRefusal("INVALID_DRM_MEMORY")
    return value * multiplier


def _parse(raw):
    if type(raw) is not bytes or len(raw) > I5.MAX_BYTES:
        raise I5.CgroupRefusal("INVALID_DRM_FDINFO")
    values = {}
    for line in raw.splitlines():
        key, sep, value = line.partition(b":")
        if key not in _FIELDS:
            continue
        if not sep or key in values:
            raise I5.CgroupRefusal("INVALID_DRM_FDINFO")
        values[key] = value.strip()
    if values.get(b"drm-driver") != b"amdgpu":
        raise I5.CgroupRefusal("UNSUPPORTED_DRM_DRIVER")
    bdf = values.get(b"drm-pdev", b"")
    if not _BDF.fullmatch(bdf) or b"drm-client-id" not in values:
        raise I5.CgroupRefusal("DRM_CLIENT_REFERENCE_UNAVAILABLE")
    client = I5._number(values[b"drm-client-id"])
    observations = [_memory(values[k]) for k in _FIELDS[3:] if k in values]
    if not observations:
        raise I5.CgroupRefusal("DRM_RESIDENCY_UNAVAILABLE")
    if len(set(observations)) != 1:
        raise I5.CgroupRefusal("DRM_RESIDENCY_ALIAS_MISMATCH")
    return Client(bdf, client, observations[0])


def _fd_reference(procfd, fd_number):
    # Follow only fixed procfs numeric magic link for metadata. Never open
    # the target device, duplicate its descriptor or issue GPU ioctls.
    info = os.stat("fd/" + str(fd_number), dir_fd=procfd)
    if not stat.S_ISCHR(info.st_mode) or os.major(info.st_rdev) != 226:
        raise I5.CgroupRefusal("NOT_DRM_DEVICE")
    return info.st_dev, info.st_ino, info.st_rdev


def _client(procfd, fd_number):
    fd = os.open("fdinfo/" + str(fd_number),
                 os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=procfd)
    try:
        return _parse(I5._read_fd(fd, I5.MAX_BYTES))
    finally:
        os.close(fd)


def _device_path(bdf):
    return "/sys/bus/pci/devices/" + bdf.decode("ascii")


def _device_identity(path):
    info = os.stat(path)
    if not stat.S_ISDIR(info.st_mode):
        raise I5.CgroupRefusal("DRM_DEVICE_SCOPE_UNAVAILABLE")
    return info.st_dev, info.st_ino


def _link_identity(ref):
    dev = ref[2]
    return _device_identity("/sys/dev/char/" + str(os.major(dev)) + ":" +
                            str(os.minor(dev)) + "/device")


def _counter(fd, name):
    if name not in ("mem_info_vram_total", "mem_info_vram_used"):
        raise I5.CgroupRefusal("INVALID_DRM_COUNTER")
    counter = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
    try:
        return I5._number(I5._read_fd(counter, 64).strip())
    finally:
        os.close(counter)


def _sample_device(fd):
    return _counter(fd, "mem_info_vram_total"), _counter(fd, "mem_info_vram_used")


def _summary(a, b, d1, d2):
    if (a.bdf, a.client_id) != (b.bdf, b.client_id):
        raise I5.CgroupRefusal("DRM_CLIENT_REFERENCE_CHANGED")
    total, used1 = d1
    total2, used2 = d2
    if total != total2 or total <= 0 or not 0 <= max(used1, used2) <= total:
        raise I5.CgroupRefusal("DRM_DEVICE_COUNTER_CHANGED_OR_INVALID")
    return {
        "selected_drm_client_count": 1,
        "client_resident_vram_sampled_max_bytes": max(a.resident, b.resident),
        "device_total_vram_reported_bytes": total,
        "device_used_vram_sampled_max_bytes": max(used1, used2),
        "device_headroom_hint_bytes": total - max(used1, used2),
    }


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "EXPLICIT_SAME_OWNER_AMDGPU_DRM_CLIENT",
        "provider_runtime_instance_verified": False,
        "model_binding_verified": False,
        "all_clients_observed": False,
        "physical_vram_deduplicated": False,
        "ollama_device_mapping_verified": False,
        "allocatable_vram_established": False,
        "resource_requirements_established": False,
        "resource_reserved": False,
        "safe_to_start_inference": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def observe(path, pid, fd_number):
    selected = I5._parts(path)
    I6._pids((pid,))
    if type(fd_number) is not int or not 0 <= fd_number <= MAX_FD:
        raise I5.CgroupRefusal("INVALID_DRM_FD_SELECTION")
    if sys.platform != "linux":
        raise I5.CgroupRefusal("LINUX_REQUIRED")
    uid = os.geteuid()
    try:
        started = time.monotonic_ns()
        boot, mount = I6._boot(), I5._mount()
        with ExitStack() as stack:
            groupfd = I5._open_group(selected)
            stack.callback(os.close, groupfd)
            groupid = I5._identity(groupfd)
            procfd = os.open("/proc/" + str(pid), _DIR | os.O_NOFOLLOW)
            stack.callback(os.close, procfd)
            member = I6._member(procfd, pid, selected, uid)
            ref = _fd_reference(procfd, fd_number)
            first = _client(procfd, fd_number)
            device_path = _device_path(first.bdf)
            devicefd = os.open(device_path, _DIR)
            stack.callback(os.close, devicefd)
            deviceid = I5._identity(devicefd)
            if _link_identity(ref) != deviceid:
                raise I5.CgroupRefusal("DRM_PCI_REFERENCE_MISMATCH")
            d1 = _sample_device(devicefd)
            second = _client(procfd, fd_number)
            d2 = _sample_device(devicefd)
            if (_fd_reference(procfd, fd_number) != ref
                    or _link_identity(ref) != deviceid
                    or _device_identity(device_path) != deviceid
                    or I6._member(procfd, pid, selected, uid) != member):
                raise I5.CgroupRefusal("DRM_SCOPE_CHANGED")
            for check, identity in (
                    (lambda: I5._open_group(selected), groupid),
                    (lambda: os.open("/proc/" + str(pid), _DIR | os.O_NOFOLLOW),
                     I5._identity(procfd))):
                fd = check()
                try:
                    if I5._identity(fd) != identity:
                        raise I5.CgroupRefusal("DRM_SCOPE_CHANGED")
                finally:
                    os.close(fd)
            if I6._boot() != boot or I5._mount() != mount:
                raise I5.CgroupRefusal("DRM_SCOPE_CHANGED")
            elapsed = time.monotonic_ns() - started
            if not 0 < elapsed <= MAX_WINDOW_NS:
                raise I5.CgroupRefusal("OBSERVATION_WINDOW_EXCEEDED")
            result = _summary(first, second, d1, d2)
    except (OSError, OverflowError, I4.ObservationRefusal):
        raise I5.CgroupRefusal("DRM_OBSERVATION_UNAVAILABLE") from None
    return {**_base(), "status": "OBSERVED", "elapsed_ns": elapsed, **result}


def main(argv=None):
    parser = argparse.ArgumentParser(description="H4b: read-only selected DRM client")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--cgroup", required=True)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--fd", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        result, code = observe(args.cgroup, args.pid, args.fd), 0
    except (I5.CgroupRefusal, I6.MembershipRefusal) as exc:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        result, code = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
