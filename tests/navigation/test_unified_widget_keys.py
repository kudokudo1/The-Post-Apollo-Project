"""Static guards for Nurse 3c's additive universal keyboard navigation pilot.

These assertions do not replace live compositor/Qt keyboard-delivery tests.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_universal_contract_preserves_koinoikos_scope():
    docs = read("docs/unified-widget-keyboard-navigation.md")
    assert "Super + ~" in docs
    assert "`Mod4+grave`" in docs
    assert "Tab" in docs and "Shift+Tab" in docs
    assert "Shift+Left/Right" in docs and "Ctrl+Left/Right" in docs
    assert "contextual selector" in docs
    assert "Koinoikos" in docs


def test_git_main_and_visible_lower_mode_keys_are_window_local():
    src = read("widgets/GitW.qml")
    assert "readonly property bool standardModeKeysAvailable" in src
    for key in ("Tab", "Shift+Tab", "Ctrl+Left", "Ctrl+Right"):
        assert 'sequence: "' + key + '"' in src
    assert src.count("enabled: root.standardModeKeysAvailable") == 4
    assert src.count("context: Qt.WindowShortcut") >= 4
    assert "function cycleMainMode(direction)" in src
    assert "function cycleVisibleSubMode(direction)" in src
    for action in (
        "showGitControl()", "showGitBranches()", "showGitChanges()",
        "showGitHistory()", "showGitRepository()", "showGitOperations()",
    ):
        assert action in src
    assert "selectBottomMode(direction)" in src
    # Git's contextual history back must not be overwritten by mode cycling.
    assert 'sequence: "Alt+Left"' in src
    assert "goBackGitNavigation()" in src
    for guarded in ("!root.activeTextEditor", "!root.dialControlMode",
                    "!root.workflowMenuOpen", "!root.runInspectorOpen"):
        assert guarded in src


def test_cpu_mode_and_monitor_keys_are_window_local():
    src = read("widgets/CpuPlusW.qml")
    assert "readonly property bool standardKeysAvailable" in src
    for key in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right", "Up", "Down"):
        assert 'sequence: "' + key + '"' in src
    assert "function cycleMainMode(direction)" in src
    assert "function cycleTopSubMode(direction)" in src
    assert "function cycleMonitorRow(direction)" in src
    assert "choices.findIndex" in src
    assert "return !choice.spacer;" in src
    assert "selectMonitorRow(" in src
    assert "(!relationshipFocusModeActive || relationshipFocused)" in src
    assert "context: Qt.WindowShortcut" in src
    # No bottom submode is invented merely to consume Ctrl arrows.
    assert 'sequence: "Ctrl+Right"' not in src


def test_weather_semantic_main_and_top_submode_and_arrow_preview():
    src = read("widgets/weather/WeatherStationW.qml")
    for key in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right",
                "Up", "Down", "Enter", "Return"):
        assert 'sequence: "' + key + '"' in src
    assert "function cycleMainMode(direction)" in src
    assert "function cycleTopSubMode(direction)" in src
    assert 'const pages = ["home"].concat(views.map' in src
    assert "function moveNavigationCursor(direction)" in src
    assert "function activateNavigationCursor()" in src
    for qml in ("id: homeButton", "id: domainButton", "id: viewButton"):
        assert qml in src
    assert src.count("keyboardSelected: weatherStation.navigationIndex") == 3
    assert src.count("onPointerMoved: weatherStation.navigationIndex") == 3
    assert "(!relationshipFocusModeActive || relationshipFocused)" in src
    assert "context: Qt.WindowShortcut" in src


def test_notifications_non_destructive_context_and_filter_keys():
    src = read("widgets/notifications/NotificationsHubW.qml")
    assert "function cycleMainMode()" in src
    assert "function cycleTopSubMode(direction)" in src
    assert "function moveCurrentList(direction)" in src
    assert "lastHistoryFilter" in src
    assert "!searchInput.activeFocus" in src
    assert 'pendingClearAllKey === ""' in src
    for key in ("Tab", "Shift+Tab", "Shift+Left", "Shift+Right",
                "Up", "Down"):
        assert 'sequence: "' + key + '"' in src
    assert src.count("context: Qt.WindowShortcut") >= 6
    assert "list.positionViewAtIndex(index, ListView.Contain)" in src


def test_social_main_app_modes_use_existing_activate_path_and_protect_chat():
    src = read("widgets/messanger/MessagingW.qml")
    assert "event.key === Qt.Key_Tab" in src
    assert "event.key === Qt.Key_Backtab" in src
    assert "messagingWindow.focusZone !== messagingWindow.chatZone" in src
    assert "appSelector.messagingApps.length" in src
    assert "messagingWindow.activateApp(index);" in src
    assert "focusable: false" in src  # Focus lane owns registration.


def test_focus_router_and_broker_still_independently_own_window_focus():
    router = read("scripts/koinoikos_focus.py")
    broker = read("components/RelationshipFocusBroker.qml")
    focus = read("docs/window-keyboard-focus-contract.md")
    assert "def nearest(" in router
    assert "def focus_target(" in router
    assert "function selectOwner(id)" in broker
    assert "Only one owner" in focus
