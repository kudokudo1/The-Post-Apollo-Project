#!/usr/bin/env python3
"""M1p typed-confirmation rehearsal: no token, no write and no Sway mutation."""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineMoveConfirmRead import (
    ConfirmationError, confirm_preview, required_phrase, main,
)

rect = {"x": 0, "y": 0, "width": 1280, "height": 800}
document = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "M1p",
    "captured_at_utc": "2026-10-24T12:53:00+00:00",
    "outputs": [{"connector": "DP-5", "rect": rect}],
    "workspaces": [{"name": "1", "output": "DP-5"},
                   {"name": "2", "output": "DP-5"}],
    "windows": [{"app_id": "kitty", "workspace": "2", "floating": False}],
}
candidate = {"app_id": "kitty", "status": "candidate",
             "reason": "UNIQUE LIVE WINDOW; NOT YET APPROVED",
             "target_workspace": "2", "current_workspace": "1",
             "live_con_id": 51}
payload = {"checkpoint_id": "11111111-2222-4333-8444-555555555555",
           "document": document, "candidate": candidate,
           "confirmation_text": "MOVE kitty FROM 1 TO 2"}
outputs = [{"name": "DP-5", "active": True, "rect": rect}]
workspaces = [{"name": "1", "output": "DP-5"},
              {"name": "2", "output": "DP-5"}]


class ReadOnlySway:
    def __init__(self, app="kitty", location="1", con_id=51):
        self.calls = []
        self.app, self.location, self.con_id = app, location, con_id
    def runner(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        assert argv[:3] == ["swaymsg", "-r", "-t"]
        assert argv[3] in ("get_outputs", "get_workspaces", "get_tree")
        assert kwargs["shell"] is False
        tree = {"type": "root", "nodes": [{
            "type": "workspace", "name": self.location,
            "nodes": [{"type": "con", "id": self.con_id, "app_id": self.app,
                       "floating": "auto_off", "fullscreen_mode": 0,
                       "nodes": [], "floating_nodes": [],
                       "name": "PRIVATE TITLE", "pid": 987}],
            "floating_nodes": []}], "floating_nodes": []}
        values = {"get_outputs": outputs, "get_workspaces": workspaces,
                  "get_tree": tree}
        return SimpleNamespace(stdout=json.dumps(values[argv[-1]]).encode())


def rejects(entry, sway=None):
    f = sway if sway is not None else ReadOnlySway()
    try:
        confirm_preview(entry, read_runner=f.runner)
        raise AssertionError("confirmation improperly accepted")
    except (ConfirmationError, ValueError):
        pass
    assert all(x[3] != "command" for x in f.calls)


sway = ReadOnlySway()
original = copy.deepcopy(payload)
result = confirm_preview(payload, read_runner=sway.runner)
assert payload == original
assert len(sway.calls) == 3
assert result == {
    "kind": "machine-m1p-confirmation-dry-run",
    "status": "phrase_validated_read_only",
    "read_only": True, "executable": False,
    "approval_issued": False, "confirmation_persisted": False,
    "requires_new_approval_to_execute": True,
    "action": {"app_id": "kitty", "con_id": 51,
               "from_workspace": "1", "to_workspace": "2"},
}
assert required_phrase(result["action"]) == payload["confirmation_text"]
assert "approval_token" not in str(result)
assert "PRIVATE" not in str(result) and "987" not in str(result)
for typo in ("move kitty FROM 1 TO 2", "MOVE kitty FROM 1 TO 3",
             "MOVE  kitty FROM 1 TO 2", "MOVE kitty FROM 1 TO 2 ",
             "MOVE kitty FROM 1 TO 2\n", "", " " * 257):
    rejects(dict(payload, confirmation_text=typo))
rejects(dict(payload, checkpoint_id="bad"))
rejects(dict(payload, document=dict(document, title="SECRET")))
rejects(dict(payload, candidate=dict(candidate, status="manual")))
rejects(dict(payload, candidate=dict(candidate, live_con_id=99)))
rejects(dict(payload, injected=True))
rejects(payload, ReadOnlySway(location="2"))
rejects(payload, ReadOnlySway(app="brave"))
rejects(payload, ReadOnlySway(con_id=98))


def call(argv, payload_for_input=None):
    old_stdin = sys.stdin
    raw = (json.dumps(payload_for_input) + "\n").encode() if payload_for_input else b""
    try:
        sys.stdin = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = ["MachineMoveConfirmRead.py", *argv]
        try:
            with contextlib.redirect_stdout(buf):
                status = main(read_runner=ReadOnlySway().runner)
        finally:
            sys.argv = old_argv
        return status, json.loads(buf.getvalue())
    finally:
        sys.stdin = old_stdin

status, data = call(["confirm-preview"], payload)
assert status == 0 and data["read_only"] and not data["approval_issued"]
for action in ("approve", "execute", "move", "confirm"):
    status, data = call([action], payload)
    assert status == 2 and data["status"] == "error"
status, data = call(["confirm-preview"])
assert status == 1 and data["status"] == "error"
status, data = call(["confirm-preview"], dict(payload, confirmation_text="bad"))
assert status == 1 and data["status"] == "error"
print("MACHINE M1P: TYPED CONFIRMATION REHEARSAL PASS / ZERO APPROVALS")
