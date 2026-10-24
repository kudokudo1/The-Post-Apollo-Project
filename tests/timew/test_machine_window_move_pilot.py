#!/usr/bin/env python3
"""M1k mock Sway harness. No live compositor is contacted or changed."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2] / "services" / "time"
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location("machine_move", root / "MachineWindowMovePilot.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

rect = {"x": 0, "y": 0, "width": 1920, "height": 1080}
document = {
    "schema_version": 1, "kind": "sway-layout-selection-preview",
    "preview_only": True, "label": "Work",
    "captured_at_utc": "2026-10-24T09:35:00+00:00",
    "outputs": [{"connector": "DP-5", "rect": rect}],
    "workspaces": [{"name": "1", "output": "DP-5"},
                   {"name": "2", "output": "DP-5"}],
    "windows": [{"app_id": "kitty", "workspace": "2", "floating": False}],
}
request = {
    "intent": "single-existing-window-workspace-move", "approved": True,
    "app_id": "kitty", "con_id": 51, "from_workspace": "1",
    "to_workspace": "2",
}
outputs = [{"name": "DP-5", "active": True, "rect": rect}]
workspaces = [{"name": "1", "output": "DP-5"}, {"name": "2", "output": "DP-5"}]


def node(ws):
    return {
        "type": "root", "nodes": [{
            "type": "workspace", "name": ws,
            "nodes": [{"type": "con", "id": 51, "app_id": "kitty",
                       "floating": "auto_off", "fullscreen_mode": 0,
                       "nodes": [], "floating_nodes": [],
                       "name": "VERY PRIVATE TITLE", "pid": 777}],
            "floating_nodes": [],
        }], "floating_nodes": [],
    }


class FakeSway:
    def __init__(self, before="1", after="2", successful=True, fail_read=False):
        self.before = before
        self.after = after
        self.location = before
        self.successful = successful
        self.fail_read = fail_read
        self.calls = []

    def read(self, argv, **kwargs):
        assert argv[:3] == ["swaymsg", "-r", "-t"]
        assert kwargs["shell"] is False and kwargs["timeout"] == 3
        assert kwargs["capture_output"] is True and kwargs["check"] is True
        self.calls.append(tuple(argv))
        if self.fail_read:
            raise OSError("unavailable")
        data = {"get_outputs": outputs, "get_workspaces": workspaces,
                "get_tree": node(self.location)}
        return SimpleNamespace(stdout=json.dumps(data[argv[-1]]).encode())

    def command(self, argv, **kwargs):
        assert kwargs == {"check": False, "capture_output": True, "timeout": 3, "shell": False}
        self.calls.append(tuple(argv))
        assert argv == ["swaymsg", "-r", "-t", "command",
                        "[con_id=51] move container to workspace number 2"]
        if self.successful:
            self.location = self.after
        return SimpleNamespace(
            returncode=0 if self.successful else 1,
            stdout=b'[{"success":true}]' if self.successful else b'[{"success":false}]',
        )


def refused(document, req, fake):
    try:
        mod.execute_one(document, req, read_runner=fake.read, command_runner=fake.command)
        raise AssertionError("unsafe plan unexpectedly executed")
    except mod.MoveRefused:
        assert not any(x[3] == "command" for x in fake.calls)


before = copy.deepcopy(document)
req_before = copy.deepcopy(request)
fake = FakeSway()
preview = mod.preview_one(document, dict(request, approved=False), read_runner=fake.read)
assert preview["status"] == "ready_for_review"
assert preview["requires_explicit_approval"] and not preview["executable"]
assert preview["undo_preview"]["workspace"] == "1"
assert not any(c[3] == "command" for c in fake.calls)
fake = FakeSway()
result = mod.execute_one(document, request, read_runner=fake.read, command_runner=fake.command)
assert result["status"] == "verified_moved"
assert result["observed_workspace"] == "2"
assert result["before"]["workspace"] == "1"
assert result["undo_preview"]["executable"] is False
assert result["no_automatic_undo"]
assert sum(x[3] == "command" for x in fake.calls) == 1
assert fake.calls[:3] == [
    ("swaymsg", "-r", "-t", "get_outputs"),
    ("swaymsg", "-r", "-t", "get_workspaces"),
    ("swaymsg", "-r", "-t", "get_tree"),
]
assert fake.calls[-3:] == fake.calls[:3]
assert document == before and request == req_before
assert "PRIVATE" not in str(result) and "777" not in str(result)

# Sway accepted the command but the window never moved: no false success.
fake = FakeSway(after="1")
assert mod.execute_one(document, request, read_runner=fake.read,
                       command_runner=fake.command)["status"] == "uncertain_requires_manual_review"

# Explicit refusal with confirmed original placement.
fake = FakeSway(successful=False)
assert mod.execute_one(document, request, read_runner=fake.read,
                       command_runner=fake.command)["status"] == "refused_no_confirmed_move"

# No action for unsigned, stale, ambiguous, malformed, or unsafe requests.
for req in (
    dict(request, approved=False),
    dict(request, con_id=52),
    dict(request, from_workspace="3"),
    dict(request, app_id="brave"),
    dict(request, to_workspace="2; kill"),
    dict(request, to_workspace="Work"),
    dict(request, to_workspace="0"),
    dict(request, to_workspace="1000"),
    dict(request, intent="start-program"),
    dict(request, con_id=True),
    dict(request, to_workspace="1"),
    dict(request, approved="yes"),
    dict(request, extra=True),
):
    refused(document, req, FakeSway())

bad = copy.deepcopy(document)
bad["windows"].append(copy.deepcopy(bad["windows"][0]))
refused(bad, request, FakeSway())
fake = FakeSway(before="2")
refused(document, request, fake)

fake = FakeSway(fail_read=True)
refused(document, request, fake)

# An ambiguous current app ID is refused before any move.
def duplicate_tree_runner(argv, **kwargs):
    data = {"get_outputs": outputs, "get_workspaces": workspaces,
            "get_tree": {"type": "root", "nodes": [{
                "type": "workspace", "name": "1",
                "nodes": [
                    {"type":"con","id":51,"app_id":"kitty","nodes":[],"floating_nodes":[]},
                    {"type":"con","id":52,"app_id":"kitty","nodes":[],"floating_nodes":[]}
                ], "floating_nodes": []
            }], "floating_nodes": []}}
    return SimpleNamespace(stdout=json.dumps(data[argv[-1]]).encode())

try:
    mod.execute_one(document, request, read_runner=duplicate_tree_runner,
                    command_runner=lambda *_a, **_kw: (_ for _ in ()).throw(
                        AssertionError("must not send move")))
    raise AssertionError("duplicate apps accepted")
except mod.MoveRefused:
    pass


# A command accepted by Sway but losing its target output after the move
# must not be reported as successful.
class ChangedOutput(FakeSway):
    def read(self, argv, **kwargs):
        if self.location == "2" and argv[-1] == "get_workspaces":
            changed = copy.deepcopy(workspaces)
            changed[1]["output"] = "UNPLUGGED"
            return SimpleNamespace(stdout=json.dumps(changed).encode())
        return super().read(argv, **kwargs)
fake = ChangedOutput()
assert mod.execute_one(document, request, read_runner=fake.read,
                       command_runner=fake.command)["status"] == "uncertain_requires_manual_review"

# Fresh postflight no longer sees the same app identity: uncertain.
class SwappedApp(FakeSway):
    def read(self, argv, **kwargs):
        if self.location == "2" and argv[-1] == "get_tree":
            altered = node("2")
            altered["nodes"][0]["nodes"][0]["app_id"] = "different-app"
            return SimpleNamespace(stdout=json.dumps(altered).encode())
        return super().read(argv, **kwargs)
fake = SwappedApp()
assert mod.execute_one(document, request, read_runner=fake.read,
                       command_runner=fake.command)["status"] == "uncertain_requires_manual_review"

print("MACHINE M1K: GUARDED MOVE PILOT PASS / INJECTED SWAY ONLY")
