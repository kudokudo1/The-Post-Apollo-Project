"""Static guards for Nurse 3c's additive universal keyboard navigation pilot.

These assertions do not replace live compositor/Qt keyboard-delivery tests.
"""
import re
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
    # Four standard Tab/Ctrl shortcuts plus two guarded legacy Up/Down aliases.
    assert src.count("enabled: root.standardModeKeysAvailable") == 6
    assert src.count("enabled: root.topSubModeKeysAvailable") == 2
    assert "function cycleTopSubMode(direction)" in src
    assert "gitChangesView.cycleSubMode(direction)" in src
    assert "gitHistoryView.cycleSubMode(direction)" in src
    assert "gitRepositoryView.cycleSubMode(direction)" in src
    assert "root.selectPrimaryMode(-1)" in src   # Shift+Up legacy
    assert "root.selectPrimaryMode(1)" in src    # Shift+Down legacy
    assert "context: Qt.WindowShortcut" in src
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


def test_nested_git_top_sub_modes_match_their_pointer_paths():
    for path, keys in (
        ("widgets/GitChangesView.qml",
         ["files", "hunks", "stashes", "conflicts"]),
        ("widgets/GitHistoryView.qml",
         ["log", "query", "reflog", "compare", "operate", "rebase", "surgery"]),
        ("widgets/GitRepositoryView.qml",
         ["remotes", "tags", "worktrees", "config", "files", "hooks", "health"]),
    ):
        src = read(path)
        assert "function selectSubMode(key)" in src, path
        assert "function cycleSubMode(direction)" in src, path
        assert "onTriggered: root.selectSubMode(modelData.key)" in src, path
        for key in keys:
            assert '"' + key + '"' in src, (path, key)
        assert "armedAction" in src or "clearArm()" in src, path
    assert "historyService.loadReflog();" in read(
        "widgets/GitHistoryView.qml")


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


def test_weather_domains_are_first_class_main_modes():
    src = read("widgets/weather/WeatherStationW.qml")

    for key in ("Tab", "Shift+Tab", "Up", "Down", "Enter", "Return"):
        assert 'sequence: "' + key + '"' in src

    # Domain pages are no longer a HOME-owned top Sub Mode family.
    assert 'sequence: "Shift+Left"' not in src
    assert 'sequence: "Shift+Right"' not in src
    assert "function cycleTopSubMode(direction)" not in src
    assert "property string activeDomain" not in src

    order_match = re.search(
        r"readonly property var mainModes:\s*\[([^\]]+)\]", src
    )
    assert order_match
    order = re.findall(r'"id":\s*"([^"]+)"', order_match.group(1))
    assert order == [
        "home", "ground", "sky", "space",
        "map", "news", "radio", "terminal",
    ]

    assert "function cycleMainMode(direction)" in src
    assert "function moveNavigationCursor(direction)" in src
    assert "function activateNavigationCursor()" in src
    assert "id: mainModeButton" in src
    assert "keyboardSelected:" in src
    assert "onPointerMoved:" in src
    assert "StationGround {" in src
    assert "StationSky {" in src
    assert "StationSpace {" in src
    assert "(!relationshipFocusModeActive || relationshipFocused)" in src
    assert "context: Qt.WindowShortcut" in src


