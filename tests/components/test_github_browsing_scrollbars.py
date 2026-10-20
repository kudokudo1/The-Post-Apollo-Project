#!/usr/bin/env python3
"""Scope contract: three GitHub browsing scrollbars are visible and usable.

Source assertions only. The shared Qt offscreen smoke covers reusable
NeonScrollBar motion/geometry; user desktop confirms real pointer/rendering.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
work = (ROOT / "widgets/GitHubWorkItemsView.qml").read_text(encoding="utf-8")
profile = (ROOT / "widgets/RepositoryProfileView.qml").read_text(encoding="utf-8")
host = (ROOT / "widgets/GitW.qml").read_text(encoding="utf-8")
shared = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")


def scrollbar_block(source, identity):
    start = source.rfind("NeonScrollBar {", 0, source.index(identity))
    assert start >= 0, f"Missing scroll control {identity}"
    depth, end = 0, 0
    for end in range(start, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if depth == 0:
                return source[start : end + 1]
    raise AssertionError(f"Unclosed scroll control {identity}")


work_bar = scrollbar_block(work, "id: scrollTrack")
catalog_bar = scrollbar_block(profile, "id: catalogScrollTrack")

# One implementation serves both the GitHub Pulls and Issues top-level lists.
assert 'readonly property bool isPulls: kind === "pulls"' in work
assert 'kind: "pulls"' in host
assert 'kind: "issues"' in host
assert "id: sourceList" in work
assert "rightMargin: scrollTrack.width + 9" in work

for title, bar in (("Pulls/Issues", work_bar), ("Repository Catalog", catalog_bar)):
    for clause in (
        'handleStyle: "star"',
        "railColor: Colors.cyan",
        "railGlowColor: Colors.cyan",
        "interactive: true",
        "wheelEnabled: true",
        "clickToJump: true",
        "z: 2",
    ):
        assert clause in bar, f"{title}: missing {clause}"
    assert "interactive: false" not in bar, title
    assert "wheelEnabled: false" not in bar, title
    assert "railColor: Colors.dark" not in bar, title
    assert "railColor: Colors.black" not in bar, title

# Full-length click/drag target exists in the shared component already; only
# these consumers activate it. Long lists retain their entire vertical rail.
for clause in (
    "anchors.fill: parent",
    "enabled: root.interactive && root.scrollable",
    "draggingHandle = insideHandle || (!pageMode && root.clickToJump)",
    "root.scrollTo(pointer, dragOffset)",
):
    assert clause in shared, clause
assert "height: Math.max(0, parent.height - 10)" in work_bar
assert "visible: scrollable" in work_bar
assert "scrollThreshold: 0" in work_bar
assert "scrollThreshold: 0" in catalog_bar
assert "autoHide: false" in catalog_bar
assert "x: parent.width - width" in catalog_bar
assert "right: catalogScrollTrack.left" in profile
assert "rightMargin: 5" in profile

# Compact Profile: catalog and queue no longer consume fixed 205+145 px.
# The magenta Saved Sets panel keeps a real footer and scroll viewport.
for clause in (
    "id: profileLeftColumn",
    "Math.max(0, height - 2 * spacing)",
    "Math.min(170, Math.max(90, cardSpace * 0.45))",
    "id: repositoryCatalogFrame",
    "id: targetBatchFrame",
    "id: savedSetsFrame",
    "profileLeftColumn.upperCardSpace",
    "profileLeftColumn.cardSpace",
    "id: setNameRow",
    "height: 32",
    "height: 30\n                                anchors.verticalCenter: parent.verticalCenter",
    "id: savedSetsCaption",
    "id: queueScrollTrack",
    "geometryHost: targetBatchFrame",
    "boxTopInset: 4 + syntagmaPane1.y",
    "id: savedSetsScrollTrack",
    "geometryHost: savedSetsFrame",
    "boxTopInset: 6 + syntagmaPane2.y",
    "width: Math.max(0, parent.width\n                                - queueScrollTrack.reservedExtent - 4)",
    "width: Math.max(0, parent.width\n                                - savedSetsScrollTrack.reservedExtent - 4)",
    "setNameRow.height",
    "savedSetsCaption.implicitHeight",
):
    assert clause in profile, f"Compact Profile missing: {clause}"

assert "height: parent.height - 366" not in profile
assert "height: parent.height - 67" not in profile
assert 'placeholderText: "PROFILE SET NAME"' in profile

for height in (215, 235, 300, 420):
    space = max(0, height - 2 * 6)
    saved_target = min(space, min(170, max(90, space * 0.45)))
    upper = max(0, space - saved_target)
    catalog_height = round(upper * 0.52)
    batch_height = max(0, upper - catalog_height)
    saved_height = max(0, space - catalog_height - batch_height)
    assert saved_height >= 90, f"Saved Sets collapsed at {height}px"
    assert abs(catalog_height + batch_height + saved_height + 12 - height) < 1.1

# Intentionally no modifications to graph panes, shared UI primitive, or
# unrelated Repository Profile subviews.
print("GITHUB PULLS / ISSUES / CATALOG // INTERACTIVE RAIL CONTRACT PASS")
