#!/usr/bin/env python3
"""V2v actual read-only system-bus GetUnitByPIDFD probe, never authority.

On supported Linux hosts with dbus-next installed, this opens ONLY the
system D-Bus, verifies the systemd1 well-known name is owned by a unique
connection whose bus credentials are uid 0 and PID 1, passes the original
pidfd via UNIX_FD, and reads Unit properties. The unique sender and
owner are rechecked. All failures refuse, with no numeric-PID fallback.

The injected bus_factory is test-only. Neither a real probe nor a test
result authorizes a source owner, ArchiveStore capture, Restore or Burn.
No bus controls, unit start/stop or local files are modified.
"""
import asyncio
import hashlib
import os
import re

BUS = "org.freedesktop.DBus"
BUS_PATH = "/org/freedesktop/DBus"
SYSTEMD_NAME = "org.freedesktop.systemd1"
SYSTEMD_PATH = "/org/freedesktop/systemd1"
SYSTEMD_IFACE = "org.freedesktop.systemd1.Manager"
PROPS = "org.freedesktop.DBus.Properties"
UNIT_IFACE = "org.freedesktop.systemd1.Unit"
UNIQUE = re.compile(r"^:[0-9]+[.][0-9]+(?:[.][0-9]+)*$")
UNIT = re.compile(r"^[A-Za-z0-9_@.:-]{1,120}[.]service$")
OBJECT = re.compile(r"^/org/freedesktop/systemd1/unit/[A-Za-z0-9_]{1,256}$")
CGROUP = re.compile(r"^/[A-Za-z0-9_.:@+/-]{0,2047}$")
TIMEOUT = 3.0


class SystemdProbeRefused(Exception):
    """Stable error code; never return a raw D-Bus exception or path."""


def _need(ok, code):
    if not ok:
        raise SystemdProbeRefused(code)


def _expected_policy(policy):
    expected = frozenset(("unitId","invocationId","controlGroup",
                          "fragmentPath"))
    _need(type(policy) is dict and set(policy) == expected,
          "SYSTEMD_EXPECTED_POLICY_INVALID")
    _need(type(policy["unitId"]) is str and UNIT.fullmatch(policy["unitId"])
          and type(policy["invocationId"]) is str
          and re.fullmatch(r"[0-9a-f]{32}",policy["invocationId"])
          and type(policy["controlGroup"]) is str
          and CGROUP.fullmatch(policy["controlGroup"])
          and ".." not in policy["controlGroup"].split("/")
          and "//" not in policy["controlGroup"]
          and type(policy["fragmentPath"]) is str
          and policy["fragmentPath"].startswith("/")
          and len(policy["fragmentPath"]) <= 4096
          and "\x00" not in policy["fragmentPath"],
          "SYSTEMD_EXPECTED_POLICY_INVALID")


def _pidfd_valid(pidfd):
    _need(type(pidfd) is int and pidfd >= 0,
          "SYSTEMD_PIDFD_REQUIRED")
    try:
        label = os.readlink(f"/proc/self/fd/{pidfd}")
        with open(f"/proc/self/fdinfo/{pidfd}", "r",
                  encoding="ascii") as handle:
            metadata = handle.read(2048)
    except (OSError, UnicodeError) as exc:
        raise SystemdProbeRefused("SYSTEMD_PIDFD_REQUIRED") from exc
    _need(label == "anon_inode:[pidfd]"
          and any(x.startswith("Pid:\t") and
                  x[5:].strip().isdigit() and
                  int(x[5:].strip()) > 0
                  for x in metadata.splitlines()),
          "SYSTEMD_PIDFD_REQUIRED")


def _single(reply, signature, sender, kind):
    from dbus_next import MessageType
    _need(reply is not None
          and reply.message_type == MessageType.METHOD_RETURN
          and reply.signature == signature
          and reply.sender == sender
          and type(reply.body) is list
          and len(reply.body) == 1,
          kind)
    return reply.body[0]


async def _call(bus, message, *, fail):
    try:
        return await asyncio.wait_for(bus.call(message), TIMEOUT)
    except (asyncio.TimeoutError, OSError, Exception) as exc:
        raise SystemdProbeRefused(fail) from exc