def test_weather_keyboard_live_indicator_and_close_follow_shared_contract():
    src = read("widgets/weather/WeatherStationW.qml")

    assert "property bool keyboardActive: true" in src
    assert "property bool keyboardLock: false" in src
    assert "signal keyboardOwnershipRequested()" in src
    assert "id: weatherKeyboardAnchor" in src
    assert "WlrKeyboardFocus.OnDemand" in src
    assert "weatherStation.keyboardLock" in src
    assert "focusable:" in src
    assert "weatherStation.keyboardActive" in src
    assert "weatherStation.relationshipFocused" in src

    # Normal Weather Station chassis remains painted, but the Sway-hosted
    # terminal viewport needs a REAL alpha hole through the overlay.
    assert "fillVisible: !weatherStation.terminalHoleActive" in src
    assert "StationChassisCutout {" in src
    assert "visible: weatherStation.terminalHoleActive" in src
    assert "panelOpacity: 0.96" in src
    assert "borderVisible: true" in src
    assert "borderColor: Colors.cyan" in src

    assert "id: sourceStatusIndicator" in src
    assert 'return "WEATHER LIVE";' in src
    assert 'return "READING";' in src
    assert 'return "STALE";' in src
    assert 'return "OFFLINE";' in src
    assert "return Colors.magenta;" in src
    assert "weatherAgeMinutes >= 20" in src
    assert 'return sourceStatusText + " // " + ageText;' in src
    assert 'width: 150' in src
    assert 'font.pixelSize: 11' in src
    assert "id: focusButton" not in src
    assert 'label: "FOCUS"' not in src

    assert "id: closeButton" in src
    assert 'label: "×"' in src
    assert "accentColor: Colors.red" in src
    assert "destructive: true" in src


def test_notifications_tab_cycles_every_real_mode_in_visual_order():
    src = read("widgets/notifications/NotificationsHubW.qml")
    expected = ["all", "favorites", "apps", "social",
                "apollo", "system", "warning", "manager"]

    # Compare the Tab cycle against the actual left-to-right button row.
    order_match = re.search(
        r"readonly property var mainModeOrder:\s*\[([^\]]+)\]", src)
    assert order_match
    order = re.findall(r'"([^"]+)"', order_match.group(1))
    assert order == expected

    strip = src.split("id: filterStrip", 1)[1].split(
        "// New second header divider", 1)[0]
    visible_buttons = re.findall(r'filterId: "([^"]+)"', strip)
    assert visible_buttons == expected

    assert "function cycleMainMode(direction)" in src
    assert "mainModeOrder.indexOf(activeFilter)" in src
    assert "Number(direction) < 0 ? -1 : 1" in src
    assert "activeFilter = mainModeOrder[(current + step + count) % count];" in src
    assert 'onActivated: root.cycleMainMode(1)' in src
    assert 'onActivated: root.cycleMainMode(-1)' in src

    # Clicked mode is the starting state; each key advances to a neighbor,
    # and both directions wrap, rather than toggling back to Manager.
    for start in range(len(expected)):
        assert expected[(start + 1) % len(expected)] == order[
            (start + 1) % len(order)]
        assert expected[(start - 1) % len(expected)] == order[
            (start - 1) % len(order)]
    assert "lastHistoryFilter" not in src
    assert "function cycleTopSubMode" not in src
    assert 'sequence: "Shift+Left"' not in src
    assert 'sequence: "Shift+Right"' not in src


def test_notifications_non_destructive_list_navigation_stays_guarded():
    src = read("widgets/notifications/NotificationsHubW.qml")
    assert "function moveCurrentList(direction)" in src
    assert "listKeyboardSelectionActive" in src
    assert "function activateCurrentHistoryItem()" in src
    assert 'activeFilter === "manager"' in src
    assert 'root.activeFilter !== "manager"' in src
    assert "const index = !listKeyboardSelectionActive || list.currentIndex < 0" in src
    assert "historyList.currentIndex === notificationEntry.index" in src
    assert "ListView.isCurrentItem ? 2 : 1" in src
    # Enter follows the event's native default action when live, then
    # validated website origin or the original app focus. Never mutate state.
    assert "root.openNotificationDestination(" in src
    assert "row.notificationId, row.sourceId, row.source, row.websiteHost" in src
    assert 'root.takeMeToApp(sourceId, source);' in src
    for key in ("Tab", "Shift+Tab", "Enter", "Return", "Up", "Down"):
        assert 'sequence: "' + key + '"' in src
    assert "!searchInput.activeFocus" in src
    assert 'pendingClearAllKey === ""' in src
    assert src.count("context: Qt.WindowShortcut") >= 6
    assert "list.positionViewAtIndex(index, ListView.Contain)" in src


