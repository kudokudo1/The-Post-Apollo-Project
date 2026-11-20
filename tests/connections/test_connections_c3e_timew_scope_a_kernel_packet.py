#!/usr/bin/env python3
"""Real Linux SCM_CREDENTIALS/pidfd test over fake TimeW Scope A packets."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import unittest
import uuid
from unittest.mock import patch

if (sys.platform != "linux" or os.environ.get("CI") != "true"
        or os.environ.get("GITHUB_ACTIONS") != "true"):
    raise SystemExit("C3E_TIMEW_SCOPE_A_PACKET_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_timew"))
import TimeWSelectedSurfacePacketPreflight as P


def ident():
    return str(uuid.uuid4())


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.challenge = b"C" * 32
        self.now = 1763658000000
        self.selection = {
            "schema": P.ScopeA.SCHEMA,
            "audience": P.ScopeA.AUDIENCE,
            "challenge_sha256": hashlib.sha256(self.challenge).hexdigest(),
            "selection_id": ident(),
            "compositor_epoch": ident(),
            "surface_lifetime_id": ident(),
            "surface_generation": 1,
            "live_con_id": 501,
            "app_id": "brave",
            "output": "DP-3",
            "workspace": "1",
            "floating": True,
            "fullscreen_mode": 0,
            "before_rect": {"x": 40, "y": 60, "width": 480, "height": 320},
            "target_rect": {"x": 80, "y": 120, "width": 600, "height": 440},
            "checkpoint_id": ident(),
            "window_key": ident(),
            "seat_id": "seat0",
            "session_id": ident(),
            "issued_ms": self.now,
            "expires_ms": self.now+1500,
        }

    def pair(self, *, creds=True, typ=socket.SOCK_SEQPACKET, timeout=.5):
        receiver, sender = socket.socketpair(socket.AF_UNIX, typ)
        receiver.settimeout(timeout)
        if creds:
            receiver.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
        self.addCleanup(receiver.close)
        self.addCleanup(sender.close)
        return receiver, sender

    def inspect(self, receiver, **replacements):
        options = {
            "receiver": receiver,
            "expected_uid": os.getuid(),
            "expected_challenge": self.challenge,
            "expected_selection": self.selection,
            "now_ms": self.now,
        }
        options.update(replacements)
        return P.inspect_kernel_sender_and_selection_ci_only(**options)

    def packet(self, *, selection=None, challenge=None):
        return P.make_packet_ci_only(
            selection=self.selection if selection is None else selection,
            challenge=self.challenge if challenge is None else challenge,
            now_ms=self.now)

    def denial(self, expected, data=None, **other):
        receiver, sender = self.pair()
        sender.send(self.packet() if data is None else data)
        with self.assertRaisesRegex(P.ObservationHold, expected):
            self.inspect(receiver, **other)

    def test_01_real_linux_sender_matches_but_never_authorizes(self):
        receiver, sender = self.pair()
        sender.send(self.packet())
        out = self.inspect(receiver)
        self.assertTrue(out["actualLinuxPacketSenderMatchesOriginalPeerInCI"])
        self.assertEqual(out["sourceOnlyPeerPid"], os.getpid())
        self.assertEqual(out["sourceOnlyPeerUid"], os.getuid())
        self.assertTrue(out["fixtureTimeWScopeASelectionDigestMatches"])
        self.assertEqual(out["status"], "ACTUAL_KERNEL_PACKET_SENDER_OBSERVED_NOT_SWAY_ORIGIN")
        for key in P.DENIED:
            self.assertIs(out[key], False, key)

    def test_02_unenrolled_kernel_uid_mismatch_refused(self):
        self.denial("ORIGINAL_PEER_DIFFERS_FROM_TEST_POLICY",
                    expected_uid=os.getuid()+1)

    def test_03_missing_per_packet_credentials_refused(self):
        receiver, sender = self.pair(creds=False)
        sender.send(self.packet())
        with self.assertRaisesRegex(P.ObservationHold,
                                    "PACKET_CREDENTIALS_NOT_ENABLED"):
            self.inspect(receiver)

    def test_04_stream_not_a_message_boundary_refused(self):
        receiver, sender = self.pair(typ=socket.SOCK_STREAM)
        sender.send(self.packet())
        with self.assertRaisesRegex(P.ObservationHold, "CI_RECEIVER_OR_UID_INVALID"):
            self.inspect(receiver)

    def test_05_indefinite_receiver_timeout_refused(self):
        receiver, sender = self.pair(timeout=None)
        sender.send(self.packet())
        with self.assertRaisesRegex(P.ObservationHold,
                                    "BOUNDED_SOCKET_TIMEOUT_REQUIRED"):
            self.inspect(receiver)

    def test_06_client_can_forge_selection_but_it_still_cannot_authorize(self):
        receiver, sender = self.pair()
        selection = copy.deepcopy(self.selection)
        selection.update(selection_id=ident(), surface_lifetime_id=ident(),
                         live_con_id=502, surface_generation=2)
        sender.send(self.packet(selection=selection))
        out = self.inspect(receiver, expected_selection=selection)
        self.assertTrue(out["fixtureTimeWScopeASelectionDigestMatches"])
        self.assertFalse(out["perSurfaceSelectionOriginAuthenticated"])
        self.assertFalse(out["compositorLifetimeAuthenticated"])
        self.assertFalse(out["canMoveWindow"])

    def test_07_two_same_app_windows_cannot_swap_claim(self):
        changed = copy.deepcopy(self.selection)
        changed["surface_lifetime_id"] = ident()
        changed["live_con_id"] = 502
        self.denial("PACKET_DIFFERS_FROM_EXPECTED_SCOPE_A",
                    expected_selection=changed)

    def test_08_changed_generation_or_seat_rejected(self):
        for changes in ({"surface_generation":2}, {"seat_id":"seat1"},
                        {"session_id":ident()}, {"compositor_epoch":ident()}):
            with self.subTest(changes=changes):
                self.denial("PACKET_DIFFERS_FROM_EXPECTED_SCOPE_A",
                            expected_selection={**self.selection,**changes})

    def test_09_changed_or_missing_challenge_refused(self):
        with self.assertRaisesRegex(P.ObservationHold, "TIMEW_CHALLENGE_DIGEST_CHANGED"):
            self.packet(challenge=b"D"*32)
        changed = dict(self.selection, challenge_sha256="b"*64)
        with self.assertRaisesRegex(P.ObservationHold, "TIMEW_CHALLENGE_DIGEST_CHANGED"):
            self.packet(selection=changed)

    def test_10_wrong_browser_pairing_schema_refused(self):
        changed = dict(self.selection,
                       schema="post-apollo.timew.external-window-pairing.v1")
        with self.assertRaisesRegex(P.ObservationHold, "WRONG_SCOPE_A_AUDIENCE"):
            self.packet(selection=changed)

    def test_11_unknown_protected_authority_field_refused(self):
        changed = dict(self.selection, browser_window_ref=ident())
        with self.assertRaisesRegex(P.ObservationHold, "TIMEW_SCOPE_A_FIELDS_REQUIRED"):
            self.packet(selection=changed)

    def test_12_stale_or_nonfloating_token_refused(self):
        for changes in (
            {"issued_ms":self.now-7000,"expires_ms":self.now-5000},
            {"floating":False}, {"fullscreen_mode":1},
            {"surface_generation":True}, {"live_con_id":-1}):
            with self.subTest(changes=changes):
                with self.assertRaises(P.ObservationHold):
                    self.packet(selection={**self.selection,**changes})

    def test_13_duplicate_packet_fields_rejected(self):
        raw=self.packet()
        self.denial("INVALID_PACKET_JSON",
                    data=raw[:-1]+b',"selectionId":"forged"}')

    def test_14_noncanonical_packet_rejected(self):
        self.denial("NONCANONICAL_PACKET_JSON",
                    data=json.dumps(json.loads(self.packet())).encode())

    def test_15_packet_claimed_authority_or_version_rejected(self):
        obj=json.loads(self.packet())
        obj["productionAuthority"]=True
        self.denial("UNRECOGNIZED_PACKET_FIELDS",data=P._canonical(obj))
        obj.pop("productionAuthority")
        obj["version"]=2
        self.denial("PACKET_DIFFERS_FROM_EXPECTED_SCOPE_A",
                    data=P._canonical(obj))

    def test_16_oversized_message_rejected(self):
        self.denial("PACKET_TRUNCATED_OVERSIZED_OR_BAD_ADDRESS",
                    data=b"X"*(P.MAX_PACKET+512))

    def test_17_inherited_socket_forked_child_packet_sender_rejected(self):
        receiver, sender = self.pair()
        child = os.fork()
        if child == 0:
            try:
                receiver.close()
                sender.send(self.packet())
                sender.close()
                os._exit(0)
            except (OSError, ValueError):
                os._exit(4)
        sender.close()
        try:
            with self.assertRaisesRegex(P.ObservationHold,
                                        "INHERITED_SOCKET_SENDER_OR_MISSING_CREDS"):
                self.inspect(receiver)
        finally:
            found, status = os.waitpid(child, 0)
            self.assertEqual(found, child)
            self.assertEqual(status, 0)

    def test_18_exited_or_invalid_peer_lease_refuses(self):
        receiver, sender = self.pair()
        sender.send(self.packet())
        with patch.object(P.Lease, "_pidfd_alive", return_value=False):
            with self.assertRaises(P.ObservationHold):
                self.inspect(receiver)

    def test_19_native_issuer_cannot_be_overridden(self):
        with self.assertRaisesRegex(P.ObservationHold,
                                    "REAL_SWAYPX_SELECTED_SURFACE_ISSUER_NOT_INSTALLED"):
            P.run_native_selected_surface_issuer(
                operatorApproved=True, c5ConsentVerified=True,
                canMoveWindow=True)

    def test_20_no_client_or_issuer_signing_custody(self):
        receiver, sender = self.pair()
        sender.send(self.packet())
        out=self.inspect(receiver)
        self.assertFalse(out["installedCompositorReleaseEnrolled"])
        self.assertFalse(out["selectionChallengeIndependentlyIssued"])
        self.assertFalse(out["c5TimeWOperatorConsentVerified"])
        self.assertFalse(out["productionAuthority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
