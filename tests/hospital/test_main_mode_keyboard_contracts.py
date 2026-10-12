#!/usr/bin/env python3
"""Hospital Main Mode keyboard contract: Tab cycles tabs, not Floor/Room/Bed."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
host = (ROOT / "widgets/HospitalW.qml").read_text(encoding="utf-8")
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


def required(needle, description):
    check(needle in host, description + ": missing " + repr(needle))


expected = [
    ("reception", "RECEPTION", "openReception"),
    ("surgery", "SURGERY", "showSurgery"),
    ("attention", "ATTENTION", "openAttention"),
    ("archive", "ARCHIVE", "openArchive"),
    ("reports", "REPORTS", "openReports"),
    ("rounds", "ROUNDS", "openRounds"),
    ("staff", "STAFF", "openStaff"),
]

rail = host.split("id: hospitalModeTabs", 1)
check(len(rail) == 2, "Hospital must retain its seven-tab Main Mode rail")
if len(rail) == 2:
    rail = rail[1].split("id: departmentContextStrip", 1)[0]
    labels = re.findall(r'label:\s*"([A-Z]+)"', rail)
    check(labels == [row[1] for row in expected],
          "Main Mode order must match the visible seven tabs")
    for _, _, action in expected:
        required("onTriggered: root." + action + "()",
                 "Keep existing tab click handlers")

start = host.find("readonly property var mainModeOrder:")
end = host.find('sequence: "Esc"', start)
check(start >= 0 and end > start, "Main Mode key contract must precede Esc shortcut")
if start >= 0 and end > start:
    section = host[start:end]
    key_order = re.findall(r'"(reception|surgery|attention|archive|reports|rounds|staff)"',
                           section.split("readonly property bool mainModeKeysAvailable:", 1)[0])
    check(key_order == [row[0] for row in expected],
          "Keyboard cycle order must match actual visual Main Mode tabs")

    for condition in (
        "root.menuOpen", "root.keyboardActive", "keyboardFocusAnchor.activeFocus",
        "!root.intercomTyping", "!root.receptionistTyping",
        "!root.intercomMenuOpen", "!root.phoneMenuOpen",
        'root.operationsSurface === ""',
        "root.mainModeOrder.indexOf(root.operationsSurface) >= 0",
    ):
        check(condition in section, "Main Mode focus/surface guard: " + condition)

    for segment in (
        'sequence: "Tab"',
        'onActivated: root.cycleHospitalMainMode(1)',
        'sequence: "Shift+Tab"',
        'onActivated: root.cycleHospitalMainMode(-1)',
        "enabled: root.mainModeKeysAvailable",
        'root.operationsSurface === ""',
        'const target = root.mainModeOrder[(index + step + count) % count];',
        "if (!mainModeKeysAvailable)",
    ):
        check(segment in section, "Keyboard shortcut/mode cycle: " + segment)

    for key, _, action in expected:
        check("target === " + repr(key).replace("'", '"') in section,
              "Main Mode dispatcher lacks: " + key)
        check("root." + action + "();" in section,
              "Main Mode must use existing opener: " + action)
    for forbidden in ("cycleFloor(", "cycleBed(", "cycleRoom(",
                      "performRoomControl(", "invokeMoveBed(",
                      "floorService.selectFloor(", "floorService.selectBed("):
        check(forbidden not in section, "Tab routing must not change selectors: " + forbidden)

# Preserve existing in-context Floor/Room/Bed keybindings and their safety gates.
for old in (
    'onActivated: root.moveRoomControl(-1, 0)',
    'onActivated: root.moveRoomControl(1, 0)',
    'onActivated: root.moveRoomControl(0, -1)',
    'onActivated: root.moveRoomControl(0, 1)',
    'onActivated: root.cycleBed(-1)',
    'onActivated: root.cycleBed(1)',
    'onActivated: root.handleRoomEnter()',
    "if (!floorSwitchEnabled)", "if (!bedSwitchEnabled)",
    "function enterRoomControls()", "function enterBedControls()",
):
    required(old, "Existing Hospital navigation unchanged")

if errors:
    print("HOSPITAL MAIN MODE KEYBOARD // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)

print("HOSPITAL MAIN MODE KEYBOARD // PASS")
print("seven Main Modes, forward/reverse wrap, focus safety, old selector keys")
