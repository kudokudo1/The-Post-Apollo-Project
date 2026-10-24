#!/usr/bin/env python3
"""M1o action/journal reader fixtures; no live Sway writes."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineMoveReviewRead import (
    ReviewError, main, review_candidate, review_interruptions,
)
from MachineMoveJournal import MoveJournal

rect = {"x": 0, "y": 0, "width": 1280, "height": 800}
document = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "M1o",
    "captured_at_utc": "2026-10-24T12:53:00+00:00",
    "outputs": [{"connector": "DP-5", "rect": rect}],
    "workspaces": [{"name": "1", "output": "DP-5"},
                   {"name": "2", "output": "DP-5"}],
    "windows": [{"app_id": "kitty", "workspace": "2", "floating": False}],
}
candidate = {
    "app_id": "kitty", "status": "candidate",
    "reason": "UNIQUE LIVE WINDOW; NOT YET APPROVED",
    "target_workspace": "2", "current_workspace": "1",
    "live_con_id": 51,
}
payload = {
    "checkpoint_id": "11111111-2222-4333-8444-555555555555",
    "document": document, "candidate": candidate,
}
outputs = [{"name": "DP-5", "active": True, "rect": rect}]
workspaces = [{"name": "1", "output": "DP-5"},
              {"name": "2", "output": "DP-5"}]

def tree(ws="1", app="kitty", id=51):
    return {"type": "root", "nodes": [
        {"type": "workspace", "name": ws,
         "nodes": [{"type": "con", "id": id, "app_id": app,
                    "floating": "auto_off", "fullscreen_mode": 0,
                    "nodes": [], "floating_nodes": [],
                    "title": "PRIVATE", "pid": 777}],
         "floating_nodes": []}], "floating_nodes": []}

class Fake:
    def __init__(self, ws="1"):
        self.ws = ws
        self.calls = []
    def read(self, argv, **kwargs):
        self.calls.append(tuple(argv))
        assert argv in (
            ["swaymsg", "-r", "-t", "get_outputs"],
            ["swaymsg", "-r", "-t", "get_workspaces"],
            ["swaymsg", "-r", "-t", "get_tree"],
        )
        assert kwargs["shell"] is False
        values = {"get_outputs": outputs, "get_workspaces": workspaces,
                  "get_tree": tree(self.ws)}
        return SimpleNamespace(stdout=json.dumps(values[argv[-1]]).encode())

def reject(payload):
    f = Fake()
    try:
        review_candidate(payload, read_runner=f.read)
        raise AssertionError("unsafe preview accepted")
    except (ReviewError, ValueError):
        pass
    assert not any("command" in x for x in f.calls)

original = copy.deepcopy(payload)
mock = Fake()
result = review_candidate(payload, read_runner=mock.read)
assert result["status"] == "review_only"
assert result["kind"] == "machine-m1o-action-review"
assert result["read_only"] is True
assert result["executable"] is False
assert result["approval_issued"] is False
assert result["requires_fresh_revalidation"] is True
assert result["action"] == {
    "app_id": "kitty", "con_id": 51,
    "from_workspace": "1", "to_workspace": "2"}
assert not any("command" in x for x in mock.calls)
assert len(mock.calls) == 3
assert "review_id" not in result and "approval_token" not in result
assert "confirmation_text" not in result
assert "PRIVATE" not in str(result) and "777" not in str(result)
assert payload == original

reject(dict(payload, candidate=dict(candidate, live_con_id=52)))
reject(dict(payload, candidate=dict(candidate, status="manual")))
reject(dict(payload, candidate=dict(candidate, extra="injected")))
reject(dict(payload, checkpoint_id="bad"))
reject(dict(payload, document=dict(document, title="secret")))
reject(dict(payload, injected=True))
reject(dict(payload, candidate=dict(candidate, target_workspace="1")))

with tempfile.TemporaryDirectory() as temp:
    journal = MoveJournal(Path(temp) / "machine" / "move-operations.db")
    called = Fake()
    empty = review_interruptions(journal=journal, read_runner=called.read)
    assert empty["status"] == "clear" and empty["items"] == []
    assert called.calls == [] and not journal.path.exists()

    before = {"con_id": 51, "app_id": "kitty",
              "workspace": "1", "target_workspace": "2"}
    operation_id = journal.begin(before)
    data = review_interruptions(journal=journal, read_runner=Fake().read)
    assert data["status"] == "pending_review"
    assert data["read_only"] is True and data["executable"] is False
    assert data["approval_issued"] is False
    assert data["no_automatic_retry"] and data["no_automatic_undo"]
    assert len(data["items"]) == 1
    assert data["items"][0]["operation_id"] == operation_id
    assert data["items"][0]["durable_phase"] == "prepared"
    assert data["items"][0]["advisory_state"] == "appears_at_origin"
    assert data["items"][0]["app_id"] == "kitty"
    assert "before" not in data["items"][0]
    assert "PRIVATE" not in str(data) and "777" not in str(data)
    assert journal.get(operation_id)["phase"] == "prepared"
    journal.mark_dispatching(operation_id)
    data = review_interruptions(journal=journal, read_runner=Fake("2").read)
    assert data["items"][0]["advisory_state"] == "appears_at_target"
    assert data["items"][0]["durable_phase"] == "dispatching"
    assert journal.get(operation_id)["phase"] == "dispatching"

    def call_main(action, payload=None):
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        input_bytes = (json.dumps(payload) + "\n").encode() if payload is not None else b""
        try:
            sys.stdin = io.TextIOWrapper(io.BytesIO(input_bytes), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main([action], read_runner=Fake().read,
                            journal_factory=lambda _: journal)
            return code, json.loads(out.getvalue())
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout

    code, data = call_main("preview", payload)
    assert code == 0 and data["status"] == "review_only"
    code, data = call_main("pending")
    assert code == 0 and data["items"][0]["durable_phase"] == "dispatching"
    code, data = call_main("execute", payload)
    assert code == 2 and data["status"] == "error"
    code, data = call_main("approve", payload)
    assert code == 2 and data["status"] == "error"
    code, data = call_main("preview")
    assert code == 1 and data["status"] == "error"
    code, data = call_main("preview", dict(payload, checkpoint_id="bad"))
    assert code == 1 and data["status"] == "error"

print("TIMEW MACHINE M1O: READ-ONLY MOVE + PENDING BRIDGE PASS")
