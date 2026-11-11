"""V2v actual read-only system-bus client contract, entirely mocked transport.

Uses actual Linux pidfds and real dbus-next message encoding types. Tests
NEVER connect to an OS bus or start/stop a real systemd unit. The live
source owner and ArchiveStore remain unconnected and deny-only.
"""
import asyncio
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from dbus_next import BusType, Message, MessageType, Variant

from scripts.trash.archive_v2_systemd_bus_readonly import (
    SystemdProbeRefused, read_only_systemd_unit_by_pidfd,
)

UNIT = "post-apollo-fixture.service"
OBJECT = "/org/freedesktop/systemd1/unit/post_2dapollo_2dfixture_2eservice"
INVOCATION = "a" * 32
CGROUP = "/system.slice/post-apollo-fixture.service"
FRAGMENT = "/opt/post-apollo/fixture.service"
OWNER = ":1.42"

EXPECTED = {
    "unitId": UNIT,
    "invocationId": INVOCATION,
    "controlGroup": CGROUP,
    "fragmentPath": FRAGMENT,
}


class SimulatedSystemBus:
    """Fake D-Bus response stream with real Message/Variant types."""

    def __init__(self, *, bus_type, negotiate_unix_fd, overrides=None):
        self.bus_type = bus_type
        self.negotiate_unix_fd = negotiate_unix_fd
        self.overrides = overrides or {}
        self.calls = []
        self.connected = False
        self.disconnected = False

    async def connect(self):
        self.connected = True
        return self

    def disconnect(self):
        self.disconnected = True

    async def call(self, msg):
        self.calls.append(msg)
        if self.overrides.get("timeout") == msg.member:
            await asyncio.sleep(20)
        if self.overrides.get("exception") == msg.member:
            raise OSError("synthetic bus unavailable")
        owner = self.overrides.get("owner", OWNER)
        if msg.member == "GetNameOwner":
            if len([x for x in self.calls if x.member == "GetNameOwner"]) > 1:
                owner = self.overrides.get("owner_after", owner)
            return self.reply("s", [owner], "org.freedesktop.DBus",
                              override_key="owner_reply")
        if msg.member == "GetConnectionUnixUser":
            return self.reply("u", [self.overrides.get("uid", 0)],
                              "org.freedesktop.DBus",
                              override_key="uid_reply")
        if msg.member == "GetConnectionUnixProcessID":
            return self.reply("u", [self.overrides.get("pid", 1)],
                              "org.freedesktop.DBus",
                              override_key="pid_reply")
        if msg.member == "GetUnitByPIDFD":
            return self.reply("osay", [
                self.overrides.get("object",OBJECT),
                self.overrides.get("unit",UNIT),
                bytes.fromhex(self.overrides.get("invocation",INVOCATION)),
            ], owner, override_key="unit_reply")
        if msg.member == "GetAll":
            properties = {
                "Id": Variant("s",self.overrides.get("prop_id",UNIT)),
                "ControlGroup": Variant("s",self.overrides.get("cgroup",CGROUP)),
                "FragmentPath": Variant("s",self.overrides.get("fragment",FRAGMENT)),
                "LoadState": Variant("s",self.overrides.get("load","loaded")),
                "ActiveState": Variant("s",self.overrides.get("active","active")),
            }
            if self.overrides.get("missing_id"):
                del properties["Id"]
            return self.reply("a{sv}",[properties],owner,
                              override_key="properties_reply")
        raise AssertionError("Unapproved D-Bus method: " + msg.member)

    def reply(self, signature, body, sender, override_key):
        override = self.overrides.get(override_key, {})
        return Message(
            message_type=override.get("type",MessageType.METHOD_RETURN),
            signature=override.get("signature",signature),
            body=override.get("body",body),
            sender=override.get("sender",sender),
        )


