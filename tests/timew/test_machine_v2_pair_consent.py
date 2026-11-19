#!/usr/bin/env python3
"""TimeW V2: two independently signed fixture authorities, one-use admission.

Disposable fake Brave/Sway windows, temporary real SQLite and throwaway Ed25519
keys. NEVER opens real Brave, logind, C3e/C5 or an operator Sway socket.
"""
from __future__ import annotations

import base64
import copy
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import threading
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services/time"))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import MachineV2PairConsent as pc
import MachineV2PairedRehearsal as run
from MachineV2GeometryJournal import GeometryJournal, DB_NAME
from MachineCaptureSaveV2 import _legacy_from_geometry
from MachineGeometryV2 import project_geometry
from MachineGeometryStoreV2 import save_pair, load_geometry
from MachineCheckpointStore import load as load_legacy

KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"
SESSION = "33333333-3333-4333-8333-333333333333"
SEAT = "seat0"
NOW = 1763491200000


def rect(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}


def leaf(con_id, rectangle):
    return {
        "type": "floating_con", "id": con_id, "app_id": "brave",
        "rect": rectangle, "layout": "none", "floating": "user_on",
        "percent": None, "fullscreen_mode": 0,
        "nodes": [], "floating_nodes": [], "pid": 999123,
        "name": "PRIVATE BRAVE TITLE SHOULD NEVER APPEAR",
    }


def frame(*, saved=False):
    first, second = (rect(100, 90, 520, 400), rect(780, 130, 620, 490)) if saved else (
        rect(200, 220, 470, 320), rect(920, 240, 500, 380))
    outputs = [{
        "name": "DP-3", "active": True,
        "rect": rect(0, 0, 1920, 1080),
        "scale": 1.0, "transform": "normal",
    }]
    workspaces = [{"name": "1", "output": "DP-3"}]
    tree = {"type": "root", "nodes": [{
        "type": "output", "name": "DP-3", "nodes": [{
            "type": "workspace", "name": "1", "layout": "splith",
            "rect": rect(0, 0, 1920, 1080), "nodes": [],
            "floating_nodes": [
                leaf(11 if saved else 110, first),
                leaf(12 if saved else 111, second),
            ],
        }],
    }]}
    return outputs, workspaces, tree


class FakeSway:
    def __init__(self):
        self.state = frame()
        self.commands = []
        self.on_first_command = None
        self.no_effect = False

    def win(self, cid):
        return next(x for x in self.state[2]["nodes"][0]["nodes"][0]["floating_nodes"]
                    if x["id"] == cid)

    def read(self, argv, **kw):
        assert argv[:3] == ["swaymsg", "-r", "-t"]
        assert kw == {"check": True, "capture_output": True,
                      "timeout": 3, "shell": False}
        index = {"get_outputs": 0, "get_workspaces": 1, "get_tree": 2}[argv[3]]
        return SimpleNamespace(stdout=json.dumps(self.state[index]).encode(),
                               returncode=0)

    def command(self, argv, **kw):
        assert argv[:4] == ["swaymsg", "-r", "-t", "command"]
        assert kw == {"check": False, "capture_output": True,
                      "timeout": 3, "shell": False}
        command = argv[4]
        self.commands.append(command)
        match = re.fullmatch(
            r"\[con_id=([1-9]\d*)\] resize set ([1-9]\d*) px ([1-9]\d*) px",
            command)
        moved = re.fullmatch(
            r"\[con_id=([1-9]\d*)\] move absolute position (\d+) px (\d+) px",
            command)
        assert (match is None) != (moved is None), command
        match = match or moved
        win = self.win(int(match.group(1)))
        if not self.no_effect:
            if "resize" in command:
                win["rect"]["width"] = int(match.group(2))
                win["rect"]["height"] = int(match.group(3))
            else:
                win["rect"]["x"] = int(match.group(2))
                win["rect"]["y"] = int(match.group(3))
        if len(self.commands) == 1 and self.on_first_command is not None:
            self.on_first_command()
        return SimpleNamespace(stdout=b'[{"success":true}]', returncode=0)


