#!/usr/bin/env python3
"""MACHINE one-click orchestration: disposable fake compositor, no real actions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "time"))
from MachineRestoreCheckpoint import restore_checkpoint, RestoreError, RESULT_KIND

ID = "00000000-0000-4000-8000-000000000001"


def make_store(windows):
    def load(value):
        assert value == ID
        return {"status": "loaded", "checkpoint": {"id": ID},
                "document": {"windows": windows}}
    return load


class Journal:
    def __init__(self, pending=False):
        self._pending = pending

    def pending(self):
        return [{"phase": "dispatching"}] if self._pending else []


def exercise(windows, states, *, launched=True, pending=False,
             uncertain_app=None):
    calls = []
    def resolved(document, *, runner):
        candidates = list(states.values())
        return {"truncated": False, "candidates": candidates}
    def moved(checkpoint_id, document, candidate, *, read_runner,
              command_runner):
        assert checkpoint_id == ID
        assert candidate["status"] == "candidate"
        calls.append(("move", candidate["app_id"]))
        if candidate["app_id"] == uncertain_app:
            return {"status": "uncertain_requires_manual_review"}
        return {"status": "verified_moved"}
    def launched_app(app_id, *, runner):
        calls.append(("launch", app_id))
        if not launched:
            return False
        states[app_id] = candidate(app_id, "candidate")
        return True
    result = restore_checkpoint(
        ID, load_adapter=make_store(windows),
        resolve_adapter=resolved, move_adapter=moved,
        launch_adapter=launched_app, read_runner=None,
        command_runner=None, launch_runner=None,
        journal_factory=lambda _: Journal(pending), sleep=lambda _: None)
    assert result["kind"] == RESULT_KIND
    assert result["checkpoint_id"] == ID
    return result, calls


def candidate(app, status, reason=None):
    return {"app_id": app, "status": status,
            "reason": reason or ("APP NOT RUNNING" if status == "manual" else "OK"),
            "target_workspace": "2", "current_workspace": "1",
            "live_con_id": 101 if status == "candidate" else None}


def win(app):
    return {"app_id": app, "workspace": "2", "floating": False}


result, calls = exercise(
    [win("alpha"), win("beta"), win("gamma")],
    {"alpha": candidate("alpha", "candidate"),
     "beta": candidate("beta", "already"),
     "gamma": candidate("gamma", "manual")})
assert result["status"] == "complete", result
assert result["counts"] == {"moved": 1, "opened": 1, "in_place": 1,
                            "pending": 0, "skipped": 0}, result
assert calls == [("move", "alpha"), ("launch", "gamma"), ("move", "gamma")], calls

result, calls = exercise([win("two"), win("two"), win("three")],
                         {"two": candidate("two", "manual"),
                          "three": candidate("three", "candidate")})
assert result["counts"]["skipped"] == 1
assert calls == [("move", "three")], calls
assert "MULTIPLE WINDOWS" in result["items"][-1]["reason"]

result, calls = exercise([win("alpha")],
                         {"alpha": candidate("alpha", "manual")},
                         launched=False)
assert result["counts"]["skipped"] == 1 and calls == [("launch", "alpha")]

result, calls = exercise([win("alpha")],
                         {"alpha": candidate("alpha", "candidate")}, pending=True)
assert result["status"] == "needs_attention" and not calls

result, calls = exercise([win("alpha"), win("beta")],
                         {"alpha": candidate("alpha", "candidate"),
                          "beta": candidate("beta", "candidate")},
                         uncertain_app="alpha")
assert result["counts"]["skipped"] == 2
assert calls == [("move", "alpha")], calls
assert result["no_automatic_retry"] is True

try:
    restore_checkpoint(ID, load_adapter=lambda _: {"status": "error"})
except RestoreError:
    pass
else:
    raise AssertionError("missing stored checkpoint was accepted")

# Native launcher boundary: never pass commands, paths, or shell fragments.
from MachineRestoreCheckpoint import _start_app


class FakeRun:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        return type("Completed", (), {"returncode": 0})()


fake_run = FakeRun()
assert not _start_app("brave; rm -rf /", runner=fake_run)
assert not _start_app("../../untrusted", runner=fake_run)
assert not _start_app("quickshell", runner=fake_run)
assert fake_run.calls == []
assert _start_app("brave-browser", runner=fake_run)
assert fake_run.calls[0][0] == ["gtk-launch", "brave-browser"]
assert fake_run.calls[0][1]["shell"] is False

print("MACHINE ONE CLICK // FAKE DESKTOP RESTORE PASS")