class V2vReadOnlySystemdBusTests(unittest.TestCase):
    def setUp(self):
        self.pidfd = os.pidfd_open(os.getpid(),0)
        self.addCleanup(os.close,self.pidfd)
        self.created = []

    def factory(self, overrides=None):
        def create(**kwargs):
            bus = SimulatedSystemBus(**kwargs,overrides=overrides)
            self.created.append(bus)
            return bus
        return create

    def probe(self, overrides=None, *, expected=None, fd=None):
        return asyncio.run(read_only_systemd_unit_by_pidfd(
            self.pidfd if fd is None else fd,
            EXPECTED if expected is None else expected,
            bus_factory=self.factory(overrides)))

    def test_read_only_query_authenticates_manager_connection_and_pidfd(self):
        result=self.probe()
        bus=self.created[-1]
        self.assertTrue(bus.connected)
        self.assertTrue(bus.disconnected)
        self.assertEqual(bus.bus_type,BusType.SYSTEM)
        self.assertTrue(bus.negotiate_unix_fd)
        self.assertEqual([m.member for m in bus.calls],[
            "GetNameOwner","GetConnectionUnixUser","GetConnectionUnixProcessID",
            "GetUnitByPIDFD","GetAll","GetNameOwner"])
        methods={m.member:m for m in bus.calls}
        unit_method=methods["GetUnitByPIDFD"]
        self.assertEqual(unit_method.destination,OWNER)
        self.assertEqual(unit_method.interface,
                         "org.freedesktop.systemd1.Manager")
        self.assertEqual(unit_method.signature,"h")
        self.assertEqual(unit_method.body,[0])
        self.assertEqual(unit_method.unix_fds,[self.pidfd])
        self.assertEqual(methods["GetAll"].destination,OWNER)
        self.assertEqual(methods["GetAll"].signature,"s")
        self.assertEqual(methods["GetAll"].body,
                         ["org.freedesktop.systemd1.Unit"])
        self.assertEqual(result["state"],"TEST_SYSTEMD_BUS_EVIDENCE_DENY_ONLY")
        self.assertEqual(len(result["managerEvidenceSha256"]),64)
        self.assertTrue(result["managerUidZeroPidOneChecked"])
        self.assertTrue(result["unitInvocationMatched"])
        self.assertTrue(result["pidfdSentViaUnixFd"])
        for flag in ("systemdUnitVerified","sourceServiceVerified",
                     "sourceAuthorityVerified","captureAllowed",
                     "productionAllowed","restoreAllowed","burnAllowed"):
            self.assertFalse(result[flag])

    def test_wrong_manager_uid_or_pid_one_refused(self):
        for fake in ({"uid":1000},{"pid":433},{"uid":0,"pid":0}):
            with self.subTest(fake=fake):
                with self.assertRaisesRegex(SystemdProbeRefused,
                                            "SYSTEMD_NOT_PID1"):
                    self.probe(fake)
                self.assertTrue(self.created[-1].disconnected)

    def test_bad_unique_owner_and_owner_change_refuse(self):
        for fake,code in (
            ({"owner":"org.freedesktop.systemd1"},"SYSTEMD_BUS_OWNER_INVALID"),
            ({"owner_after":":1.43"},"SYSTEMD_BUS_OWNER_CHANGED"),
            ({"owner_reply":{"sender":":1.55"}},"SYSTEMD_BUS_OWNER_INVALID"),
        ):
            with self.subTest(fake=fake):
                with self.assertRaisesRegex(SystemdProbeRefused,code):
                    self.probe(fake)

    def test_wrong_pidfd_sender_or_signature_refused(self):
        for fake in (
            {"unit_reply":{"sender":":1.78"}},
            {"unit_reply":{"signature":"s"}},
            {"unit_reply":{"type":MessageType.ERROR}},
        ):
            with self.subTest(fake=fake):
                with self.assertRaisesRegex(SystemdProbeRefused,
                                            "SYSTEMD_UNIT_REPLY_INVALID"):
                    self.probe(fake)

    def test_wrong_unit_invocation_object_and_properties_refuse(self):
        for fake,code in (
            ({"unit":"other.service"},"SYSTEMD_UNIT_MISMATCH"),
            ({"invocation":"b"*32},"SYSTEMD_UNIT_MISMATCH"),
            ({"object":"/org/freedesktop/systemd1/invalid"},
             "SYSTEMD_UNIT_REPLY_INVALID"),
            ({"prop_id":"other.service"},"SYSTEMD_UNIT_MISMATCH"),
            ({"cgroup":"/system.slice/another.service"},"SYSTEMD_UNIT_MISMATCH"),
            ({"fragment":"/tmp/unapproved.service"},"SYSTEMD_UNIT_MISMATCH"),
            ({"load":"not-found"},"SYSTEMD_UNIT_MISMATCH"),
            ({"active":"inactive"},"SYSTEMD_UNIT_MISMATCH"),
            ({"missing_id":True},"SYSTEMD_UNIT_PROPERTIES_INVALID"),
            ({"properties_reply":{"sender":":1.81"}},"SYSTEMD_UNIT_PROPERTIES_INVALID"),
        ):
            with self.subTest(fake=fake):
                with self.assertRaisesRegex(SystemdProbeRefused,code):
                    self.probe(fake)

    def test_invalid_fd_and_non_pidfd_are_refused_before_bus_connection(self):
        with self.assertRaisesRegex(SystemdProbeRefused,"SYSTEMD_PIDFD_REQUIRED"):
            self.probe(fd=-1)
        with open("/dev/null","rb") as handle:
            with self.assertRaisesRegex(SystemdProbeRefused,"SYSTEMD_PIDFD_REQUIRED"):
                self.probe(fd=handle.fileno())
        self.assertEqual(self.created,[])

    def test_expected_policy_and_extra_fields_are_strict(self):
        for policy in (
            {**EXPECTED,"ownerProvidedPid":12},
            {**EXPECTED,"invocationId":True},
            {**EXPECTED,"unitId":"other.socket"},
            {**EXPECTED,"controlGroup":"/../untrusted"},
            {**EXPECTED,"fragmentPath":"../untrusted.service"},
        ):
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(SystemdProbeRefused,
                                            "SYSTEMD_EXPECTED_POLICY_INVALID"):
                    self.probe(expected=policy)
        self.assertEqual(self.created,[])

    def test_system_bus_failure_and_timeout_refuse_without_production_fallback(self):
        for fake in ({"exception":"GetUnitByPIDFD"},
                     {"timeout":"GetUnitByPIDFD"}):
            with self.subTest(fake=fake):
                # Speed up the injected failure by patching TIMEOUT.
                with patch("scripts.trash.archive_v2_systemd_bus_readonly.TIMEOUT",
                           0.02):
                    with self.assertRaisesRegex(SystemdProbeRefused,
                                                "SYSTEMD_DBUS_CALL_REFUSED"):
                        self.probe(fake)
                self.assertTrue(self.created[-1].disconnected)

    def test_fake_bus_never_authorizes_archive_even_on_exact_match(self):
        result=self.probe()
        self.assertFalse(result["systemdUnitVerified"])
        self.assertFalse(result["captureAllowed"])
        self.assertFalse(result["productionAllowed"])
        self.assertFalse((Path("/mnt/data")/"trashpp-archive-v2.sqlite3").exists())
        for request in self.created[-1].calls:
            self.assertIn(request.member,{
                "GetNameOwner","GetConnectionUnixUser",
                "GetConnectionUnixProcessID","GetUnitByPIDFD","GetAll"})

    def test_module_has_no_live_broker_or_mutation_entrance(self):
        from scripts.trash import archive_v2_systemd_bus_readonly as module
        source=Path(module.__file__).read_text(encoding="utf8")
        self.assertNotIn("ArchiveStore(",source)
        self.assertNotIn("Ed25519PrivateKey",source)
        self.assertNotIn("Quickshell.dataDir",source)
        self.assertFalse(hasattr(module,"main"))
        self.assertFalse(hasattr(module,"serve_forever"))


if __name__=="__main__":
    unittest.main()
