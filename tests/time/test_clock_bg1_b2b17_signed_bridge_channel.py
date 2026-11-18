"""Clock B2B17: signed AF_UNIX bridge challenge is not an alarm grant."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT/"tests/time/test_clock_bg1_b2b10_native_supervisor.py"
MODULE = ROOT/"services/time/AlarmNativeClockSupervisor.py"
QML = ROOT/"services/time/AlarmManagerService.qml"

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

Fixture = load(HARNESS, "clock_b2b17_real_signed_harness")
Supervisor = Fixture.Supervisor
Bridge = Supervisor.Bridge

CLIENT = r'''
import socket,sys
for frame in sys.stdin.buffer:
    peer=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    peer.connect(sys.argv[1])
    peer.sendall(frame)
    response=peer.makefile("rb").readline(4096)
    peer.close()
    sys.stdout.buffer.write(response)
    sys.stdout.buffer.flush()
'''

def frame(action, **fields):
    return (json.dumps(dict(v=1, action=action, **fields),
                       sort_keys=True, separators=(",", ":"))
            .encode("ascii") + b"\n")

def identity(pid=100):
    return (pid, 111, 5, "a"*64, 5, 1000)


class ClockBridgeLedgerTests(unittest.TestCase):
    def test_process_epoch_root_and_pidfd_identity_are_bound(self):
        for index in (0, 1, 2, 3, 4, 5):
            with self.subTest(field=index):
                item=list(identity())
                item[index]=("b"*64 if index == 3 else
                             (200 if index == 0 else item[index]+1))
                ledger=Bridge.ClockBridgeChallengeLedger()
                challenge=ledger.issue(identity())
                with self.assertRaisesRegex(Bridge.Refused,
                                             "CLOCK_BRIDGE_PEER_CHANGED"):
                    ledger.acknowledge(tuple(item),challenge)
                with self.assertRaisesRegex(Bridge.Refused,
                                             "CHALLENGE_NOT_PENDING"):
                    ledger.acknowledge(identity(),challenge)

    def test_unknown_or_bad_binding_cannot_issue(self):
        for bad in (None, [], (), (1,2,3), (0,111,5,"a"*64,5,1000),
                    (100,111,5,"A"*64,5,1000),
                    (True,111,5,"a"*64,5,1000)):
            with self.subTest(bad=bad):
                with self.assertRaises(Bridge.Refused):
                    Bridge.ClockBridgeChallengeLedger().issue(bad)

    def test_nonce_is_random_64_hex_and_single_issue(self):
        ledger=Bridge.ClockBridgeChallengeLedger()
        challenge=ledger.issue(identity())
        self.assertRegex(challenge, r"^[0-9a-f]{64}$")
        with self.assertRaisesRegex(Bridge.Refused, "ALREADY_ISSUED"):
            ledger.issue(identity())
        self.assertFalse(ledger.round_trip_observed)
        self.assertTrue(ledger.acknowledge(identity(),challenge))
        self.assertTrue(ledger.round_trip_observed)
        with self.assertRaisesRegex(Bridge.Refused, "NOT_PENDING"):
            ledger.acknowledge(identity(),challenge)

    def test_wrong_nonce_consumes_one_use_request(self):
        ledger=Bridge.ClockBridgeChallengeLedger()
        original=ledger.issue(identity())
        with self.assertRaisesRegex(Bridge.Refused, "CHALLENGE_MISMATCH"):
            ledger.acknowledge(identity(),"0"*64 if original!="0"*64 else "1"*64)
        with self.assertRaisesRegex(Bridge.Refused, "NOT_PENDING"):
            ledger.acknowledge(identity(),original)
        self.assertFalse(ledger.round_trip_observed)

    def test_expiry_is_closed_at_deadline_and_unrecoverable(self):
        ledger=Bridge.ClockBridgeChallengeLedger()
        with patch.object(Bridge.time, "monotonic", side_effect=[100.0, 120.0]):
            token=ledger.issue(identity())
            with self.assertRaisesRegex(Bridge.Refused, "CHALLENGE_EXPIRED"):
                ledger.acknowledge(identity(),token)
        with self.assertRaisesRegex(Bridge.Refused, "NOT_PENDING"):
            ledger.acknowledge(identity(),token)
        with self.assertRaisesRegex(Bridge.Refused, "ALREADY_ISSUED"):
            ledger.issue(identity())

    def test_shutdown_scrubs_pending_challenge(self):
        ledger=Bridge.ClockBridgeChallengeLedger()
        token=ledger.issue(identity())
        ledger.clear()
        with self.assertRaisesRegex(Bridge.Refused, "NOT_PENDING"):
            ledger.acknowledge(identity(),token)


class ClockNativeBridgeSocketTests(unittest.TestCase):
    def setUp(self):
        self.h=Fixture.ClockNativeSupervisorTests(
            methodName="test_real_af_unix_signed_client_is_only_observed_never_authorized")
        self.addCleanup(self.h.doCleanups)
        self.h.setUp()
        self.h.script.write_text(CLIENT, encoding="utf-8")
        self.h.script.chmod(0o600)

    def start(self, **kwargs):
        self.h.spawn(**kwargs)

    def exchange(self, packet):
        self.h.child.stdin.write(packet)
        self.h.child.stdin.flush()
        actual=self.h.server.serve_once(timeout=4.0)
        line=self.h.child.stdout.readline()
        self.assertTrue(line, "signed process did not receive socket reply")
        result=json.loads(line)
        self.assertEqual(actual,result)
        self.assertIs(result["ok"], False)
        for field in ("roleAuthenticated","writerStopped","releaseAcknowledged",
                      "ownsRealAlarmFile","canTransferOwnership","canRing",
                      "canNotify"):
            self.assertIs(result[field],False,field)
        return result

    def test_signed_same_process_real_socket_round_trip_is_only_observation(self):
        self.start()
        prepared=self.exchange(frame("PREPARE_BRIDGE_CHALLENGE"))
        self.assertTrue(prepared["originObserved"])
        self.assertTrue(prepared["channelChallengeIssued"])
        self.assertFalse(prepared["nativeToQmlChannelAuthenticated"])
        token=prepared["challenge"]
        self.assertRegex(token,r"^[0-9a-f]{64}$")
        confirmed=self.exchange(frame("ACK_BRIDGE_CHALLENGE",challenge=token))
        self.assertEqual(confirmed["reason"],
                         "BRIDGE_ROUND_TRIP_ONLY_NO_QML_AUTHORITY")
        self.assertTrue(confirmed["channelRoundTripObserved"])
        self.assertFalse(confirmed["quickshellDrainObserved"])
        self.assertFalse(confirmed["finalRevisionDurablyLocked"])
        self.assertFalse(confirmed["oldWriterRestartPrevented"])
        self.assertNotIn("challenge",confirmed)
        repeated=self.exchange(frame("ACK_BRIDGE_CHALLENGE",challenge=token))
        self.assertEqual(repeated["reason"],
                         "CLOCK_BRIDGE_CHALLENGE_NOT_PENDING")
        self.assertFalse(repeated["channelRoundTripObserved"])
        again=self.exchange(frame("PREPARE_BRIDGE_CHALLENGE"))
        self.assertEqual(again["reason"],
                         "CLOCK_BRIDGE_CHALLENGE_ALREADY_ISSUED")
        self.assertNotIn("challenge",again)

    def test_bad_token_invalidates_authentic_process_request(self):
        self.start()
        original=self.exchange(frame("PREPARE_BRIDGE_CHALLENGE"))["challenge"]
        wrong=("f" if original[0]!="f" else "e")+original[1:]
        denied=self.exchange(frame("ACK_BRIDGE_CHALLENGE",challenge=wrong))
        self.assertEqual(denied["reason"],"CLOCK_BRIDGE_CHALLENGE_MISMATCH")
        self.assertFalse(denied["channelRoundTripObserved"])
        refused=self.exchange(frame("ACK_BRIDGE_CHALLENGE",challenge=original))
        self.assertEqual(refused["reason"],"CLOCK_BRIDGE_CHALLENGE_NOT_PENDING")

    def test_unsigned_socket_peer_cannot_obtain_ticket(self):
        self.start(trusted=False)
        denied=self.exchange(frame("PREPARE_BRIDGE_CHALLENGE"))
        self.assertEqual(denied["reason"],"CLOCK_BRIDGE_SIGNED_PEER_REQUIRED")
        self.assertNotIn("challenge",denied)
        self.assertFalse(denied["originObserved"])

    def test_wrong_installed_signer_root_cannot_obtain_ticket(self):
        self.start(issuer_pin="f"*64)
        denied=self.exchange(frame("PREPARE_BRIDGE_CHALLENGE"))
        self.assertFalse(denied["channelChallengeIssued"])
        self.assertNotIn("challenge",denied)

    def test_only_canonical_minimal_request_fields_are_accepted(self):
        self.start()
        for packet in (
            frame("PREPARE_BRIDGE_CHALLENGE",path="/tmp/time-alarms-v2.json"),
            frame("PREPARE_BRIDGE_CHALLENGE",epoch=5),
            frame("ACK_BRIDGE_CHALLENGE",challenge="b"*64,writerStopped=True),
            frame("ACK_BRIDGE_CHALLENGE",challenge="invalid"),
            b'{"action":"PREPARE_BRIDGE_CHALLENGE","action":"PREPARE_BRIDGE_CHALLENGE","v":1}\n',
            b'{"v":1,"action":"PREPARE_BRIDGE_CHALLENGE"}\n',
        ):
            result=self.exchange(packet)
            self.assertFalse(result["originObserved"])
            self.assertNotIn("challenge",result)
        prepared=self.exchange(frame("PREPARE_BRIDGE_CHALLENGE"))
        self.assertTrue(prepared["channelChallengeIssued"])

    def test_protected_qml_drain_and_real_actuation_still_disabled(self):
        qml=QML.read_text(encoding="utf-8")
        self.assertIn('readonly property bool nativeWriterDrainBridgeInstalled: false',qml)
        self.assertIn('readonly property string alarmWriterBarrierPhase: "ACTIVE"',qml)
        self.assertIn('function requestAlarmWriterPause()',qml)
        self.assertIsNone(Supervisor.APPROVED_CLOCK_RELEASE_ROOT_SHA256)
        self.assertIsNone(Supervisor.APPROVED_CLOCK_FINAL_V2_SOURCE_PATH)
        self.start()
        for action in ("REQUEST_PAUSE","RELEASE_WRITER",
                       "TAKE_OWNERSHIP","RING_ALARM"):
            result=self.exchange(frame(action))
            self.assertEqual(result["reason"],
                             "NATIVE_WRITER_HANDOFF_NOT_AUTHORIZED")
        self.assertFalse(self.h.server._bridge_challenges.round_trip_observed)


if __name__ == "__main__":
    unittest.main()
