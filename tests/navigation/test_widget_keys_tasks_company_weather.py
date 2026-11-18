"""Keyboard owners: TASKS and Company main-mode rails, Weather lower tabs.

Static source gates supplement, not replace, native Wayland key delivery.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def check_window_local_modes(relative, frame, mode_count):
    source = read(relative)
    assert f"readonly property bool standardModeKeysAvailable:" in source
    assert f"root.menuOpen && root.activeFocusItem === {frame}" in source
    assert f"{frame}.forceActiveFocus();" in source
    assert "Keys.onShortcutOverride: function(event)" in source
    assert "Keys.onPressed: function(event)" in source
    assert "event.key === Qt.Key_Tab" in source or "event.key===Qt.Key_Tab" in source
    assert "Qt.Key_Backtab" in source
    assert "function cycleMainMode(direction)" in source
    assert "function moveNavigationCursor(direction)" in source
    assert "function activateNavigationCursor()" in source
    assert "keyboardSelected: root.keyboardModeCursor === index" in source
    assert "keyboardActive: root.standardModeKeysAvailable" in source
    assert "property int keyboardModeCursor: 0" in source
    # TASKS security forbids window-wide shortcuts; Company follows the
    # same frame-only approach to protect native map and editing controls.
    assert 'context: Qt.WindowShortcut' not in source
    assert "Shortcut {" not in source
    assert "root.cycleMainMode(reverse ? -1 : 1)" in source
    assert "root.moveContentKey(event.key,event.modifiers)" in source
    assert "root.activateNavigationCursor()" in source
    for forbidden in ('sequence: "Ctrl+Left"', 'sequence: "Ctrl+Right"',
                      'sequence: "Shift+Left"', 'sequence: "Shift+Right"'):
        assert forbidden not in source, (relative, forbidden)
    # Tab owns main modes. Plain arrows/HJKL select a content control,
    # not a rail button, and Enter never commits an arbitrary destructive act.
    assert "WidgetContentKeyboardNavigator {" in source
    assert "function moveContentKey(key,modifiers)" in source
    assert "contentKeyboardSelectorItem" in source
    assert all(key in source for key in
               ("Qt.Key_H", "Qt.Key_J", "Qt.Key_K", "Qt.Key_L"))
    cursor = source.split("function moveNavigationCursor(direction)", 1)[1]
    cursor = cursor.split("function activateNavigationCursor()", 1)[0]
    assert "ContentKeys.move" in cursor
    activate = source.split("function activateNavigationCursor()", 1)[1]
    activate = activate.split("function ", 1)[0]
    assert "ContentKeys.activate()" in activate
    assert "selectMainMode(keyboardModeCursor)" not in source
    assert source.count("onMenuOpenChanged:") == 1
    assert "WlrKeyboardFocus.OnDemand" in source
    assert "WlrKeyboardFocus.Exclusive" not in source
    assert source.count("FileView {") == 0
    assert source.count("Process {") == 0
    assert source.count("property int selectedMainModeIndex") == 1
    assert ("onTriggered: {" in source
            or "onTriggered: root.selectMainMode(index)" in source)
    labels = re.findall(r'\{ id: "([^"]+)", label: "([^"]+)"', source)
    assert len(labels) == mode_count, (relative, labels)


def test_tasks():
    check_window_local_modes("widgets/TasksW.qml", "tasksFrame", 5)
    source = read("widgets/TasksW.qml")
    # Original store and child editor keep ownership. We do not bind Return
    # to completion, new-task creation, or a write through the shared store.
    assert "ApolloHubTodoStore.snapshot" in source
    assert "taskEditor.unsavedLocalEntryDraft" in source
    assert "Keys.onEscapePressed: function(event)" in source
    assert "onEntryEscapeReleased:" in source
    assert "TaskDetailsPane {" in source
    assert "TaskTodayPane {" in source
    assert "TaskProjectsPane {" in source
    assert "TaskPlannerPane {" in source
    assert "TaskSyncConnectionsPane {" in source
    assert "root.activeFocusItem === tasksFrame" in source


def test_company():
    check_window_local_modes("widgets/CompanyNetworkW.qml", "companyFrame", 4)
    source = read("widgets/CompanyNetworkW.qml")
    assert "root.activeFocusItem === companyFrame" in source
    assert "CompanyVectorBridgeLink {" in source
    assert "CompanyCoveragePane {" in source
    assert "vectorBridgeOptIn: false" in source
    assert "coverageLoaded = true;" in source
    assert "Keys.onEscapePressed: function(event)" in source


def test_weather_actual_bottom_tabs():
    navigator = read("widgets/weather/StationSubjectNavigator.qml")
    station = read("widgets/weather/WeatherStationW.qml")
    policy = read("widgets/weather/StationWorkspaceNavigationPolicy.js")
    assert "function cycleWorkspaceTab(direction)" in navigator
    assert "if(indexOpen) return false" in navigator
    assert "Workspace.tabsFor(currentPath)" in navigator
    assert "Workspace.selectedGroup(currentPath)" in navigator
    assert "chooseRoute(tabs[next].path)" in navigator
    assert "function cycleBottomSubMode(direction)" in station
    assert "subjectNavigator.cycleWorkspaceTab(direction)" in station
    assert "if (!standardKeysAvailable || !weatherKeyboardAnchor.activeFocus" in station
    assert "&& weatherKeyboardAnchor.activeFocus" in station
    for name in ("Ctrl+Left", "Ctrl+Right"):
        assert f'sequence: "{name}"' in station
    assert "Qt.ControlModifier" in station
    assert "Keys.onShortcutOverride: function(event)" in station
    assert "Keys.onPressed: function(event)" in station
    # Shift+arrow is not silently assigned to a non-existent global top rail.
    assert 'sequence: "Shift+Left"' not in station
    assert 'sequence: "Shift+Right"' not in station
    assert "function familySwitchTarget(" in policy
    assert "function servicesTabFor(" in policy


def test_finance_actual_lower_sections():
    source = read("widgets/FinanceW.qml")
    assert "function cycleBudgetSection(direction)" in source
    assert "function selectBudgetSection(section)" in source
    assert "return selectBudgetSection(" in source
    assert 'const sections = ["budget","transactions","accounts","categories"]' in source
    assert "selectedMainMode === \"budget\"" in source
    assert "selectedBudgetSubMode === \"budget\"" in source
    assert "financeKeyboardAnchor.activeFocus" in source
    assert "!quickAddPane.open" in source
    assert "root.lowerSectionKeysAvailable" in source
    assert "Qt.ControlModifier" in source
    for key in ("Ctrl+Left", "Ctrl+Right"):
        assert f'sequence: "{key}"' in source
    compact = source.replace(" ", "").replace("\\n", "")
    assert 'financeWrite.state==="pending"' in compact
    assert 'transactionDraftPane.open&&section!=="transactions"' in compact
    assert 'onLeftClicked: root.selectBudgetSection(modelData.key)' in source
    assert "onActivated: root.cycleBudgetSection(-1)" in source
    assert "onActivated: root.cycleBudgetSection(1)" in source


if __name__ == "__main__":
    tests = [test_tasks, test_company, test_weather_actual_bottom_tabs,
             test_finance_actual_lower_sections]
    for test in tests:
        test()
    print(f"UNIFIED WIDGET KEYS // {len(tests)} focused source contracts PASS")