async def read_only_systemd_unit_by_pidfd(
    pidfd, expected_policy, *, bus_factory=None,
):
    """Query an authenticated system-bus PID 1, but never grant capture.

    The application must independently supply expected policy. Passing a
    test bus_factory only exercises wire-contract checking, never serves
    as proof of authenticated origin.
    """
    _expected_policy(expected_policy)
    _pidfd_valid(pidfd)
    try:
        from dbus_next import Message, BusType, MessageType
        from dbus_next.aio import MessageBus
    except ImportError as exc:
        raise SystemdProbeRefused("SYSTEMD_DBUS_DEPENDENCY_MISSING") from exc
    using_test_bus = bus_factory is not None
    if using_test_bus:
        _need(callable(bus_factory), "SYSTEMD_TEST_BUS_INVALID")
    else:
        bus_factory = MessageBus
    try:
        bus = await asyncio.wait_for(
            bus_factory(bus_type=BusType.SYSTEM, negotiate_unix_fd=True)
            .connect(), TIMEOUT)
    except (Exception,) as exc:
        raise SystemdProbeRefused("SYSTEMD_BUS_UNAVAILABLE") from exc
    try:
        async def request(destination, path, interface, member,
                          signature="", body=None, unix_fds=None):
            if body is None:
                body = []
            if unix_fds is None:
                unix_fds = []
            # The only allowed call targets are D-Bus's identity authority
            # and the single uniquely resolved PID 1 systemd peer.
            _need(destination == BUS or
                  (type(destination) is str and UNIQUE.fullmatch(destination)),
                  "SYSTEMD_BUS_TARGET_REFUSED")
            msg = Message(destination=destination, path=path,
                          interface=interface, member=member,
                          signature=signature, body=body, unix_fds=unix_fds)
            return await _call(bus,msg,fail="SYSTEMD_DBUS_CALL_REFUSED")

        async def owner_lookup():
            r = await request(BUS,BUS_PATH,BUS,"GetNameOwner","s",
                              [SYSTEMD_NAME])
            owner = _single(r,"s",BUS,"SYSTEMD_BUS_OWNER_INVALID")
            _need(type(owner) is str and UNIQUE.fullmatch(owner),
                  "SYSTEMD_BUS_OWNER_INVALID")
            return owner

        owner = await owner_lookup()
        uid_reply = await request(BUS,BUS_PATH,BUS,
                                  "GetConnectionUnixUser","s",[owner])
        uid = _single(uid_reply,"u",BUS,"SYSTEMD_BUS_IDENTITY_INVALID")
        pid_reply = await request(BUS,BUS_PATH,BUS,
                                  "GetConnectionUnixProcessID","s",[owner])
        pid = _single(pid_reply,"u",BUS,"SYSTEMD_BUS_IDENTITY_INVALID")
        _need(type(uid) is int and uid == 0 and type(pid) is int and pid == 1,
              "SYSTEMD_NOT_PID1")
        # The Unix FD is sent by index 0 in the D-Bus 'h' argument. The
        # original PIDFD remains owned by the caller and is not closed here.
        _pidfd_valid(pidfd)
        unit_reply = await request(owner,SYSTEMD_PATH,SYSTEMD_IFACE,
                                   "GetUnitByPIDFD","h",[0],[pidfd])
        _need(unit_reply.message_type == MessageType.METHOD_RETURN
              and unit_reply.signature == "osay"
              and unit_reply.sender == owner
              and type(unit_reply.body) is list
              and len(unit_reply.body) == 3,
              "SYSTEMD_UNIT_REPLY_INVALID")
        obj, unit_id, invocation = unit_reply.body
        _need(type(obj) is str and OBJECT.fullmatch(obj)
              and type(unit_id) is str and UNIT.fullmatch(unit_id)
              and type(invocation) in (bytes, bytearray, list)
              and len(invocation) == 16
              and all(type(b) is int and 0 <= b <= 255
                      for b in invocation),
              "SYSTEMD_UNIT_REPLY_INVALID")
        inv_hex = bytes(invocation).hex()
        props_reply = await request(owner,obj,PROPS,"GetAll","s",[UNIT_IFACE])
        props = _single(props_reply,"a{sv}",owner,
                        "SYSTEMD_UNIT_PROPERTIES_INVALID")
        _need(type(props) is dict, "SYSTEMD_UNIT_PROPERTIES_INVALID")

        def value(key):
            _need(key in props
                  and getattr(props[key],"signature",None) == "s"
                  and type(getattr(props[key],"value",None)) is str,
                  "SYSTEMD_UNIT_PROPERTIES_INVALID")
            return props[key].value

        named = {k:value(k) for k in (
            "Id","ControlGroup","FragmentPath","LoadState","ActiveState")}
        _need(named["Id"] == unit_id
              and named["Id"] == expected_policy["unitId"]
              and inv_hex == expected_policy["invocationId"]
              and named["ControlGroup"] == expected_policy["controlGroup"]
              and named["FragmentPath"] == expected_policy["fragmentPath"]
              and named["LoadState"] == "loaded"
              and named["ActiveState"] == "active",
              "SYSTEMD_UNIT_MISMATCH")
        _need((await owner_lookup()) == owner,
              "SYSTEMD_BUS_OWNER_CHANGED")
        _pidfd_valid(pidfd)
        evidence = (
            f"{owner}\n{unit_id}\n{inv_hex}\n{obj}\n"
            f"{named['ControlGroup']}\n{named['FragmentPath']}"
        ).encode("ascii")
        return {
            "state":"SYSTEMD_READ_ONLY_EVIDENCE_DENY_ONLY"
                     if not using_test_bus
                     else "TEST_SYSTEMD_BUS_EVIDENCE_DENY_ONLY",
            "managerEvidenceSha256":hashlib.sha256(evidence).hexdigest(),
            "managerUniqueOwnerChecked":True,
            "managerUidZeroPidOneChecked":True,
            "pidfdSentViaUnixFd":True,
            "unitInvocationMatched":True,
            "systemdUnitVerified":False,
            "sourceServiceVerified":False,
            "sourceAuthorityVerified":False,
            "captureAllowed":False,"productionAllowed":False,
            "restoreAllowed":False,"burnAllowed":False,
        }
    except SystemdProbeRefused:
        raise
    except Exception as exc:
        raise SystemdProbeRefused("SYSTEMD_READ_ONLY_REFUSED") from exc
    finally:
        try:
            bus.disconnect()
        except Exception:
            pass
