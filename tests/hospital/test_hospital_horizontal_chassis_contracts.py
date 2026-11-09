#!/usr/bin/env python3
"""Source contracts for horizontally resizable, full-height Hospital chassis."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
host = (ROOT / "widgets/HospitalW.qml").read_text()
policy = (ROOT / "services/hospital/HospitalHorizontalChassisPolicy.js").read_text()
checks = []

def check(ok, description):
    if not ok:
        checks.append(description)

check('PanelWindow {' in host and 'WindowPanelFrame {' in host,
      "Hospital must resize the existing mapped PanelWindow and frame")
check('property int panelWidthLevel: 0' in host
      and 'readonly property int panelWidth: SurgeryWidthPolicy.panelWidth(' in host,
      "Default size and width policy must bind one window's panelWidth")
check('root.screen ? root.screen.width' in host
      and 'panelLeftMargin, glowGutter' in host,
      "Width must be clamped against the active display and glow margins")
check('function stepHospitalWidth(direction)' in host
      and 'panelWidthLevel = next;' in host,
      "Size arrows must update horizontal geometry in place")
check('implicitWidth: panelWidth + glowGutter * 2' in host
      and 'width: root.panelWidth' in host
      and 'anchors.horizontalCenter: parent.horizontalCenter' in host,
      "Window and visible frame widths must share the same size state")
check('top: true' in host and 'bottom: true' in host
      and 'left: true' in host and 'right: false' in host,
      "Hospital remains left anchored and full height")
check('property int panelHeight: Math.max(1, height - frameInset * 2)' in host
      and 'height: root.panelHeight' in host,
      "Width changes must not replace compositor-controlled height")
check('visible: true' in host
      and 'width: root.menuOpen ? root.width : 0' in host
      and 'height: root.menuOpen ? root.height : 0' in host,
      "Permanent map and click-through closed input mask must remain")
check('id: hospitalHeaderActions' in host
      and 'id: narrowHospitalButton' in host
      and 'id: widenHospitalButton' in host,
      "Arrows must live in the existing header action row")
check('label: "←"' in host
      and 'label: "→"' in host
      and 'available: root.canNarrowHospital' in host
      and 'available: root.canWidenHospital' in host,
      "Left and right size arrows must respect available size")
check('root.stepHospitalWidth(-1);' in host
      and 'root.stepHospitalWidth(1);' in host,
      "Arrow activation must only adjust a width level")
check('contentGlowEnabled: false' in host.split('id: narrowHospitalButton',1)[1][:420]
      and 'contentGlowEnabled: false' in host.split('id: widenHospitalButton',1)[1][:420],
      "Avoid offset dual text shadows on new size arrows")
check('right: hospitalHeaderActions.left' in host
      and 'elide: Text.ElideRight' in host,
      "Long title must not overlap header size buttons on compact")
check('const HOSPITAL_WIDTH_STEPS = [744, 984, 1224, 1464]' in policy
      and 'function canStep(' in policy
      and 'function displayBudget(' in policy,
      "Four horizontal size levels must be display-clamped and no-op aware")
for forbidden in ('session-succeed', 'session-create', 'assignment-activate',
                  'px agent turn', 'orchestrate-ready'):
    check(forbidden not in policy,
          "Pure width policy cannot contain runtime commands: " + forbidden)

if checks:
    print("HOSPITAL HORIZONTAL CHASSIS // FAIL")
    for message in checks:
        print(" - " + message)
    raise SystemExit(1)
print("HOSPITAL HORIZONTAL CHASSIS // PASS // full-height mapped resize and isolated arrow controls")