def signed(payload, private, domain):
    message = domain + pc._json(payload)
    signature = base64.urlsafe_b64encode(private.sign(message)).decode().rstrip("=")
    return {"payload": payload, "signature": signature}


def bundle(checkpoint_id, window_key, live_con_id, plan, pair_priv,
           consent_priv, *, pair_id=None, grant_id=None, ms=NOW):
    pairing = {
        "schema": pc.PAIR_SCHEMA, "audience": pc.AUDIENCE,
        "pair_id": pair_id or str(uuid.uuid4()),
        "checkpoint_id": checkpoint_id, "window_key": window_key,
        "live_con_id": live_con_id,
        "app_id": "brave", "workspace": "1", "output": "DP-3",
        "session_id": SESSION,
        "browser_window_ref": str(uuid.uuid4()),
        "issued_ms": ms, "expires_ms": ms + 9000,
    }
    consent = {
        "schema": pc.CONSENT_SCHEMA, "audience": pc.AUDIENCE,
        "grant_id": grant_id or str(uuid.uuid4()),
        "pair_sha256": pc._digest(pairing),
        "intent_sha256": pc._digest(plan), "seat_id": SEAT,
        "session_id": SESSION, "issued_ms": ms,
        "expires_ms": ms + 8000,
        "single_use": True, "approved_action": pc.ACTION,
    }
    return (signed(pairing, pair_priv, pc.PAIR_DOMAIN),
            signed(consent, consent_priv, pc.CONSENT_DOMAIN))


def expect_denied(call):
    try:
        call()
    except (pc.AdmissionRefused, ValueError):
        return
    raise AssertionError("PAIR/CONSENT SAFETY REFUSAL MISSING")


def private_journals(root):
    root = Path(root) / "post-apollo" / "machine"
    return (pc.OneUseSpendLedger(root / pc.SPEND_NAME),
            GeometryJournal(root / DB_NAME))


