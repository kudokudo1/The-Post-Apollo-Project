#!/usr/bin/env python3
"""Guard the bounded non-CPU sampled-glow normalization slice."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

# Guard actual sampled items while preserving intentional per-widget layering.
# Duplicate entries are deliberate when more than one semantic effect samples
# the same visible source.
SURFACES = {
    "modules/Clock.qml": (
        "clockLeftStar",
        "clockIcon",
        "clockRightStar",
        "clockHour",
        "clockColon",
        "clockMinute",
        "clockPeriodSeparator",
        "clockPeriod",
    ),
    "modules/Volumebar.qml": (
        "volumebarIcon",
        "volumebarText",
    ),
    "modules/Workspaces.qml": (
        "workspacesButtonBackground",
        "workspacesText",
        "workspacesText",
    ),
}

for relative, sources in SURFACES.items():
    qml = (ROOT / relative).read_text(encoding="utf-8")
    direct = re.findall(r"(?m)^\s*DropShadow\s*\{", qml)
    safe = re.findall(r"(?m)^\s*SafeDropShadow\s*\{", qml)

    assert not direct, f"{relative}: unguarded source-attached DropShadow"
    assert len(safe) == len(sources), (
        f"{relative}: expected {len(sources)} guarded sampled glows, "
        f"found {len(safe)}"
    )

    for source in set(sources):
        expected = sources.count(source)
        actual = len(re.findall(rf"(?m)^\s*safeSource:\s*{re.escape(source)}\s*$", qml))
        assert actual == expected, (
            f"{relative}: expected {expected} safeSource attachment(s) "
            f"for {source}, found {actual}"
        )

workspaces = (ROOT / "modules/Workspaces.qml").read_text(encoding="utf-8")
assert workspaces.count("id: workspacesTextGlow") == 1
assert workspaces.count("id: workspacesActiveTextGlow") == 1
assert "visible: workspacesWorkspaceButton.isActive" in workspaces
assert "color: Colors.cyan" in workspaces
assert "color: workspacesText.workspaceColor" in workspaces
assert "workspacesButtonMouse.pressed ? 1.0" in workspaces
assert "workspacesButtonMouse.containsMouse ? 0.95" in workspaces

clock = (ROOT / "modules/Clock.qml").read_text(encoding="utf-8")
for source in (
    "clockLeftStar",
    "clockIcon",
    "clockRightStar",
    "clockHour",
    "clockColon",
    "clockMinute",
    "clockPeriodSeparator",
    "clockPeriod",
):
    assert f"id: {source}" in clock
    assert f"safeSource: {source}" in clock

# Closed Clock keeps cyan for 12-hour and orange for 24-hour readings.
# TimeW-open inherits the canonical yellow dock fill and magenta open glow:
# each source-sampled glyph must follow the bound DockButton color. The four
# structural marks are white/muted while closed and magenta while open.
assert "open: clockArea.timeWindow !== null" in clock
assert "&& clockArea.timeWindow.menuOpen === true" in clock
assert "clockArea.is24Hour ? Colors.orange : Colors.cyan" in clock
assert "normalDockGlowColor: normalForegroundColor" in clock
assert "normalContentGlowColor: normalDockGlowColor" in clock
assert clock.count("color: clockButton.foregroundColor") == 4
assert clock.count("color: clockButton.contentGlowColor") == 8
assert 'Qt.formatDateTime(clock.date, "hh AP").split(" ")[0]' in clock
assert 'Qt.formatDateTime(clock.date, "HH")' in clock
assert 'text: "//"' in clock
assert "width: clockPeriodSeparator.implicitWidth + 4" in clock
assert 'text: Qt.formatDateTime(clock.date, "AP")' in clock
assert '? "24H"' not in clock
assert "property int contentLeftPadding: 2" in clock
assert "property int contentRightPadding: 4" in clock
assert "Math.ceil(clockRow.implicitWidth)" in clock
assert "+ contentLeftPadding" in clock
assert "+ contentRightPadding" in clock
assert "(clockButton.contentLeftPadding" in clock
assert "- clockButton.contentRightPadding) / 2" in clock
assert clock.count("? clockButton.openForegroundColor : Colors.white") == 4
assert clock.count("opacity: clockButton.open ? 1.0 : 0.6") == 4
assert clock.count("radius: 8") >= 4
assert clock.count("samples: 15") >= 8
assert clock.count("opacity: 1.0") >= 4
period_start = clock.index("id: clockPeriod\n")
period_end = clock.index("SafeDropShadow", period_start)
period_text = clock[period_start:period_end]
assert "color: Colors.white" not in period_text
assert "opacity: 0.6" not in period_text
assert "color: clockButton.foregroundColor" in period_text
assert "font.pixelSize: 11" not in clock
assert "font.pixelSize: 17" not in clock
assert "font.pixelSize: 20" in clock
assert "color: Colors.magenta" not in clock
assert "color: Colors.yellow" not in clock

print("Non-CPU sampled-glow structural contracts: PASS")
