#!/usr/bin/env python3
"""Source-only regression for keyboard input in explicit QS test windows.

This does not launch native Quickshell, change sway, restart a desktop, or
authorize production TASKS storage activity.
"""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[2]
tasks=(root/"widgets/TasksW.qml").read_text()
assert "WlrKeyboardFocus.OnDemand" in tasks
assert "focusable:" in tasks

targets=["TaskFileViewHostHarnessM11g.qml",
         "TaskFileViewGateHarnessM11e.qml"]
for name in targets:
    source=(root/name).read_text()
    assert "import Quickshell.Wayland" in source,name
    assert "PanelWindow {" in source,name
    assert re.search(r"\bfocusable\s*:\s*true\b",source),name
    assert re.search(
        r"\bWlrLayershell\.keyboardFocus\s*:\s*WlrKeyboardFocus\.OnDemand\b",
        source),name
    assert "WlrKeyboardFocus.Exclusive" not in source,name
    assert "exclusiveZone: 0" in source,name
    assert "TextInput {" in source,name
    assert re.search(r"\bTextInput\s*\{[^{}]*\bfocus\s*:\s*true\b",
                     source,re.DOTALL),name
    assert "selectByMouse: true" in source,name
    for forbidden in ("ApolloHubTodoStore","Quickshell.dataDir",
                      "Component.onCompleted:", "Timer {",
                      "WlrKeyboardFocus.Exclusive"):
        assert forbidden not in source,(name,forbidden)
    print(name, "ON_DEMAND_KEYBOARD_FOCUS_PRESENT")

# No production-task window has to be changed to fix this test-only issue.
print("M11 native FileView test focus regression: PASS (static source only)")
