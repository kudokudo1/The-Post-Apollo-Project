#!/usr/bin/env python3
"""M11d source-derived write-path audit; no runtime or live database access.

Fail if a TASKS mutation gains an unreviewed UI caller, if a second
task-specific FileView appears, or if the single authoritative staging
seam and asynchronous completion semantics disappear.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT/"tests/tasks/fixtures/task_writer_gate_inventory_m11d.json"
data = json.loads(MANIFEST.read_text())
STORE = ROOT / data["authoritativeStore"]
store = STORE.read_text()
MUTATORS = set(data["mutationMethods"])
READERS = set(data["readMethods"])
ALL = MUTATORS | READERS
assert data["contractVersion"] == 1
assert data["productionChangesAuthorized"] is False
assert data["sqliteActivationAuthorized"] is False
assert data["scope"] == "SOURCE_AUDIT_ONLY_NOT_WRITER_GATE"
assert STORE.exists()
assert len(MUTATORS) == 9 and READERS == {"reloadFromDisk"}
assert len(data["mandatoryFutureGateSeams"]) >= 9
assert {r["event"] for r in data["mandatoryFutureGateSeams"]} == {
    "stage entry","freeze request","in-flight save","save failure",
    "load","explicit reload","source readback","process restart",
    "SQLite writer"
}

# Verify the exact backend and the only FileView write entry. No fabricated
# SQLite gate can be inferred from the success of this static test.
assert "Quickshell.dataDir + " in store
assert data["storagePathSuffix"] in store
assert len(re.findall(r"\bFileView\s*\{",store)) == 1
assert len(re.findall(r"\btodoFile\.setText\s*\(",store)) == 1
for event in ("onLoaded:","onLoadFailed:","onSaved:","onSaveFailed:"):
    assert store.count(event) == 1, event
assert "atomicWrites: true" in store
assert "blockWrites: false" in store
assert "watchChanges: false" in store
assert "pendingDocument = null;" in store
assert 'todo.storageState = "error";' in store

# Every public write wrapper must return through stage(...). A separate
# direct FileView or task SQL write would bypass future epoch admission.
public_funcs = dict((name,body) for name,body in re.findall(
    r"\bfunction\s+(\w+)\s*\([^)]*\)\s*\{(.*?)\n\s*\}",
    store,re.DOTALL))
expected_public = MUTATORS | READERS | {"stage","acceptLoaded"}
assert set(public_funcs) == expected_public, sorted(set(public_funcs)^expected_public)
for method in sorted(MUTATORS):
    body = public_funcs[method]
    assert re.search(r"\breturn\s+stage\s*\(\s*TodoPolicy\.",body),method
    assert "setText" not in body, method
    assert "exec(" not in body, method
stage = public_funcs["stage"]
assert re.search(r'storageState\s*!==\s*"ready"\s*&&\s*storageState\s*!==\s*"empty"',stage)
assert 'storageState = "saving"' in stage
assert stage.index("pendingDocument = result.document") < stage.index("todoFile.setText")
assert 'pendingDocument = result.document' in stage
assert 'todoFile.setText' in stage
assert "readonly property var snapshot:" in store
assert "TodoPolicy.view(storageState, document, errorCode)" in store
# Event callback success is the only point where the new document publishes.
on_saved = store[store.index("onSaved:"):store.index("onSaveFailed:")]
assert "todo.document = todo.pendingDocument;" in on_saved
assert "todo.pendingDocument = null;" in on_saved
assert "todo.document = todo.pendingDocument;" not in stage

# Search the complete QML surfaces used by the desktop, not a hand-picked
# list only. New direct task calls make CI fail until inventoried/reviewed.
roots = [ROOT/"widgets", ROOT/"services", ROOT/"modules"]
files = [p for root in roots for p in root.rglob("*.qml")]
files += list(ROOT.glob("*.qml"))
pattern = re.compile(
    r"\b(?:todoStore|ApolloHubTodoStore)\s*\.\s*(" +
    "|".join(re.escape(x) for x in sorted(ALL | {"stage"})) + r")\s*\(")
actual = {}
for path in files:
    text = path.read_text()
    name = path.relative_to(ROOT).as_posix()
    matches = Counter(pattern.findall(text))
    if matches:
        actual[name] = dict(matches)
assert actual == data["callers"], (
    "TASKS writer route drift: actual="+repr(actual)+
    " expected="+repr(data["callers"]))

# No task UI should hold a second FileView, write to a task path, or call
# stage directly. These are targeted checks, not a general filesystem audit.
target_files = [p for p in files if (
    p.as_posix().startswith((ROOT/"widgets/tasks").as_posix()) or
    p.name.startswith(("ApolloHubTodo","TasksW")))]
for p in target_files:
    src = p.read_text()
    assert re.search(r"\bFileView\s*\{",src) is None,p
    assert 'apollo-hub-todo-v1.json' not in src,p
    assert re.search(r"\.stage\s*\(",src) is None,p
    assert re.search(r"\bQuickshell\.execDetached\s*\(",src) is None,p

# TODAY and the pure Planner view do not mutate; PlannerSchedule is the
# only scheduling write caller and routes through an injected store.
for name in data["readOnlySurfaces"]:
    src = (ROOT/name).read_text()
    assert not pattern.search(src),name
    assert "FileView {" not in src,name
today = (ROOT/"widgets/tasks/TaskTodayPane.qml").read_text()
assert "TodayPolicy.view(todoSnapshot, todayKey)" in today
assert "signal openTaskRequested(string taskId)" in today
planner = (ROOT/"widgets/tasks/TaskPlannerPane.qml").read_text()
assert "Planner.view(todoSnapshot, monthKey, selectedDate, todayKey)" in planner
assert "TaskPlannerSchedulePane {" in planner
assert "todoStore: planner.todoStore" in planner

# Follow injection routes to preserve the one shared singleton: TASKS and
# ApolloHub both inject the same actual store and snapshot.
for name,links in data["hostBindings"].items():
    src=(ROOT/name).read_text()
    for kind,code in links.items():
        assert code in src,(name,kind)
tasks=(ROOT/"widgets/TasksW.qml").read_text()
assert "TaskTodayPane {" in tasks
assert "TaskProjectsPane {" in tasks
assert "TaskPlannerPane {" in tasks
assert "ApolloHubTodoMini {" in tasks
assert "TaskDetailsPane {" in tasks
hub=(ROOT/"widgets/ApolloHubW.qml").read_text()
assert "todoStore: ApolloHubTodoStore" in hub
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in hub

# Static audit is not an authorization for local tasks, DB activation or
# any real Quickshell writer gate installation.
print("M11d TASKS/TODAY/PLANNER/Hub single-store mutation inventory and gate seams: PASS")