original_env = {x: os.environ.get(x) for x in ("CI", "GITHUB_ACTIONS", "XDG_DATA_HOME")}
try:
    with tempfile.TemporaryDirectory(prefix="timew-v2-signed-admission-") as tmp:
        os.environ["XDG_DATA_HOME"] = tmp
        os.environ["CI"] = "true"
        os.environ["GITHUB_ACTIONS"] = "true"
        a_priv, c_priv = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
        p_pub, c_pub = a_priv.public_key(), c_priv.public_key()
        bad_priv = Ed25519PrivateKey.generate()
        saved = project_geometry(
            *frame(saved=True), window_keys={11: KEY_A, 12: KEY_B})
        record = _legacy_from_geometry(
            saved, label="Two brave windows", captured_at="2026-11-18T23:00:00+00:00")
        checkpoint_id = save_pair(record, saved)["checkpoint"]["id"]
        assert load_geometry(checkpoint_id)["status"] == "loaded"
        clock = [NOW]
        main = FakeSway()
        base = pc._intent({
            "checkpoint_id": checkpoint_id, "window_key": KEY_A,
            "live_con_id": 110, "app_id": "brave",
            "workspace": "1", "output": "DP-3",
            "before_rect": main.win(110)["rect"],
            "target_rect": saved["windows"][0]["rect"],
            "session_id": SESSION,
        })
        pair, consent = bundle(checkpoint_id, KEY_A, 110, base, a_priv, c_priv)
        verified = pc.verify_pair_and_consent(
            pairing=pair, consent=consent, intent=base,
            pair_key=p_pub, consent_key=c_pub,
            expected_session_id=SESSION, expected_seat_id=SEAT, now_ms=NOW)
        assert verified["production_authorized"] is False
        assert verified["persistent_brave_identity_verified"] is False
        assert verified["requires_independent_issuer_provenance"] is True

        # One exact action, one active session and seat, two independently
        # pinned role-specific Ed25519 public keys. No production trust key.
        allowed = lambda: True
        def invoke(pairing=pair, permit=consent, sway=main,
                   spend=None, journal=None, seat_guard=allowed, clock_source=None,
                   window_key=KEY_A, live_id=110, pair_public=p_pub,
                   consent_public=c_pub, session=SESSION, seat=SEAT):
            if spend is None or journal is None:
                spend, journal = private_journals(tmp)
            return run.execute_fixture(
                checkpoint_id=checkpoint_id, window_key=window_key,
                live_con_id=live_id, pairing=pairing, consent=permit,
                pair_key=pair_public, consent_key=consent_public,
                expected_session_id=session, expected_seat_id=seat,
                active_seat_guard=seat_guard,
                clock_ms=clock_source or (lambda: clock[0]),
                spend_ledger=spend, geometry_journal=journal,
                read_runner=sway.read, command_runner=sway.command,
                legacy_reader=load_legacy, geometry_reader=load_geometry,
            )

        spend, journal = private_journals(tmp)
        assert spend.lookup(verified["grant_id"]) is None
        assert not spend.path.exists() and not journal.path.exists()
        # The earlier saved V1/V2 checkpoint owns the shared parent
        # directory; read-only spend lookup creates no ledger files.
        assert spend.path.parent.is_dir()

        # Cryptographic, role, audience, binding and freshness refusals MUST
        # occur before a grant is spent or Sway is commanded.
        altered_pair = copy.deepcopy(pair)
        altered_pair["payload"]["live_con_id"] = 111
        expect_denied(lambda: invoke(pairing=altered_pair))
        altered_consent = copy.deepcopy(consent)
        altered_consent["payload"]["intent_sha256"] = "0" * 64
        expect_denied(lambda: invoke(permit=altered_consent))
        expect_denied(lambda: invoke(pair_public=c_pub))
        expect_denied(lambda: invoke(consent_public=p_pub))
        expect_denied(lambda: invoke(pair_public=bad_priv.public_key()))
        expect_denied(lambda: invoke(session=str(uuid.uuid4())))
        expect_denied(lambda: invoke(seat="wrong-seat"))
        expect_denied(lambda: invoke(seat_guard=lambda: False))
        expect_denied(lambda: invoke(window_key=KEY_B))
        expect_denied(lambda: invoke(live_id=111))
        expire_clock = lambda: NOW + 10000
        expect_denied(lambda: invoke(clock_source=expire_clock))
        # Two distinct signers are mandatory, including when valid envelopes
        # were issued by the same private key. Never allow "one signer for all".
        same_pair, same_consent = bundle(checkpoint_id, KEY_A, 110, base,
                                        a_priv, a_priv)
        expect_denied(lambda: invoke(pairing=same_pair, permit=same_consent,
                                     consent_public=p_pub))
        assert main.commands == []
        assert not spend.path.exists()

        result = invoke()
        assert result["status"] == "verified_fixture_placement", result
        assert result["dispatched_commands"] == 2
        assert result["consent_spent"] is True
        assert result["production_authorized"] is False
        assert main.win(110)["rect"] == saved["windows"][0]["rect"]
        assert main.win(111)["rect"] != saved["windows"][1]["rect"]
        assert spend.lookup(verified["grant_id"])["spent"] is True
        assert spend.lookup(verified["grant_id"])["replay_allowed"] is False
        assert journal.pending() == []
        with sqlite3.connect(journal.path) as db:
            rows = db.execute("SELECT phase FROM operations").fetchall()
        assert rows == [("verified_fixture_placement",)]

        # A fresh process reopening the spent database still sees burn state.
        import subprocess
        child = """import sys
sys.path.insert(0,sys.argv[1])
from MachineV2PairConsent import OneUseSpendLedger
ledger=OneUseSpendLedger(sys.argv[2])
row=ledger.lookup(sys.argv[3])
assert row and row['spent'] is True and row['replay_allowed'] is False
"""
        child_out = subprocess.run(
            [sys.executable, "-B", "-I", "-c", child, str(ROOT/"services/time"),
             str(spend.path), verified["grant_id"]],
            capture_output=True, timeout=10)
        assert child_out.returncode == 0, child_out.stderr.decode()

        replay = FakeSway()
        expect_denied(lambda: invoke(sway=replay))
        assert replay.commands == [], "spent grant performed second action"

        # A distinct signed per-window pair/consent can target the other Brave
        # instance without confusing two identical app IDs.
        second_sway = main
        second_intent = pc._intent({
            "checkpoint_id": checkpoint_id, "window_key": KEY_B,
            "live_con_id": 111, "app_id": "brave",
            "workspace": "1", "output": "DP-3",
            "before_rect": second_sway.win(111)["rect"],
            "target_rect": saved["windows"][1]["rect"],
            "session_id": SESSION,
        })
        pair_b, consent_b = bundle(checkpoint_id, KEY_B, 111, second_intent,
                                   a_priv, c_priv)
        other = invoke(pairing=pair_b, permit=consent_b,
                       window_key=KEY_B, live_id=111)
        assert other["status"] == "verified_fixture_placement"
        assert main.win(111)["rect"] == saved["windows"][1]["rect"]

        # An expired seat binding after the FIRST command must not allow the
        # SECOND command. Journal becomes UNCERTAIN; approval remains spent.
        expired_sway = FakeSway()
        new_clock = [NOW]
        expired_sway.on_first_command = lambda: new_clock.__setitem__(0, NOW+9000)
        stopped_spend, stopped_journal = private_journals(Path(tmp)/"expired")
        interrupted = invoke(sway=expired_sway, spend=stopped_spend,
                             journal=stopped_journal,
                             clock_source=lambda: new_clock[0])
        assert interrupted["status"] == "uncertain_requires_review"
        assert interrupted["manual_recovery_required"] is True
        assert interrupted["dispatched_commands"] == 1
        assert len(expired_sway.commands) == 1
        assert len(stopped_journal.pending()) == 1
        assert stopped_spend.lookup(verified["grant_id"])["spent"] is True

        # If the geometry journal is already held, a new consent can be
        # burned but still cannot override the protected pending operation.
        held_spend, held_journal = private_journals(Path(tmp)/"held")
        held_journal.begin({
            "checkpoint_id": checkpoint_id, "window_key": KEY_B,
            "app_id": "brave", "live_con_id": 111,
            "before_rect": frame()[2]["nodes"][0]["nodes"][0]["floating_nodes"][1]["rect"],
            "target_rect": saved["windows"][1]["rect"],
        })
        blocked_sway = FakeSway()
        expect_denied(lambda: invoke(sway=blocked_sway, spend=held_spend,
                                     journal=held_journal))
        assert blocked_sway.commands == []
        assert held_spend.lookup(verified["grant_id"])["spent"] is True

        # The durable spend ledger serializes races. Even simultaneous
        # calls attempting the same signed grant cannot both be accepted.
        race_ledger, _ = private_journals(Path(tmp)/"race")
        barrier = threading.Barrier(5)
        won, lost, gate = [], [], threading.Lock()
        def race():
            barrier.wait()
            try:
                race_ledger.spend(verified, now_ms=NOW)
                with gate:
                    won.append(True)
            except pc.AdmissionRefused:
                with gate:
                    lost.append(True)
        tasks = [threading.Thread(target=race) for _ in range(5)]
        for t in tasks:
            t.start()
        for t in tasks:
            t.join(timeout=15)
            assert not t.is_alive()
        assert len(won) == 1 and len(lost) == 4
        assert race_ledger.lookup(verified["grant_id"])["spent"]

        # A same-UID forged document cannot grant permission without Ed25519.
        # Even valid signatures are fixture-only until independent installed
        # key provenance and actual logind seat review exist.
        status = json.dumps(result)
        for secret in ("PRIVATE BRAVE TITLE", "999123",
                       "https://", "password", "tab_url"):
            assert secret not in status

        # Direct test runner bypass is forbidden outside CI. The source
        # exposes no signer or native host startup entrypoint.
        os.environ.pop("CI", None)
        isolated_sway = FakeSway()
        expect_denied(lambda: invoke(sway=isolated_sway))
        assert isolated_sway.commands == []
        assert not hasattr(run, "main")
        assert not hasattr(pc, "main")
finally:
    for name, value in original_env.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value

print("TIMEW V2 PAIR+CONSENT // INDEPENDENT ED25519 ROLES / ONE USE / CRASH HOLDS PASS")
