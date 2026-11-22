#!/usr/bin/env python3
"""Source contract for native shared ResizeButton rollout, no production resizing.

Audit window chassis controls throughout modules/widgets/components and prove
that each registered consumer retains its own direction, boundary and callback.
This intentionally does not replace chart navigation, download or scroll arrows.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

# (source, component id, semantic direction, enabled expression, owner callback)
CONTROLS = (
    ("widgets/FinanceW.qml", "collapseChassisButton", "down", 'root.chassisLevel !== "compact"', "root.collapseChassis();"),
    ("widgets/FinanceW.qml", "expandChassisButton", "up", 'root.chassisLevel !== "fullscreen"', "root.expandChassis();"),
    ("widgets/CompanyNetworkW.qml", "collapseChassisButton", "down", 'root.chassisLevel !== "compact"', "root.collapseChassis();"),
    ("widgets/CompanyNetworkW.qml", "expandChassisButton", "up", 'root.chassisLevel !== "fullscreen"', "root.expandChassis();"),
    ("widgets/TasksW.qml", "collapseChassisButton", "down", 'root.chassisLevel !== "compact"', "root.collapseChassis();"),
    ("widgets/TasksW.qml", "expandChassisButton", "up", 'root.chassisLevel !== "large"', "root.expandChassis();"),
    ("widgets/CameraW.qml", "cameraCollapseButton", "down", 'camera.chassisLevel !== "compact"', "camera.collapseChassis();"),
    ("widgets/CameraW.qml", "cameraExpandButton", "up", 'camera.chassisLevel !== "fullscreen"', "camera.expandChassis();"),
    ("modules/Trash.qml", "collapseTrashButton", "down", 'trashLauncher.chassisSize !== "compact"', "trashLauncher.stepChassis(-1);"),
    ("modules/Trash.qml", "expandTrashButton", "up", 'trashLauncher.chassisSize !== "full"', "trashLauncher.stepChassis(1);"),
    ("widgets/weather/WeatherStationW.qml", "collapseChassisButton", "down", 'weatherStation.chassisLevel !== "compact"', "weatherStation.collapseChassis();"),
    ("widgets/weather/WeatherStationW.qml", "expandChassisButton", "up", 'weatherStation.chassisLevel !== "fullscreen"', "weatherStation.expandChassis();"),
    ("widgets/HospitalW.qml", "narrowHospitalButton", "left", "root.canNarrowHospital", "root.stepHospitalWidth(-1);"),
    ("widgets/HospitalW.qml", "widenHospitalButton", "right", "root.canWidenHospital", "root.stepHospitalWidth(1);"),
)


def block_at_id(source, ident):
    lines = source.splitlines()
    indices = [i for i, line in enumerate(lines) if line.strip() == f"id: {ident}"]
    assert len(indices) == 1, f"unique control {ident}: {len(indices)}"
    idx = indices[0]
    assert idx > 0 and lines[idx - 1].strip() == "ResizeButton {", ident
    start = idx - 1
    indent = lines[start][: len(lines[start]) - len(lines[start].lstrip())]
    for end in range(idx + 1, len(lines)):
        if lines[end] == indent + "}":
            return "\n".join(lines[start : end + 1])
    raise AssertionError(f"unclosed resize component {ident}")


seen_sources = {}
for path, ident, direction, enabled, callback in CONTROLS:
    source = seen_sources.setdefault(path, (ROOT / path).read_text(encoding="utf-8"))
    block = block_at_id(source, ident)
    sign = -1 if direction in ("down", "left") else 1
    assert f'direction: "{direction}"' in block, (path, ident, "direction")
    assert enabled in block, (path, ident, "boundary")
    assert "onResizeRequested: function(delta)" in block, (path, ident, "signal")
    assert f"if (delta !== {sign})" in block, (path, ident, "sign guard")
    assert callback in block, (path, ident, "owner callback")
    assert "onLeftClicked:" not in block, (path, ident)
    assert not re.search(r'(?m)^\s*(?:label|accentColor|height):', block), (path, ident, "shared presentation override")
    if path == "modules/Trash.qml":
        assert "width: 28" in block, (path, ident, "compact width")
    else:
        assert not re.search(r'(?m)^\s*width:', block), (path, ident, "shared 30px width")
    if path in ("widgets/FinanceW.qml", "widgets/HospitalW.qml"):
        assert "root.keyboardOwnershipRequested();" in block, (path, ident, "focus")


# A source-wide audit catches old labeled chassis arrows in any QML host.
# Do not flag unrelated arrow controls for lists, downloads or chart navigation.
legacy = []
for directory in ("widgets", "modules", "components"):
    for path in (ROOT / directory).rglob("*.qml"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.strip() != "ActionButton {":
                continue
            indent = line[: len(line) - len(line.lstrip())]
            for j in range(i + 1, len(lines)):
                if lines[j] == indent + "}":
                    block = "\n".join(lines[i : j + 1])
                    if re.search(r'(?m)^\s*label:\s*"[↑↓←→⮜⮝⮟➤]"', block) and re.search(
                        r'\b(?:collapseChassis|expandChassis|stepChassis|stepHospitalWidth)\s*\(', block
                    ):
                        legacy.append(f"{path.relative_to(ROOT)}:{i + 1}")
                    break
assert not legacy, "Legacy chassis ActionButtons remain: " + ", ".join(legacy)

hospital = seen_sources["widgets/HospitalW.qml"]
assert hospital.count("ResizeButton {") == 2, "Hospital must use horizontal pair only"
assert "root.keyboardOwnershipRequested();" in block_at_id(hospital, "narrowHospitalButton")
assert "root.keyboardOwnershipRequested();" in block_at_id(hospital, "widenHospitalButton")

shared = (ROOT / "components/ResizeButton.qml").read_text(encoding="utf-8")
assert "property color decreaseAccentColor: Colors.orange" in shared
assert 'property color increaseAccentColor: "#A46AFF"' in shared
assert 'label: direction === "left" ? "⮜"' in shared
assert 'direction === "up" ? "⮝"' in shared
assert 'direction === "right" ? "➤"' in shared
assert '"⮟"' in shared
assert "pressedFillColor: accentColor" in shared
assert "pressedBorderColor: Colors.black" in shared
assert "pressedForegroundColor: Colors.black" in shared

print(f"Universal chassis resize rollout PASS: {len(CONTROLS)} controls in {len(seen_sources)} hosts")
