#!/usr/bin/env python3
"""M3 TASKS is a second UI for the Hub checklist, not a second store."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MENU = (ROOT / "widgets/TasksW.qml").read_text(encoding="utf-8")
HUB = (ROOT / "widgets/ApolloHubW.qml").read_text(encoding="utf-8")
EDITOR = (ROOT / "widgets/hub/ApolloHubTodoMini.qml").read_text(encoding="utf-8")
STORE = (ROOT / "services/hub/ApolloHubTodoStore.qml").read_text(encoding="utf-8")
QMLDIR = (ROOT / "services/hub/qmldir").read_text(encoding="utf-8")

# Reuse one registered singleton and one editor implementation.
assert "import qs.services.hub" in MENU and 'import "hub"' in MENU
assert "import qs.services.hub" in HUB
assert "singleton ApolloHubTodoStore 1.0 ApolloHubTodoStore.qml" in QMLDIR
assert MENU.count("ApolloHubTodoMini {") == 1
assert "todoStore: ApolloHubTodoStore" in MENU
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in MENU
assert "todoStore: ApolloHubTodoStore" in HUB
assert "todoSnapshot: ApolloHubTodoStore.snapshot" in HUB
assert "visible: root.menuOpen && root.activeMode.id === \"tasks\"" in MENU
assert 'visible: root.activeMode.id !== "tasks"' in MENU

# The TASKS page alone opts into the standard scrollable checklist star.
# The editor is also used by ApolloHub; opt-in avoids changing the Hub tile.
assert 'taskScrollbarEnabled: true' in MENU
assert 'property bool taskScrollbarEnabled: false' in EDITOR
assert 'id: todoList' in EDITOR
assert 'boundsBehavior: Flickable.StopAtBounds' in EDITOR
assert EDITOR.count('NeonScrollBar {') == 1
assert 'id: taskListRail' in EDITOR
assert 'parent: todoMini' in EDITOR
assert 'flickable: todoMini.taskScrollbarEnabled ? todoList : null' in EDITOR
assert 'geometryMode: "viewport"' in EDITOR
assert 'accountForContentOrigin: true' in EDITOR
assert 'handleStyle: "star"' in EDITOR
assert 'handleColor: Colors.magenta' in EDITOR
assert 'railColor: Colors.cyan' in EDITOR
assert '&& taskListRail.scrollable' in EDITOR
assert 'taskListRail.reservedExtent : 0' in EDITOR
assert 'taskScrollbarEnabled: true' not in HUB

# Only the TASKS editor page can receive on-demand typing; closing it
# clears pointer capture and disables keyboard capture.
assert 'root.menuOpen && root.activeMode.id === "tasks"' in MENU
assert "WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None" in MENU
assert 'focusable: root.menuOpen && (root.activeMode.id === "tasks"' in MENU
assert "width: root.menuOpen ? root.frameWidth : 0" in MENU
assert "height: root.menuOpen ? root.frameHeight : 0" in MENU
assert "onLeftClicked: root.menuOpen = false" in MENU
assert "onVisibleChanged:" in EDITOR
assert "entryInput.focus = false;" in EDITOR

# The badge is not a fictional cloud connection; report the actual local
# file state and don't announce a pending atomic save as durable.
for phrase in ('"NO FEED"', '"LOCAL"', '"READING"', '"SAVING"',
               '"LOCKED"', '"UNSUP"'):
    assert phrase in MENU, phrase
assert "taskStoreState === \"saving\"" in MENU
assert "text: root.feedStatus" in MENU

# Each action stays in the existing guarded editor and asynchronous store.
for method in ("addTask(", "renameTask(", "setTaskDone(", "removeTask("):
    assert method in EDITOR, method
assert "todoStore.removeTask(task.id, true)" in EDITOR
assert 'confirmDeleteId === modelData.id' in EDITOR
assert "onTodoSnapshotChanged:" in EDITOR
assert 'storeState === "saving"' in EDITOR
assert "onSaveFailed: function(error)" in STORE
assert "onSaved:" in STORE
assert "atomicWrites: true" in STORE
assert "watchChanges: false" in STORE
assert 'Quickshell.dataDir + "/apollo-hub-todo-v1.json"' in STORE

# No added persistence, process, timer, sync or network side effect.
for token in ("FileView {", "JsonAdapter {", "Process {", "Timer {",
              "HttpClient", "XmlHttpRequest", "Quickshell.execDetached("):
    assert token not in MENU, token
assert STORE.count("FileView {") == 1
print("TASKS M3 shared-store/editor source contracts: PASS")