def test_notifications_focus_retry_and_key_delivery_guards():
    src = read("widgets/notifications/NotificationsHubW.qml")
    owner = read("components/KeyboardOwnershipCoordinator.qml")

    # The retry is one-shot, only when the notification surface has not
    # acquired real Qt window focus, and uses the existing bounded pulse.
    assert "id: notificationOpenFocusRetry" in src
    assert "interval: 48" in src
    assert "repeat: false" in src
    assert "notificationKeyboardAnchor.Window.active" in src
    assert "root.keyboardOwnershipRequested();" in src
    assert "notificationOpenFocusRetry.restart();" in src
    assert "notificationOpenFocusRetry.stop();" in src
    assert "root.menuOpen || !root.keyboardActive" in src
    assert "releaseBoost.restart()" in owner
    assert "interval: 120" in owner
    assert 'property string boostOwner: ""' in owner

    # Do not depend entirely on Qt.WindowShortcut: on a focused menu Qt
    # may otherwise consume Tab for its focus chain first.
    assert "id: notificationKeyboardAnchor" in src
    assert "Keys.priority: Keys.BeforeItem" in src
    assert "Keys.onShortcutOverride: function(event)" in src
    assert "Keys.onPressed: function(event)" in src
    assert "Qt.Key_Backtab" in src
    assert "root.cycleMainMode(reverse ? -1 : 1);" in src
    assert "event.accepted = true;" in src

    # We don't enlarge the focus pulse or change notification action guards.
    assert "WlrKeyboardFocus.OnDemand" in src
    assert 'root.activeFilter !== "manager"' in src
    assert "!searchInput.activeFocus" in src


def test_social_main_app_modes_use_existing_activate_path_and_protect_chat():
    src = read("widgets/messanger/MessagingW.qml")
    assert "event.key === Qt.Key_Tab" in src
    assert "event.key === Qt.Key_Backtab" in src
    assert "messagingWindow.focusZone !== messagingWindow.chatZone" in src
    # Family layouts can hide/reorder apps; Tab is restricted to visible
    # canonical app indices, while the host activateApp path stays unchanged.
    assert "appSelector.visibleAppIndices.length" in src
    assert "appSelector.nextActiveAppIndex(" in src
    assert "messagingWindow.activateApp(index);" in src
    assert "focusable: false" in src  # Controller layer, not Social FloatingWindow.
    assert "id: socialWindow" in src
    assert "restoreSelectorAfterDiscordShow" in src
    assert "onExited: function(exitCode, exitStatus)" in src
    assert "messagingWindow.syncSocialGeometry(true);" in src
    assert "messagingWindow.focusAppSelector();" in src
    assert "messagingWindow.activateApp(index, true);" in src
    assert "function activateApp(index, retainSelectorFocus)" in src
    assert "restoreSelectorAfterDiscordShow = false;" in src
    # Pointer activation still uses the original native focus behavior.
    assert "messagingWindow.activateApp(index);" in src


def test_focus_router_and_broker_still_independently_own_window_focus():
    router = read("scripts/koinoikos_focus.py")
    broker = read("components/RelationshipFocusBroker.qml")
    focus = read("docs/window-keyboard-focus-contract.md")
    assert "def nearest(" in router
    assert "def focus_target(" in router
    assert "function selectOwner(id)" in broker
    assert "Only one owner" in focus


if __name__ == "__main__":
    # Keep this runnable with stock Python in GitHub Actions and locally.
    count = 0
    for name, candidate in list(globals().items()):
        if name.startswith("test_") and callable(candidate):
            candidate()
            count += 1
    print(f"SYNTAGMA UNIFIED KEYS // {count} source contracts PASS")
