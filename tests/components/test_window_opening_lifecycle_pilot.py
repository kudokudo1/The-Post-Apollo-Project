#!/usr/bin/env python3
"""Source guard for opt-in window opening A/B experiment.

This does NOT claim Qt/Wayland runtime correctness; live testing decides which
visibility policy may eventually become a shared default.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOTS = {
    "widgets/GitW.qml": "POST_APOLLO_GIT_VISIBILITY_PILOT",
    "widgets/HospitalW.qml": "POST_APOLLO_HOSPITAL_VISIBILITY_PILOT",
}

for path, env_name in PILOTS.items():
    src = (ROOT / path).read_text(encoding="utf-8")

    # The default stays permanently mapped; only an explicit 1 opts in.
    assert f'Quickshell.env("{env_name}")' in src, path
    assert '=== "1"' in src, path
    assert 'visible: !root.visibilityLifecyclePilot || root.menuOpen' in src, path

    # Both presentation strategies use the same closed click-through mask,
    # and retain their existing owner/keyboard policy.
    assert 'width: root.menuOpen ? root.width : 0' in src, path
    assert 'height: root.menuOpen ? root.height : 0' in src, path
    assert "WlrKeyboardFocus.None" in src, path
    assert "WlrKeyboardFocus.OnDemand" in src, path
    assert "WlrKeyboardFocus.Exclusive" in src, path
    assert "keyboardOwnershipRequested()" in src, path

    for pilot in (False, True):
        for opened in (False, True):
            visible = not pilot or opened
            interactive_region = opened
            if not pilot:
                assert visible  # Current default: mapped whether open/closed.
            else:
                assert visible == opened
            assert interactive_region == opened

# Keep known exceptions out of this initial experiment.
notifications = (ROOT / "widgets/notifications/NotificationsHubW.qml").read_text()
assert "visible: true" in notifications
assert "Repeated unmap/remap" in notifications
assert 'POST_APOLLO_GIT_VISIBILITY_PILOT' not in notifications
assert 'POST_APOLLO_HOSPITAL_VISIBILITY_PILOT' not in notifications

social = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
assert "FloatingWindow {" in social
assert "focusable: false" in social

print("WINDOW OPENING LIFECYCLE PILOT // SOURCE CONTRACTS PASS")
