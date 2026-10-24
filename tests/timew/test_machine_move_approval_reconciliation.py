#!/usr/bin/env python3
"""M1n pure approval + read-only reconciliation, fake Sway and temp SQLite."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
from MachineMoveApproval import MoveApprovalGate, ApprovalError
from MachineMoveJournal import MoveJournal, JournalError
from MachineMoveReconciliation import inspect_pending

rect = {"x": 0, "y": 0, "width": 1280, "height": 800}
snapshot = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "test checkpoint",
    "captured_at_utc": "2026-10-24T12:53:00+00:00",
    "outputs": [{"connector": "DP-5", "rect": rect}],
    "workspaces": [{"name": "1", "output": "DP-5"},
                   {"name": "2", "output": "DP-5"}],
    "windows": [{"app_id": "kitty", "workspace": "2", "floating": False}],
}
request = {"intent": "single-existing-window-workspace-move",
           "approved": False, "app_id": "kitty", "con_id": 51,
           "from_workspace": "1", "to_workspace": "2"}
checkpoint = "11111111-2222-4333-8444-555555555555"
outputs = [{"name": "DP-5", "active": True, "rect": rect}]
workspaces = [{"name": "1", "output": "DP-5"}, {"name": "2", "output": "DP-5"}]


def node(location="1", app="kitty", id=51):
    return {"type": "root", "nodes": [
        {"type": "workspace", "name": location,
         "nodes": [{"type": "con", "id": id, "app_id": app,
                    "floating": "auto_off", "fullscreen_mode": 0,
                    "nodes": [], "floating_nodes": [], "pid": 2222,
                    "name": "private file"}],
         "floating_nodes": []}], "floating_nodes": []}


class Sway:
    def __init__(self, tree=None):
        self.tree = tree if tree is not None else node()
        self.calls = 0
        self.outputs = copy.deepcopy(outputs)
    def read(self, argv, **kwargs):
        self.calls += 1
        assert argv in ([ "swaymsg", "-r", "-t", "get_outputs"],
                        [ "swaymsg", "-r", "-t", "get_workspaces"],
                        [ "swaymsg", "-r", "-t", "get_tree"])
        assert kwargs["shell"] is False
        return SimpleNamespace(stdout=json.dumps({
            "get_outputs": self.outputs, "get_workspaces": workspaces,
            "get_tree": self.tree}[argv[-1]]).encode())


def denied(fn):
    try:
        fn()
    except ApprovalError:
        return
    raise AssertionError("approval boundary did not refuse")


time_now = [100.0]
gate = MoveApprovalGate(clock=lambda: time_now[0],
                        nonce_factory=lambda: "z"*40)
live = Sway()
preview = gate.review(snapshot, request, checkpoint_id=checkpoint,
                      read_runner=live.read)
assert preview["state"] == "awaiting_confirmation"
assert preview["executable"] is False and preview["single_use"] is True
assert preview["action"]["con_id"] == 51
assert "private" not in str(preview) and "2222" not in str(preview)
assert live.calls == 3

denied(lambda: gate.approve(
    review_id=preview["review_id"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=request, confirmation_text="MOVE"))
changed_document = copy.deepcopy(snapshot)
changed_document["label"] = "other"
denied(lambda: gate.approve(
    review_id=preview["review_id"], checkpoint_id=checkpoint,
    saved_document=changed_document, request=request,
    confirmation_text=preview["confirmation_text"]))
denied(lambda: gate.approve(
    review_id=preview["review_id"], checkpoint_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
    saved_document=snapshot, request=request,
    confirmation_text=preview["confirmation_text"]))

consent = gate.approve(
    review_id=preview["review_id"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=request,
    confirmation_text=preview["confirmation_text"])
assert consent["single_use"] is True
denied(lambda: gate.approve(
    review_id=preview["review_id"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=request,
    confirmation_text=preview["confirmation_text"]))
with_new_bool = dict(request, approved=True)
denied(lambda: gate.consume(
    approval_token="a" * 40, checkpoint_id=checkpoint,
    saved_document=snapshot, request=with_new_bool))
denied(lambda: gate.consume(
    approval_token=consent["approval_token"], checkpoint_id=checkpoint,
    saved_document=changed_document, request=with_new_bool))
gate.consume(approval_token=consent["approval_token"], checkpoint_id=checkpoint,
             saved_document=snapshot, request=with_new_bool)
denied(lambda: gate.consume(
    approval_token=consent["approval_token"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=with_new_bool))

# Approval for another review invalidates the first and doesn't bind to a
# runtime restart. Expiry uses monotonic time with exact boundary semantics.
preview = gate.review(snapshot, request, checkpoint_id=checkpoint,
                      read_runner=live.read)
next_review = gate.review(snapshot, request, checkpoint_id=checkpoint,
                          read_runner=live.read)
denied(lambda: gate.approve(
    review_id=preview["review_id"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=request,
    confirmation_text=preview["confirmation_text"]))
consent = gate.approve(
    review_id=next_review["review_id"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=request,
    confirmation_text=next_review["confirmation_text"])
time_now[0] += 90
denied(lambda: gate.consume(
    approval_token=consent["approval_token"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=with_new_bool))
denied(lambda: gate.consume(
    approval_token=consent["approval_token"], checkpoint_id=checkpoint,
    saved_document=snapshot, request=with_new_bool))
denied(lambda: gate.review(
    snapshot, with_new_bool, checkpoint_id=checkpoint, read_runner=live.read))

with tempfile.TemporaryDirectory() as temp:
    db = Path(temp) / "machine" / "move-operations.db"
    journal = MoveJournal(db)
    initial = inspect_pending(journal, read_runner=live.read)
    assert initial["items"] == [] and initial["manual_review_required"] is False
    before = {"con_id": 51, "app_id": "kitty",
              "workspace": "1", "target_workspace": "2"}
    op = journal.begin(before)
    initial_calls = live.calls
    view = inspect_pending(journal, read_runner=live.read)
    assert live.calls == initial_calls + 3
    assert len(view["items"]) == 1
    assert view["items"][0]["advisory_state"] == "appears_at_origin"
    assert view["items"][0]["durable_phase"] == "prepared"
    assert view["items"][0]["requires_manual_review"]
    assert not view["items"][0]["automatic_retry_allowed"]
    assert not view["items"][0]["automatic_undo_allowed"]
    assert "private" not in str(view) and "2222" not in str(view)
    assert journal.get(op)["phase"] == "prepared"

    journal.mark_dispatching(op)
    live.tree = node("2")
    view = inspect_pending(journal, read_runner=live.read)
    assert view["items"][0]["advisory_state"] == "appears_at_target"
    assert view["items"][0]["durable_phase"] == "dispatching"
    assert journal.get(op)["phase"] == "dispatching"

    live.tree = node("3")
    assert inspect_pending(journal, read_runner=live.read)["items"][0]["advisory_state"] == "workspace_or_window_unavailable"
    live.tree = node("1", id=99)
    assert inspect_pending(journal, read_runner=live.read)["items"][0]["advisory_state"] == "saved_window_not_identified"
    live.tree = node("1", app="other")
    assert inspect_pending(journal, read_runner=live.read)["items"][0]["advisory_state"] == "identity_conflict"

    live.tree = node("1")
    live.outputs = []
    assert inspect_pending(journal, read_runner=live.read)["items"][0]["advisory_state"] == "workspace_or_window_unavailable"
    live.outputs = copy.deepcopy(outputs)
    live.tree = {"type": "root", "nodes": [{"type": "workspace", "name": "1",
        "nodes": [node()["nodes"][0]["nodes"][0],
                  dict(node()["nodes"][0]["nodes"][0], id=52)],
        "floating_nodes": []}], "floating_nodes": []}
    assert inspect_pending(journal, read_runner=live.read)["items"][0]["advisory_state"] == "ambiguous_candidate"

    # An interrupted operation remains pending even when it appears moved.
    live.tree = node("2")
    assert journal.pending()[0]["phase"] == "dispatching"
    try:
        journal.begin(before)
        raise AssertionError("reconciliation improperly cleared pending operation")
    except JournalError:
        pass

print("MACHINE M1N: SCOPED ONE-USE APPROVAL + READ-ONLY RECONCILIATION PASS")
