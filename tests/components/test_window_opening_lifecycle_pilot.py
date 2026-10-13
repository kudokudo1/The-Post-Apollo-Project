#!/usr/bin/env python3
"""Regression guard: do not revive the crashing Git/Hospital unmap pilot.

Live operator A/B evidence (2026-10-13): both widgets crashed after repeated
open/close cycles or rapid clicking with visibility-controlled unmap/remap.
This source check protects the known working mapping policy; it does not
diagnose the underlying Qt/Wayland crash.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

for path, removed_flag in (
    ("widgets/GitW.qml", "POST_APOLLO_GIT_VISIBILITY_PILOT"),
    ("widgets/HospitalW.qml", "POST_APOLLO_HOSPITAL_VISIBILITY_PILOT"),
):
    src = (ROOT / path).read_text(encoding="utf-8")
    assert removed_flag not in src, path
    assert "visibilityLifecyclePilot" not in src, path
    assert "visible: true" in src, path
    assert "visible: root.menuOpen" not in src, path
    assert "visible: menuOpen" not in src, path

    # A permanently mapped closed menu must still be click-through and
    # must not hold the keyboard just because the native window exists.
    assert 'width: root.menuOpen ? root.width : 0' in src, path
    assert 'height: root.menuOpen ? root.height : 0' in src, path
    for mode in ("None", "OnDemand", "Exclusive"):
        assert "WlrKeyboardFocus." + mode in src, path
    assert "keyboardOwnershipRequested()" in src, path

# Recorded exception: notification remapping previously caused a native crash.
notifications = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
assert "visible: true" in notifications
assert "Repeated unmap/remap" in notifications

# Native window presentation is an intentional Social-specific requirement.
social = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
assert "FloatingWindow {" in social
assert "focusable: false" in social

report = (ROOT / "docs/window-opening-lifecycle-pilot.md").read_text()
assert "FAIL" in report and "October 13, 2026" in report

print("WINDOW OPENING LIFECYCLE // FAILED PILOT RETIRED, SAFE DEFAULT GUARDED")
