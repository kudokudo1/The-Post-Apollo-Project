#!/usr/bin/env python3
"""C3b CI-only OS service-origin consistency probe.

Reads an already running C2r fake GetStatus service in an offline Fedora guest.
Checks the D-Bus daemon's PID/UID, systemd MainPID, /proc, SELinux context,
and protected fixture paths agree. Never establishes production identity or
opens a credential/grant path. No OS mutation or API access.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys

NAME = "org.postapollo.ConnectionsStatus1"
UNIT = "postapollo-connections-status.service"
USER = "postapollo-connections"
HOST = "/usr/libexec/post-apollo/connections-status-host"
INTERPRETER = "/opt/postapollo-c2o-venv/bin/python3"
EXPECTED_CGROUP = "/system.slice/" + UNIT
UNIT_PATH = "/usr/lib/systemd/system/" + UNIT
POLICY = "/usr/share/dbus-1/system.d/" + NAME + ".conf"
FILES = (HOST, UNIT_PATH, POLICY)
# Every directory through which the OS reaches the fake executable, unit,
# D-Bus policy and Python launcher. No writable or symlinked ancestors.
PROTECTED_DIRS = (
    "/", "/usr", "/usr/libexec", "/usr/libexec/post-apollo",
    "/usr/lib", "/usr/lib/systemd", "/usr/lib/systemd/system",
    "/usr/share", "/usr/share/dbus-1", "/usr/share/dbus-1/system.d",
    "/opt", "/opt/postapollo-c2o-venv", "/opt/postapollo-c2o-venv/bin",
) 
# C4b's *signed* fake host has the original /opt shebang. Only the
# canonical Silverblue link inode below may differ from Fedora Cloud.
# The default mode's no-symlink directory list and exact argv are unchanged.
C4B_OPT_LINK = "var/opt"
C4B_OPT_REALPATH = "/var/opt"
C4B_OPT_REAL_DIRS = (
    "/", "/var", "/var/opt", "/var/opt/postapollo-c2o-venv",
    "/var/opt/postapollo-c2o-venv/bin",
)
KEYS = {
    "owner_first", "owner_last", "bus_pid", "bus_uid", "main_pid",
    "systemd_user", "systemd_active", "unit_fragment", "unit_cgroup",
    "proc_uids", "proc_args", "proc_cgroup", "proc_context",
    "proc_no_new_privs", "expected_uid", "selinux_mode",
    "kernel_enforcing", "protected_files", "protected_dirs",
}
DENIED_FLAGS = {
    "hostAuthenticated": False,
    "credentialPresent": False,
    "grantActive": False,
    "canApprove": False,
    "canUseApi": False,
}


def refusal(reason: str) -> dict:
    return {"status": reason, **DENIED_FLAGS}


def evaluate(evidence: object, *, c4b_opt: bool = False,
             opt_proof: object = None) -> dict:
    """Pure fail-closed projection. This NEVER authorizes production access."""
    if type(c4b_opt) is not bool or (not c4b_opt and opt_proof is not None):
        return refusal("C3B_INVALID_EVIDENCE")
    if c4b_opt and not _valid_opt_proof(opt_proof):
        return refusal("C3C_UNTRUSTED_C4B_OPT_LINK")
    if type(evidence) is not dict or set(evidence) != KEYS:
        return refusal("C3B_INVALID_EVIDENCE")
    e = evidence
    if not isinstance(e["owner_first"], str) or not re.fullmatch(
            r":[0-9]+(?:\.[0-9]+)+", e["owner_first"]):
        return refusal("C3B_INVALID_OWNER")
    if e["owner_last"] != e["owner_first"]:
        return refusal("C3B_OWNER_CHANGED")
    if (type(e["bus_pid"]) is not int or e["bus_pid"] <= 1 or
            type(e["main_pid"]) is not int or e["bus_pid"] != e["main_pid"]):
        return refusal("C3B_PID_MISMATCH")
    if (type(e["expected_uid"]) is not int or e["expected_uid"] <= 0 or
            type(e["bus_uid"]) is not int or
            e["bus_uid"] != e["expected_uid"] or
            type(e["proc_uids"]) is not list or len(e["proc_uids"]) != 4 or
            any(type(uid) is not int or uid != e["expected_uid"]
                for uid in e["proc_uids"])):
        return refusal("C3B_UID_MISMATCH")
    if (e["systemd_user"] != USER or e["systemd_active"] != "active" or
            e["unit_fragment"] != UNIT_PATH):
        return refusal("C3B_UNIT_MISMATCH")
    if (type(e["unit_cgroup"]) is not str or
            e["unit_cgroup"] != EXPECTED_CGROUP or
            e["proc_cgroup"] != EXPECTED_CGROUP):
        return refusal("C3B_CGROUP_MISMATCH")
    args = e["proc_args"]
    if (type(args) is not list or len(args) != 3 or
            type(args[0]) is not str or args[0] != INTERPRETER or
            args[1:] != [HOST, "--read-only"]):
        return refusal("C3B_COMMAND_MISMATCH")
    if (e["selinux_mode"] != "Enforcing" or e["kernel_enforcing"] != "1" or
            type(e["proc_context"]) is not str or
            not re.fullmatch(
                r"system_u:system_r:postapollo_connections_t:s[0-9]+",
                e["proc_context"]) or e["proc_no_new_privs"] is not True):
        return refusal("C3B_CONFINEMENT_MISMATCH")
    files = e["protected_files"]
    if type(files) is not dict or set(files) != set(FILES):
        return refusal("C3B_FILES_MISMATCH")
    for path in FILES:
        f = files[path]
        if (type(f) is not dict or set(f) != {"owner", "mode", "regular", "symlink"} or
                type(f["owner"]) is not int or f["owner"] != 0 or
                type(f["mode"]) is not int or f["mode"] & 0o022 or
                f["regular"] is not True or f["symlink"] is not False):
            return refusal("C3B_UNPROTECTED_FILE")
    dirs = e["protected_dirs"]
    if type(dirs) is not dict or set(dirs) != set(PROTECTED_DIRS):
        return refusal("C3C_DIRECTORIES_MISMATCH")
    for path in PROTECTED_DIRS:
        d = dirs[path]
        if c4b_opt and path == "/opt":
            link = opt_proof["before"]["link"]
            if (type(d) is not dict or
                    d != {key: link[key] for key in
                          ("owner", "mode", "directory", "symlink")}):
                return refusal("C3C_UNTRUSTED_C4B_OPT_LINK")
            continue
        if (type(d) is not dict or
                set(d) != {"owner", "mode", "directory", "symlink"} or
                type(d["owner"]) is not int or d["owner"] != 0 or
                type(d["mode"]) is not int or d["mode"] & 0o022 or
                d["directory"] is not True or d["symlink"] is not False):
            return refusal("C3C_UNPROTECTED_DIRECTORY")
    return refusal("C3B_OS_ORIGIN_COHERENT_TEST_ONLY")


def _show(prop: str) -> str:
    result = subprocess.run(
        ["systemctl", "show", "--value", "-p", prop, UNIT],
        check=True, capture_output=True, text=True, timeout=5,
    )
    return result.stdout.strip()


def _file_evidence(path: str) -> dict:
    info = os.lstat(path)
    return {
        "owner": info.st_uid,
        "mode": stat.S_IMODE(info.st_mode),
        "regular": stat.S_ISREG(info.st_mode),
        "symlink": stat.S_ISLNK(info.st_mode),
    }


def _directory_evidence(path: str) -> dict:
    info = os.lstat(path)  # Never follow a directory alias in our fake test tree.
    return {
        "owner": info.st_uid,
        "mode": stat.S_IMODE(info.st_mode),
        "directory": stat.S_ISDIR(info.st_mode),
        "symlink": stat.S_ISLNK(info.st_mode),
    }


def _proc_uids_and_nnp(pid: int) -> tuple[list[int], bool]:
    content = Path(f"/proc/{pid}/status").read_text()
    props = dict(line.split(":", 1) for line in content.splitlines() if ":" in line)
    return [int(s) for s in props["Uid"].split()], props["NoNewPrivs"].strip() == "1"


def normalize_kernel_context(raw: str) -> str:
    """Linux proc attr/current may carry trailing NUL(s), not context data."""
    return raw.rstrip("\x00\n") if type(raw) is str else ""


def _proc_cgroup(pid: int) -> str:
    entries = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
    unified = [x.split(":", 2)[2] for x in entries if x.startswith("0::")]
    if len(unified) != 1:
        raise ValueError("C3B_EXPECTED_UNIFIED_SYSTEMD_CGROUP")
    return unified[0]

    
def _opt_snapshot() -> dict:
    """Read genuine guest filesystem state, never D-Bus/client-supplied facts."""
    link = os.lstat("/opt")
    dirs = {}
    for path in C4B_OPT_REAL_DIRS:
        info = os.lstat(path)
        dirs[path] = {
            "owner": info.st_uid, "group": info.st_gid,
            "mode": stat.S_IMODE(info.st_mode),
            "directory": stat.S_ISDIR(info.st_mode),
            "symlink": stat.S_ISLNK(info.st_mode),
            "device": info.st_dev, "inode": info.st_ino,
        }
    return {
        "link": {
            "owner": link.st_uid, "group": link.st_gid,
            "mode": stat.S_IMODE(link.st_mode),
            "directory": stat.S_ISDIR(link.st_mode),
            "symlink": stat.S_ISLNK(link.st_mode),
            "target": os.readlink("/opt"),
            "resolved": os.path.realpath("/opt"),
            "device": link.st_dev, "inode": link.st_ino,
        },
        "dirs": dirs,
    }


def _valid_opt_snapshot(snapshot: object) -> bool:
    if type(snapshot) is not dict or set(snapshot) != {"link", "dirs"}:
        return False
    link, dirs = snapshot["link"], snapshot["dirs"]
    if type(link) is not dict or set(link) != {
            "owner", "group", "mode", "directory", "symlink",
            "target", "resolved", "device", "inode"}:
        return False
    if not (
            type(link["owner"]) is int and link["owner"] == 0 and
            type(link["group"]) is int and link["group"] == 0 and
            type(link["mode"]) is int and link["mode"] == 0o777 and
            link["directory"] is False and link["symlink"] is True and
            link["target"] == C4B_OPT_LINK and
            link["resolved"] == C4B_OPT_REALPATH and
            type(link["device"]) is int and link["device"] > 0 and
            type(link["inode"]) is int and link["inode"] > 0):
        return False
    if type(dirs) is not dict or set(dirs) != set(C4B_OPT_REAL_DIRS):
        return False
    for path in C4B_OPT_REAL_DIRS:
        d = dirs[path]
        if type(d) is not dict or set(d) != {
                "owner", "group", "mode", "directory", "symlink",
                "device", "inode"}:
            return False
        if not (
                type(d["owner"]) is int and d["owner"] == 0 and
                type(d["group"]) is int and d["group"] == 0 and
                type(d["mode"]) is int and 0 <= d["mode"] <= 0o7777 and
                not (d["mode"] & 0o022) and
                d["directory"] is True and d["symlink"] is False and
                type(d["device"]) is int and d["device"] > 0 and
                type(d["inode"]) is int and d["inode"] > 0):
            return False
    return True


def _valid_opt_proof(proof: object) -> bool:
    return (type(proof) is dict and set(proof) == {"before", "after"} and
            _valid_opt_snapshot(proof["before"]) and
            _valid_opt_snapshot(proof["after"]) and
            proof["before"] == proof["after"])


def _verified_c4b_opt_guest() -> bool:
    """CI selector must agree with independently observed offline VM facts."""
    if (os.geteuid() != 0 or
            os.environ.get("GITHUB_ACTIONS") != "true" or
            os.environ.get("POST_APOLLO_C3B_TEST_GUEST") != "1" or
            os.environ.get("POST_APOLLO_C4B_TEST_GUEST") != "1"):
        return False
    try:
        if (Path("/var/lib/c4b-runtime-ci-only").read_text().strip() !=
                "C4B_DISPOSABLE_VM_ONLY"):
            return False
        if not Path("/run/ostree-booted").exists():
            return False
        if not Path("/etc/fedora-release").read_text().startswith("Fedora release 44 "):
            return False
        if set(os.listdir("/sys/class/net")) != {"lo"}:
            return False
        ref = subprocess.run(
            ["ostree", "admin", "status"], check=True, capture_output=True,
            text=True, timeout=5,
        ).stdout
        if re.search(r"(?<![a-z0-9_/])fedora/44/x86_64/silverblue(?![a-z0-9_/-])",
                     ref.lower()) is None:
            return False
    except (OSError, ValueError, subprocess.SubprocessError):
        return False
    return True


async def _probe(*, c4b_opt: bool = False) -> tuple[dict, object]:
    # D-Bus is queried only via a private disposable Fedora VM's system bus.
    # The bus daemon reports ownership and Unix peer identity, not the service.
    from dbus_next import BusType, Message, MessageType
    from dbus_next.aio import MessageBus

    before = _opt_snapshot() if c4b_opt else None
    if c4b_opt and not _valid_opt_snapshot(before):
        raise ValueError("C3C_UNTRUSTED_C4B_OPT_LINK")
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        async def query(member: str, name: str):
            reply = await asyncio.wait_for(bus.call(Message(
                destination="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                interface="org.freedesktop.DBus",
                member=member,
                signature="s",
                body=[name],
            )), timeout=4)
            if reply.message_type != MessageType.METHOD_RETURN or len(reply.body) != 1:
                raise ValueError("C3B_DAEMON_QUERY_REFUSED_" + member)
            return reply.body[0]

        first = await query("GetNameOwner", NAME)
        if type(first) is not str or not re.fullmatch(r":[0-9]+(?:\.[0-9]+)+", first):
            raise ValueError("C3B_INVALID_DAEMON_OWNER")
        pid = await query("GetConnectionUnixProcessID", first)
        uid = await query("GetConnectionUnixUser", first)
        if type(pid) is not int or pid <= 1:
            raise ValueError("C3B_INVALID_DAEMON_PID")
        proc_uids, nnp = _proc_uids_and_nnp(pid)
        args = [s.decode("utf-8") for s in
                Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if s]
        expected_uid = pwd.getpwnam(USER).pw_uid
        e = {
            "owner_first": first,
            "bus_pid": pid,
            "bus_uid": uid,
            "main_pid": int(_show("MainPID")),
            "systemd_user": _show("User"),
            "systemd_active": _show("ActiveState"),
            "unit_fragment": _show("FragmentPath"),
            "unit_cgroup": _show("ControlGroup"),
            "proc_uids": proc_uids,
            "proc_args": args,
            "proc_cgroup": _proc_cgroup(pid),
            "proc_context": normalize_kernel_context(
                Path(f"/proc/{pid}/attr/current").read_text()),
            "proc_no_new_privs": nnp,
            "expected_uid": expected_uid,
            "selinux_mode": subprocess.run(
                ["getenforce"], check=True, capture_output=True,
                text=True, timeout=3,
            ).stdout.strip(),
            "kernel_enforcing": Path("/sys/fs/selinux/enforce").read_text().strip(),
            "protected_files": {path: _file_evidence(path) for path in FILES},
            "protected_dirs": {
                path: _directory_evidence(path) for path in PROTECTED_DIRS
            },
        }
        e["owner_last"] = await query("GetNameOwner", NAME)
        after = _opt_snapshot() if c4b_opt else None
        proof = {"before": before, "after": after} if c4b_opt else None
        if c4b_opt and not _valid_opt_proof(proof):
            raise ValueError("C3C_UNTRUSTED_C4B_OPT_LINK")
        return e, proof
    finally:
        bus.disconnect()


def main() -> int:
    args = sys.argv[1:]
    c4b_opt = args == ["--verify-disposable-silverblue-opt"]
    if (args not in (["--verify-disposable"], ["--verify-disposable-silverblue-opt"]) or
            os.environ.get("GITHUB_ACTIONS") != "true" or
            os.environ.get("POST_APOLLO_C3B_TEST_GUEST") != "1" or
            (c4b_opt and not _verified_c4b_opt_guest())):
        print("C3B_REFUSED_NOT_DISPOSABLE_GUEST")
        return 2
    try:
        evidence, opt_proof = asyncio.run(_probe(c4b_opt=c4b_opt))
        result = evaluate(evidence, c4b_opt=c4b_opt, opt_proof=opt_proof)
    except Exception as exc:
        print("C3B_FAIL // ORIGIN_EVIDENCE_UNAVAILABLE: " + type(exc).__name__)
        return 2
    if result["status"] != "C3B_OS_ORIGIN_COHERENT_TEST_ONLY":
        print("C3B_FAIL // " + result["status"])
        return 2
    assert all(value is False for key, value in result.items() if key != "status")
    print("C3B_PASS // OS_DBUS_PID_UID_SYSTEMD_SELINUX_ORIGIN_COHERENCE_TEST_ONLY")
    print("C3B_LIMITATION // NOT_AUTHENTICATED_PRODUCTION_OR_SIGNED_PROVENANCE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
