"""Personal local PHONE pilot, opt-in / single-user OS boundary regression tests.

Uses synthetic BlueFerry records, fake status/device callbacks and a temporary
Unix socket. No real paired devices, user messages, contacts or audio touched.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import socket
import stat
import tempfile
from threading import Thread
import time
from unittest import TestCase, mock
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "phone"))
import PhonePersonalReadPilot as pilot  # noqa: E402

PROFILE = "123e4567-e89b-42d3-a456-426614174000"
OTHER = "223e4567-e89b-42d3-a456-426614174000"
OWNER = ":1.78"


def device(profile=PROFILE, state="BLUETOOTH_CONNECTED", **changes):
    value = {
        "schema": "post-apollo.phone.device-observation.v0",
        "execution": "READ_ONLY_DEVICE_OBSERVATION",
        "state": state, "profileId": profile,
        "bluetoothLink": "CONNECTED",
        "trustedPhoneLink": "UNVERIFIED",
        "contentAccessEnabled": False,
    }
    value.update(changes)
    return value


def threads():
    return [{
        "key": "address:phone:15550001111", "name": "Synthetic",
        "is_group": False, "reply_ready": False, "unread": False,
        "messages_truncated": False, "messages": [{
            "handle": "m1", "body": "FAKE PRIVATE CONTENT",
            "timestamp": "2026-11-06T12:00:00Z",
            "outgoing": False, "read": True, "sender": "",
        }],
    }]


def contacts():
    return {"total": 1, "offset": 0, "query": "",
            "contacts": [{
                "id": "card-1", "name": "Synthetic",
                "organization": "", "primary": "fake@example.invalid",
                "phone_count": 0, "email_count": 1, "has_photo": False,
            }]}


class FakeProvider:
    def __init__(self):
        self.owner_value = OWNER
        self.status_record = {
            "api_version": 2, "daemon": True, "phone_profile_id": PROFILE,
            "map": True, "pbap": True, "contact_card_epoch": 6,
            "contact_card_count": 1,
        }
        self.calls = []
        self.on_read = None

    def owner(self):
        self.calls.append("owner")
        return self.owner_value

    def status(self, owner):
        self.calls.append("status")
        return dict(self.status_record)

    def threads(self, owner):
        self.calls.append("threads")
        if self.on_read:
            self.on_read()
        return threads()

    def contact_cards(self, owner):
        self.calls.append("contacts")
        if self.on_read:
            self.on_read()
        return contacts()


class PersonalPilotTests(TestCase):
    def setUp(self):
        self.provider = FakeProvider()
        self.current_device = device()
        self.now = 400.0
        self.session = pilot.PersonalReadSession(
            profile=PROFILE, owner=OWNER,
            allowed=frozenset({"messages.read", "contacts.read"}),
            source=self.provider, observer=lambda: self.current_device,
            clock=lambda: self.now,
        )

    def request(self, op):
        return self.session.process({"schema": pilot.REQUEST_SCHEMA,
                                     "operation": op})

    def assert_public(self, value):
        self.assertEqual(value["schema"], pilot.SCHEMA)
        self.assertEqual(value["execution"], pilot.EXECUTION)
        self.assertEqual(value["ownerKind"], "PERSONAL")
        self.assertFalse(value["organizationAccess"])
        self.assertFalse(value["sendingEnabled"])

    def test_status_is_content_free_and_consent_is_bounded(self):
        reply = self.request("status")
        self.assert_public(reply)
        self.assertEqual(reply["state"], "PERSONAL_LOCAL_PILOT_ACTIVE")
        self.assertNotIn("FAKE PRIVATE", str(reply))
        self.assertNotIn(PROFILE, str(reply))
        self.assertEqual(reply["contextKey"], self.session.context)
        self.now += pilot.TTL_SECONDS + 1
        self.assertEqual(self.request("status")["state"], "NOT_ACTIVE")
        self.assertEqual(self.request("messages.read")["state"], "NOT_ACTIVE")

    def test_actual_p18c_read_port_is_used_without_sending(self):
        reply = self.request("messages.read")
        self.assert_public(reply)
        self.assertEqual(reply["state"], "SNAPSHOT")
        self.assertEqual(reply["operation"], "messages.read")
        self.assertEqual(reply["profileId"], PROFILE)
        self.assertEqual(reply["sequence"], 1)
        self.assertEqual(reply["projection"]["authorization"], "NOT_EVALUATED")
        self.assertEqual(reply["projection"]["messageSets"][0]["messages"][0]["body"],
                         "FAKE PRIVATE CONTENT")
        self.assertIn("threads", self.provider.calls)
        self.assertNotIn("contacts", self.provider.calls)
        repeated = self.request("messages.read")
        self.assertEqual(repeated["sequence"], 2)

    def test_contact_grant_stays_independent_of_messages(self):
        self.session.allowed = frozenset({"contacts.read"})
        denied = self.request("messages.read")
        self.assertEqual(denied["state"], "NOT_CONSENTED")
        self.assertNotIn("FAKE PRIVATE", str(denied))
        result = self.request("contacts.read")
        self.assertEqual(result["state"], "SNAPSHOT")
        self.assertEqual(result["projection"]["contacts"][0]["displayNameInProfile"],
                         "Synthetic")
        self.assertIn("contacts", self.provider.calls)
        self.assertNotIn("threads", self.provider.calls)

    def test_profile_or_provider_owner_change_blocks_read(self):
        self.current_device = device(profile=OTHER)
        self.assertEqual(self.request("messages.read")["state"], "NOT_ACTIVE")
        self.assertEqual(self.provider.calls.count("threads"), 0)
        self.current_device = device()
        self.provider.owner_value = ":1.91"
        self.assertEqual(self.request("messages.read")["state"], "NOT_ACTIVE")
        self.assertEqual(self.provider.calls.count("threads"), 0)

    def test_device_disconnect_during_read_discards_private_content(self):
        self.provider.on_read = lambda: setattr(
            self, "current_device", device(state="PAIRED_OFFLINE")
        )
        result = self.request("messages.read")
        self.assertEqual(result["state"], "READ_UNAVAILABLE")
        self.assertNotIn("FAKE PRIVATE", str(result))

    def test_provider_capability_drop_or_cache_epoch_change_blocks_read(self):
        self.provider.status_record["map"] = False
        self.assertEqual(self.request("messages.read")["state"], "READ_UNAVAILABLE")
        self.provider.status_record["map"] = True
        self.provider.status_record["pbap"] = False
        self.assertEqual(self.request("contacts.read")["state"], "READ_UNAVAILABLE")
        self.provider.status_record["pbap"] = True
        self.provider.status_record["contact_card_epoch"] = None
        self.assertEqual(self.request("contacts.read")["state"], "READ_UNAVAILABLE")

    def test_revoke_closes_session_and_rejects_all_subsequent_reads(self):
        self.assertEqual(self.request("revoke")["state"], "REVOKED")
        self.assertEqual(self.request("messages.read")["state"], "NOT_ACTIVE")
        self.assertNotIn("threads", self.provider.calls)

    def test_request_cannot_select_person_organization_device_or_line(self):
        for fields in (
            {"schema": pilot.REQUEST_SCHEMA, "operation": "messages.read",
             "organizationId": "other-org"},
            {"schema": pilot.REQUEST_SCHEMA, "operation": "messages.read",
             "profileId": OTHER},
            {"schema": pilot.REQUEST_SCHEMA, "operation": "messages.read",
             "ownerKind": "ORGANIZATION"},
            {"schema": pilot.REQUEST_SCHEMA, "operation": "messages.send"},
            {"schema": "spoof", "operation": "messages.read"},
            [],
        ):
            result = self.session.process(fields)
            self.assertEqual(result["state"], "REFUSED" if
                             isinstance(fields, dict) and set(fields) !=
                             {"schema", "operation"} or isinstance(fields, list)
                             else result["state"])
            self.assertNotEqual(result["state"], "SNAPSHOT")
        self.assertNotIn("threads", self.provider.calls)

    def test_non_tty_or_unconfirmed_start_never_probes_real_device(self):
        with mock.patch.object(pilot.sys.stdin, "isatty", return_value=False):
            with mock.patch.object(pilot, "observe_device") as probe:
                self.assertEqual(pilot.main(["--serve"]), 2)
                probe.assert_not_called()

    def test_open_consent_uses_fixed_terminal_command_and_no_auto_grant(self):
        with mock.patch.object(pilot.shutil, "which", return_value="/bin/foot"):
            with mock.patch.object(pilot.subprocess, "Popen") as spawn:
                with redirect_stdout(io.StringIO()) as output:
                    code = pilot.main(["--open-consent"])
                self.assertEqual(code, 0)
                launched = spawn.call_args.args[0]
                self.assertEqual(launched[0], "/bin/foot")
                self.assertEqual(launched[-1], "--serve")
                self.assertIn("CONSENT_TERMINAL_REQUESTED", output.getvalue())
                self.assertEqual(spawn.call_count, 1)

    def test_runtime_path_refuses_world_readable_base(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": root}):
                os.chmod(path, 0o755)
                with self.assertRaises(ValueError):
                    pilot._socket_path(create=True)
                os.chmod(path, 0o700)
                pilot._socket_path(create=True)
                info = (path / pilot.RUNTIME_SUBDIR).lstat()
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o700)

    def test_exact_typed_socket_request_and_revoke_end_to_end(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": root}):
                t = Thread(target=pilot._run_server,
                           args=(self.session,), daemon=True)
                t.start()
                path = Path(root) / pilot.RUNTIME_SUBDIR / pilot.SOCKET_FILE
                for _ in range(100):
                    if path.exists():
                        break
                    time.sleep(0.01)
                self.assertTrue(path.exists(), "test socket not started")
                self.assertEqual(stat.S_IMODE(path.lstat().st_mode), 0o600)
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(pilot._client("messages.read"), 0)
                msg = json.loads(out.getvalue())
                self.assertEqual(msg["state"], "SNAPSHOT")
                self.assertEqual(msg["projection"]["conversations"][0]["serviceId"],
                                 "blueferry")
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(pilot._client("revoke"), 0)
                self.assertEqual(json.loads(out.getvalue())["state"], "REVOKED")
                t.join(3)
                self.assertFalse(t.is_alive())
                self.assertFalse(path.exists())
                with redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(pilot._client("status"), 2)
                self.assertEqual(json.loads(out.getvalue())["state"], "NOT_ACTIVE")

    def test_insecure_socket_cannot_be_used_and_no_send_methods(self):
        source = (ROOT / "services/phone/PhonePersonalReadPilot.py").read_text()
        for forbidden in (
            "SendToThread(", "MarkThreadRead(", "GetContact(", "GetContactPhoto(",
            "SetPhoneAudioRoute(", "ClearHistory(", "Pair(", "StartService(",
            "session_bus.start_service_by_name(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("SO_PEERCRED", source)
        self.assertIn("os.O_", (ROOT / "services/phone/PhoneDeviceObservation.py").read_text())


if __name__ == "__main__":
    import unittest
    unittest.main()
