#!/usr/bin/env python3
"""Static contracts for the reusable NeonScrollBar component."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPONENT = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")


def require(text: str, needle: str, message: str) -> None:
    assert needle in text, f"{message}: missing {needle!r}"


for needle, message in (
    ('property string handleStyle: "bar"', "single switchable handle-style API"),
    ('String(root.handleStyle || "").toLowerCase() === "star"', "star style selection"),
    ("property color railColor: Colors.cyan", "canonical cyan rail default"),
    ("property color handleColor: Colors.magenta", "canonical magenta handle default"),
    ("property int railWidth: 3", "canonical rail width"),
    ("property int barHandleWidth: 7", "canonical bar handle width"),
    ("property int minimumHandleHeight: 24", "canonical minimum handle height"),
    ("property int starHandleSize: 14", "canonical star handle size"),
    ("property real railOpacity: 0.82", "canonical rail opacity"),
    ("property real barGlowIdleOpacity: 0.42", "canonical bar glow"),
    ("property real starGlowIdleOpacity: 0.52", "canonical star glow"),
    ("property Component railDecoration: null", "semantic rail decoration extension point"),
    ("property bool interactive: true", "interaction toggle"),
    ("property bool wheelEnabled: true", "wheel toggle"),
    ("property bool autoHide: true", "visibility policy"),
    ("sourceComponent:", "single loader-backed handle"),
):
    require(COMPONENT, needle, message)

assert "property bool starHandle" not in COMPONENT, "legacy starHandle boolean must be removed"

star_users = []
legacy_users = []

for path in ROOT.rglob("*.qml"):
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)

    if "starHandle" in text:
        legacy_users.append(str(rel))

    if 'handleStyle: "star"' in text:
        star_users.append(str(rel))

assert not legacy_users, "legacy starHandle usage remains: " + ", ".join(legacy_users)
assert len(star_users) == 4, f"expected four star-handle consumer files, found {len(star_users)}: {star_users}"

print("Neon scrollbar contracts: PASS")
print("star-handle consumers:", ", ".join(star_users))
