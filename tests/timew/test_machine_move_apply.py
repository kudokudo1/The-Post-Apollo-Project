#!/usr/bin/env python3
"""M1q injectable bridge: synthetic only, never calls the host compositor."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineMoveApply import apply_one, ApplyError
from MachineMoveJournal import MoveJournal

RECT = {"x": 0, "y": 0, "width": 1280, "height": 800}
DOC = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "saved",
    "captured_at_utc": "2026-10-24T12:53:00+00:00",
    "outputs": [{"connector": "DP-5", "rect": RECT}],
    "workspaces": [{"name": "1", "output": "DP-5"},
                   {"name": "2", "output": "DP-5"}],
    "windows": [{"app_id": "kitty", "workspace": "2", "floating": False}],
}
ID = "11111111-2222-4333-8444-555555555555"
CANDIDATE = {
    "app_id": "kitty", "status": "candidate",
    "reason": "UNIQUE LIVE WINDOW; NOT YET APPROVED",
    "target_workspace": "2", "current_workspace": "1", "live_con_id": 51,
}


class FakeSway:
    def __init__(self):
        self.at = "1"
        self.commands = []
        self.accept = True
        self.duplicate = False

    def read(self, argv, **kwargs):
        assert argv[:4] == ["swaymsg", "-r", "-t", argv[-1]]
        assert kwargs["shell"] is False
        window = {"type": "con", "id": 51, "app_id": "kitty",
                  "floating": "auto_off", "fullscreen_mode": 0,
                  "nodes": [], "floating_nodes": [],
                  "pid": 1234, "name": "private"}
        wins = [window]
        if self.duplicate:
            wins.append(dict(window, id=52))
        tree = {"type": "root", "nodes": [
            {"type": "workspace", "name": self.at,
             "nodes": wins, "floating_nodes": []}
        ], "floating_nodes": []}
        values = {
            "get_outputs": [{"name": "DP-5", "active": True, "rect": RECT}],
            "get_workspaces": [{"name": "1", "output": "DP-5"},
                               {"name": "2", "output": "DP-5"}],
            "get_tree": tree,
        }
        return SimpleNamespace(stdout=json.dumps(values[argv[-1]]).encode())

    def command(self, argv, **kwargs):
        assert argv[:4] == ["swaymsg", "-r", "-t", "command"]
        assert argv[4] == (
            "[con_id=51] move --no-auto-back-and-forth container to workspace 2")
        assert kwargs["shell"] is False
        self.commands.append(argv)
        if self.accept:
            self.at = "2"
        return SimpleNamespace(
            stdout=b'[{"success":true}]' if self.accept else b'[{"success":false}]',
            returncode=0)


def fixture(sway, database):
    return {
        "read_runner": sway.read, "command_runner": sway.command,
        "checkpoint_loader": lambda id: {
            "status": "loaded", "checkpoint": {"id": ID},
            "document": copy.deepcopy(DOC)},
        "journal_factory": lambda ignored: MoveJournal(database),
    }


def payload():
    return {
        "checkpoint_id": ID, "document": copy.deepcopy(DOC),
        "candidate": dict(CANDIDATE),
        "confirmation_text": "MOVE kitty FROM 1 TO 2",
    }


def refuses(p, opts):
    try:
        apply_one(p, **opts)
    except (ApplyError, ValueError):
        return
    raise AssertionError("unsafe apply was not refused")


with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "move-operations.db"
    sway = FakeSway()
    opts = fixture(sway, db)
    p = payload()
    p["confirmation_text"] = "MOVE kitty FROM 2 TO 1"
    refuses(p, opts)
    assert not sway.commands and not db.exists(), "wrong phrase must never journal"

    p = payload()
    p["document"]["label"] = "forged"
    refuses(p, opts)
    assert not sway.commands and not db.exists(), "unsaved checkpoint must fail"

    p = payload()
    p["candidate"]["live_con_id"] = 99
    refuses(p, opts)
    assert not sway.commands and not db.exists(), "stale window must fail"

    sway.duplicate = True
    refuses(payload(), opts)
    assert not sway.commands and not db.exists(), "duplicate app must fail"

    sway.duplicate = False
    result = apply_one(payload(), **opts)
    assert result["status"] == "verified_moved"
    assert result["kind"] == "machine-m1q-single-window-result"
    assert result["no_automatic_retry"] and result["no_automatic_undo"]
    assert len(sway.commands) == 1 and sway.at == "2"
    assert MoveJournal(db).pending() == []
    assert "private" not in str(result) and "1234" not in str(result)

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "move-operations.db"
    sway = FakeSway()
    sway.accept = False
    opts = fixture(sway, db)
    result = apply_one(payload(), **opts)
    assert result["status"] == "refused_no_confirmed_move"
    assert not MoveJournal(db).pending()

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "move-operations.db"
    sway = FakeSway()
    opts = fixture(sway, db)

    def uncertain(argv, **kwargs):
        sway.commands.append(argv)
        sway.duplicate = True  # postflight identity becomes ambiguous
        return SimpleNamespace(stdout=b'invalid', returncode=1)

    opts["command_runner"] = uncertain
    result = apply_one(payload(), **opts)
    assert result["status"] == "uncertain_requires_manual_review"
    assert len(MoveJournal(db).pending()) == 1
    sway.duplicate = False  # next action viable, but pending journal blocks it
    refuses(payload(), opts)
    assert len(sway.commands) == 1, "pending must block repeat dispatch"

print("M1q synthetic one-window apply: PASS")
