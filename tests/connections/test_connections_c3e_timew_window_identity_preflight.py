#!/usr/bin/env python3
"""TimeW signed live-window fixture identity, fail-closed adversarial CI."""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
import sys
import unittest
import uuid

if (sys.platform != "linux" or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("CI") != "true"):
    raise SystemExit("C3E_TIMEW_WINDOW_GITHUB_CI_ONLY")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/connections/c3e_timew"))
import TimeWBraveSwayIdentityPreflight as W
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def encoded(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def uid():
    return str(uuid.uuid4())


class TimeWWindowIdentityTests(unittest.TestCase):
    def setUp(self):
        self.signer = Ed25519PrivateKey.generate()
        self.session = uid()
        self.pair = {
            "schema": W.TimeW.PAIR_SCHEMA, "audience": W.TimeW.AUDIENCE,
            "pair_id": uid(), "checkpoint_id": uid(), "window_key": uid(),
            "live_con_id": 110, "app_id": "brave-browser",
            "workspace": "3", "output": "DP-1", "session_id": self.session,
            "browser_window_ref": uid(),
            "issued_ms": 1_000_000, "expires_ms": 1_009_000,
        }
        self.re_sign()
        self.selected = {
            **{k:self.pair[k] for k in W.PAIR_SCOPE},
            "pid": 4001, "start_ticks": 8151, "uid": 1000, "gid": 1000,
            "exe_sha256": "a"*64, "snapshot_generation": 25,
            "selected_at_ms": 1_000_400,
        }
        self.proc = {
            "pid": 4001, "start_ticks": 8151, "uid": 1000, "gid": 1000,
            "exe_sha256": "a"*64, "session_id": self.session,
            "alive": True,
        }
        self.live = {
            "con_id": 110, "pid": 4001, "app_id": "brave-browser",
            "workspace": "3", "output": "DP-1", "session_id": self.session,
            "floating": True, "snapshot_generation": 25,
        }
        self.params = {
            "signed_pairing": self.signed,
            "pairing_public_key": self.signer.public_key(),
            "separately_expected_pairing_key_sha256": W.hashlib.sha256(
                self.signer.public_key().public_bytes(
                    W.Encoding.Raw, W.PublicFormat.Raw)).hexdigest(),
            "selected_window": self.selected,
            "process_snapshot": self.proc,
            "compositor_windows": [self.live],
            "observed_at_ms": 1_000_500,
        }

    def re_sign(self):
        self.signed = {
            "payload": dict(self.pair),
            "signature": encoded(self.signer.sign(
                W.TimeW.PAIR_DOMAIN + W.TimeW._json(self.pair))),
        }
        if hasattr(self, "params"):
            self.params["signed_pairing"] = self.signed

    def call(self, **changes):
        return W.inspect_live_pairing_ci_only(**{**self.params, **changes})

    def refuse(self, reason, **changes):
        with self.assertRaisesRegex(W.Refused, reason):
            self.call(**changes)

    def test_01_timew_original_pair_schema_and_ci_grants_false(self):
        r = self.call()
        self.assertEqual(r["status"], W.STATUS)
        self.assertEqual(r["observedConIdInCI"], 110)
        self.assertEqual(r["pairPayloadSha256"], hashlib.sha256(
            W.TimeW._json(self.pair)).hexdigest())
        for key in W.DENIED:
            self.assertIs(r[key], False, key)

    def test_02_substituted_public_root_pin_refused(self):
        self.refuse("SUBSTITUTED_PAIRING_KEY",
                    separately_expected_pairing_key_sha256="f"*64)

    def test_03_wrong_public_root_refused(self):
        self.refuse("SUBSTITUTED_PAIRING_KEY",
                    pairing_public_key=Ed25519PrivateKey.generate().public_key())

    def test_04_unsigned_pair_change_refused(self):
        tampered={"payload":dict(self.pair,live_con_id=111),
                  "signature":self.signed["signature"]}
        self.refuse("TIMEW_PAIR_SIGNATURE_REFUSED",signed_pairing=tampered)

    def test_05_signed_wrong_timew_audience_refused(self):
        self.pair["audience"]="post-apollo.hospital.room-trash.v1"
        self.re_sign()
        self.refuse("WRONG_TIMEW_PAIR_SCHEMA_OR_AUDIENCE")

    def test_06_signed_extra_grant_field_refused(self):
        self.pair["productionAuthority"]=True
        self.re_sign()
        self.refuse("WRONG_TIMEW_PAIR_SCHEMA_OR_AUDIENCE")

    def test_07_signed_checkpoint_swap_refused(self):
        self.pair["checkpoint_id"]=uid()
        self.re_sign()
        self.refuse("SIGNED_PAIR_SELECTION_DRIFT")

    def test_08_signed_window_key_swap_refused(self):
        self.pair["window_key"]=uid()
        self.re_sign()
        self.refuse("SIGNED_PAIR_SELECTION_DRIFT")

    def test_09_signed_app_id_swap_refused(self):
        self.pair["app_id"]="kitty"
        self.re_sign()
        self.refuse("SIGNED_PAIR_SELECTION_DRIFT")

    def test_10_signed_session_swap_refused(self):
        self.pair["session_id"]=uid()
        self.re_sign()
        self.refuse("SIGNED_PAIR_SELECTION_DRIFT")

    def test_11_signed_container_id_swap_refused(self):
        self.pair["live_con_id"]=111
        self.re_sign()
        self.refuse("SIGNED_PAIR_SELECTION_DRIFT")

    def test_12_signed_browser_ref_swap_refused(self):
        self.pair["browser_window_ref"]=uid()
        self.re_sign()
        self.refuse("SIGNED_PAIR_SELECTION_DRIFT")

    def test_13_expired_or_future_pair_refused(self):
        late=dict(self.selected,selected_at_ms=1_009_950)
        early=dict(self.selected,selected_at_ms=999_900)
        self.refuse("EXPIRED_OR_FUTURE_PAIRING",
                    selected_window=late,observed_at_ms=1_010_000)
        self.refuse("EXPIRED_OR_FUTURE_PAIRING",
                    selected_window=early,observed_at_ms=999_999)

    def test_14_stale_selection_refused(self):
        self.refuse("STALE_SELECTION",observed_at_ms=1_002_001)
        self.refuse("STALE_SELECTION",observed_at_ms=1_000_399)

    def test_15_bool_container_id_not_int(self):
        self.pair["live_con_id"]=True
        self.re_sign()
        self.refuse("INVALID_CONTAINER_ID")

    def test_16_duplicate_con_id_refused(self):
        self.refuse("DUPLICATE_OR_INVALID_COMPOSITOR_WINDOW",
                    compositor_windows=[self.live,dict(self.live)])

    def test_17_two_brave_windows_one_process_are_ambiguous(self):
        other=dict(self.live,con_id=111,snapshot_generation=26)
        self.refuse("AMBIGUOUS_BRAVE_WINDOWS_SAME_PROCESS",
                    compositor_windows=[self.live,other])

    def test_18_other_unrelated_process_is_not_ambiguous(self):
        other=dict(self.live,con_id=111,pid=4002,snapshot_generation=26)
        out=self.call(compositor_windows=[self.live,other])
        self.assertIs(out["braveWindowInstanceAuthenticated"],False)

    def test_19_reused_container_generation_refused(self):
        stale=dict(self.live,snapshot_generation=26)
        self.refuse("REUSED_CONTAINER_OR_SCOPE_DRIFT",
                    compositor_windows=[stale])

    def test_20_reused_pid_start_tick_refused(self):
        self.refuse("STALE_OR_REUSED_PROCESS_IDENTITY",
                    process_snapshot=dict(self.proc,start_ticks=8152))

    def test_21_reused_pid_number_refused(self):
        self.refuse("STALE_OR_REUSED_PROCESS_IDENTITY",
                    process_snapshot=dict(self.proc,pid=4002))

    def test_22_changed_executable_hash_refused(self):
        self.refuse("STALE_OR_REUSED_PROCESS_IDENTITY",
                    process_snapshot=dict(self.proc,exe_sha256="f"*64))

    def test_23_changed_uid_gid_refused(self):
        self.refuse("STALE_OR_REUSED_PROCESS_IDENTITY",
                    process_snapshot=dict(self.proc,uid=0))
        self.refuse("STALE_OR_REUSED_PROCESS_IDENTITY",
                    process_snapshot=dict(self.proc,gid=0))

    def test_24_dead_process_refused(self):
        self.refuse("DEAD_OR_UNVERIFIED_PROCESS",
                    process_snapshot=dict(self.proc,alive=False))

    def test_25_swapped_compositor_session_refused(self):
        self.refuse("REUSED_CONTAINER_OR_SCOPE_DRIFT",
                    compositor_windows=[dict(self.live,session_id=uid())])

    def test_26_moved_output_workspace_refused(self):
        self.refuse("REUSED_CONTAINER_OR_SCOPE_DRIFT",
                    compositor_windows=[dict(self.live,output="HDMI-A-1")])
        self.refuse("REUSED_CONTAINER_OR_SCOPE_DRIFT",
                    compositor_windows=[dict(self.live,workspace="9")])

    def test_27_tiled_window_refused(self):
        self.refuse("REUSED_CONTAINER_OR_SCOPE_DRIFT",
                    compositor_windows=[dict(self.live,floating=False)])

    def test_28_missing_live_conid_refused(self):
        self.refuse("NO_EXACT_LIVE_CONTAINER",
                    compositor_windows=[dict(self.live,con_id=222,pid=5000)])

    def test_29_missing_or_extra_snapshot_fields_refused(self):
        self.refuse("MISSING_OR_EXTRA_OBSERVATION_FIELDS",
                    selected_window={k:v for k,v in self.selected.items() if k!="uid"})
        self.refuse("MISSING_OR_EXTRA_OBSERVATION_FIELDS",
                    process_snapshot=dict(self.proc,operatorApproved=True))
        self.refuse("MALFORMED_COMPOSITOR_WINDOW",
                    compositor_windows=[dict(self.live,granted=True)])

    def test_30_unbounded_compositor_list_refused(self):
        self.refuse("UNBOUNDED_COMPOSITOR_SNAPSHOT",
                    compositor_windows=[])
        self.refuse("UNBOUNDED_COMPOSITOR_SNAPSHOT",
                    compositor_windows=[self.live]*33)

    def test_31_invalid_signed_pairing_field_refused(self):
        self.pair["session_id"]="not-a-uuid"
        self.re_sign()
        self.refuse("INVALID_UUID")

    def test_32_selected_or_snapshot_bool_pid_refused(self):
        self.refuse("INVALID_SELECTED_PROCESS_OR_GENERATION",
                    selected_window=dict(self.selected,pid=True))
        self.refuse("STALE_OR_REUSED_PROCESS_IDENTITY",
                    process_snapshot=dict(self.proc,pid=True))

    def test_33_self_selected_new_root_is_only_format_positive(self):
        other=Ed25519PrivateKey.generate()
        self.signer=other
        self.re_sign()
        new_pin=hashlib.sha256(other.public_key().public_bytes(
            W.Encoding.Raw,W.PublicFormat.Raw)).hexdigest()
        out=self.call(pairing_public_key=other.public_key(),
                      separately_expected_pairing_key_sha256=new_pin)
        self.assertTrue(out["testOnlyTimeWPairSignatureMatchesCallerPin"])
        for name in ("operatorEnrollmentRootCustodyVerified",
                     "braveWindowInstanceAuthenticated","canRestoreBrave"):
            self.assertIs(out[name],False)

    def test_34_native_service_always_refuses(self):
        with self.assertRaisesRegex(W.Refused,
                                    "REAL_NATIVE_BRAVE_SWAY_BINDING_NOT_IMPLEMENTED"):
            W.run_native_timew_window_witness(operatorApproved=True)


if __name__=="__main__":
    unittest.main(verbosity=2)
