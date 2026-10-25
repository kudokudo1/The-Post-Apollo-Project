#!/usr/bin/env python3
"""Offscreen Qt runtime smoke for the shared NeonScrollBar, not visual acceptance.

Installs/uses PySide6 when the CI runtime job runs. Native QML load and
property-level motion assertions supplement, but do not replace, an actual
operator-facing Quickshell visual and interaction pass.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QCoreApplication, QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QWheelEvent
from PySide6.QtQml import QQmlComponent, QQmlEngine

app = QGuiApplication([])
engine = QQmlEngine()
path = Path(__file__).resolve().with_name("neon_scrollbar_runtime_harness.qml")
component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
if component.isError():
    raise RuntimeError("QML compile/load: " + "; ".join(str(e) for e in component.errors()))
root = component.create()
if root is None:
    raise RuntimeError("QML instantiation: " + "; ".join(str(e) for e in component.errors()))
app.processEvents()

# PySide6 cannot convert a QML-defined strongly typed alias into a Python
# wrapper automatically. Object names resolve through QObject instead.
bar = root.findChild(QObject, "auditScrollBar")
inner = root.findChild(QObject, "innerPane")
outer = root.findChild(QObject, "outerPane")
horizontal_bar = root.findChild(QObject, "horizontalBar")
horizontal_pane = root.findChild(QObject, "horizontalPane")
positioner_bar = root.findChild(QObject, "positionerBar")
positioner_pane = root.findChild(QObject, "positionerPane")
positioned_host = root.findChild(QObject, "positionedHost")
positioner = root.findChild(QObject, "positioner")
section_bar = root.findChild(QObject, "sectionBar")
section_pane = root.findChild(QObject, "sectionPane")
section_host = root.findChild(QObject, "sectionHost")
graph_rail = root.findChild(QObject, "graphRail")
graph_pane = root.findChild(QObject, "graphPane")
graph_frame = root.findChild(QObject, "graphFrame")
graph_inset = root.findChild(QObject, "graphInset")
shifted_list = root.findChild(QObject, "shiftedList")
shifted_bar = root.findChild(QObject, "shiftedBar")
if any(obj is None for obj in (bar, inner, outer, shifted_list, shifted_bar,
                               horizontal_bar, horizontal_pane,
                               positioner_bar, positioner_pane, positioned_host, positioner,
                               section_bar, section_pane, section_host,
                               graph_rail, graph_pane, graph_frame, graph_inset)):
    raise AssertionError("QML harness did not expose the three target objects")

def near(value, expected, label):
    if abs(float(value) - expected) > 0.05:
        raise AssertionError(f"{label}: got {value!r} expected {expected!r}")

try:
    assert bar.property("nestedScrollMode") == "contain"
    assert bar.property("nestedPaneDetected") is True, "nested hierarchy was not detected"
    assert bar.property("hostIsScrollingContent") is True
    assert bar.property("boxSideGeometry") is False, (
        "Do not stretch a nested list's rail over its parent Flickable content"
    )
    assert bar.property("scrollChaining") is False
    assert bar.property("captureNestedPaneWheel") is True
    assert bar.property("horizontal") is False
    near(bar.property("crossExtent"), 10, "normal bar physical width")
    near(bar.property("reservedExtent"), 14, "normal bar reservation")
    near(bar.property("width"), 10, "normal bar viewport width")
    near(bar.property("height"), 140, "vertical track height excluding 5px endpoints")
    assert bar.property("scrollable") is True
    assert bar.property("visible") is True
    assert outer.property("contentY") == 0
    # Exercise QML component's external key-routing API.
    assert bool(bar.handleKey(0x01000011, 0)), "Key_End must be handled"
    near(inner.property("contentY"), 450, "End key inner scroll")
    near(outer.property("contentY"), 0, "End key never moves outer pane")
    assert bool(bar.handleKey(0x01000010, 0)), "Key_Home must be handled"
    near(inner.property("contentY"), 0, "Home key inner scroll")
    # Ctrl+End is an existing shortcut possibility: don't hijack.
    assert not bool(bar.handleKey(0x01000011, 0x04000000)), "Ctrl+End shortcut hijacked"
    # Confirm the width style variant doesn't inflate the real hit area.
    assert bar.setProperty("handleStyle", "star")
    app.processEvents()
    near(bar.property("width"), 16, "star physical width")
    near(bar.property("reservedExtent"), 20, "star reservation")
    assert bar.setProperty("viewportHasEndpointClearance", True)
    app.processEvents()
    near(bar.property("height"), 150, "host-supplied endpoint clearance")
    # Set inner to the bottom and verify component clamping independently.
    assert inner.setProperty("contentY", 450)
    app.processEvents()
    near(inner.property("contentY"), 450, "inner scroll at its lower boundary")
    near(outer.property("contentY"), 0, "outer does not move through inner controls")

    def send_wheel(y_angle, x=100, y=80):
        # Default point is over the INNER list, not the thin bar.
        event = QWheelEvent(QPointF(x, y), QPointF(x, y),
                            QPoint(0, 0), QPoint(0, y_angle),
                            Qt.NoButton, Qt.NoModifier, Qt.ScrollUpdate, False)
        QCoreApplication.sendEvent(root, event)
        app.processEvents()

    send_wheel(-120)  # Already at inner end: outer must remain still.
    near(inner.property("contentY"), 450, "inner wheel clamped at its bottom")
    near(outer.property("contentY"), 0, "wheel in inner pane does not chain at bottom")
    assert inner.setProperty("contentY", 0)
    send_wheel(120)  # Already at inner top: outer must remain still.
    near(inner.property("contentY"), 0, "inner wheel clamped at its top")
    near(outer.property("contentY"), 0, "wheel in inner pane does not chain at top")
    send_wheel(-120)
    assert float(inner.property("contentY")) > 0, "inner list must scroll normally"

    # The same QML component also works as a horizontal scrollbar.
    assert horizontal_bar.property("horizontal") is True
    near(horizontal_bar.property("height"), 10, "horizontal physical thickness")
    near(horizontal_bar.property("width"), 280, "horizontal track endpoint insets")
    assert bool(horizontal_bar.handleKey(0x01000014, 0)), "Right arrow should move horizontal pane"
    assert float(horizontal_pane.property("contentX")) > 0, "horizontal right-arrow moved pane"
    assert bool(horizontal_bar.handleKey(0x01000010, 0)), "Home resets horizontal pane"
    near(horizontal_pane.property("contentX"), 0, "horizontal pane Home")
    # Rule 018: vertical wheel over the *horizontal bar* scrolls right.
    send_wheel(-120, x=160, y=349)
    assert float(horizontal_pane.property("contentX")) > 0, (
        "vertical wheel over horizontal scrollbar did not scroll right"
    )
    # Verify a declaratively nested indicator actually escapes the Column.
    assert root.property("mountedOnHost") is True, "scrollbar was not reparented to the layout host"
    near(positioner_bar.property("width"), 16, "star overlay width")
    assert positioner_bar.property("boxSideGeometry") is True
    near(positioner_bar.property("x"), 320 - 16 - 4, "mounted box-edge x")
    near(positioner_bar.property("y"), 2, "mounted box-edge y")
    near(positioner_bar.property("height"), 78 - 4, "mounted box-edge height")
    assert root.property("columnKeptOneItem") is True, (
        "Scrollbar should not become an extra row in the Column"
    )

    # Default box-side track follows its enclosing section, not the inset
    # viewport. Direct header/footer siblings bound the actually usable side.
    assert section_bar.property("boxSideGeometry") is True
    near(section_bar.property("x"), 320 - 16 - 4, "section box-edge x")
    near(section_bar.property("y"), 27 + 6 + 2, "section after-header y")
    near(section_bar.property("height"), (151 - 2) - (33 + 2),
         "section track extends to footer")
    near(section_pane.property("y"), 46, "content pane stays put")
    # Legacy viewport alignment remains explicit and fully reversible.
    assert section_bar.setProperty("geometryMode", "viewport")
    app.processEvents()
    near(section_bar.property("y"), 46 + 5, "viewport override y")
    near(section_bar.property("height"), 93 - 10, "viewport override height")
    assert section_bar.setProperty("geometryMode", "box")
    app.processEvents()
    near(section_bar.property("y"), 35, "restored box alignment")

    # Git Branch Map reproduces a 10px inset wrapper with an explicit outer
    # frame geometryHost. The scrollbar fills the frame's side, not the inner
    # viewport or inset wrapper, and stays inside its top/bottom borders.
    assert root.property("graphParentIsFrame") is True, (
        "Graph scrollbar must mount on the same outer frame it measures"
    )
    assert root.property("graphParentIsInset") is False
    assert graph_rail.property("boxSideGeometry") is True
    assert root.property("graphUsesOuterFrame") is True, "graph scrollbar must use outer frame"
    near(graph_rail.property("width"), 16, "graph star rail width")
    near(root.property("graphRailFrameX"), 320 - 16 - 4 - 10 - 28,
         "graph rail matches the marked position, 28px left of its inset baseline")
    near(root.property("graphRailFrameY"), 10 + 28 / 2,
         "graph rail reaches center of data fields")
    near(graph_rail.property("height"), 190 - (10 + 28 / 2) - 2,
         "graph rail stops inside bottom frame")
    near(graph_pane.property("y"), 28 + 4, "graph content stays below header")
    # Normal viewport compatibility is tested by section_bar above. This
    # remounted graph-specific test guards only its intended box-side mode.

    # Notifications COMBI may change its ListView origin after removing old
    # rows and re-estimating variable-height report/ordinary delegates.
    assert bar.property("accountForContentOrigin") is False, (
        "All existing NeonScrollBar consumers must keep the legacy geometry"
    )
    assert shifted_bar.property("accountForContentOrigin") is True
    root.disturbListOrigin()
    app.processEvents()
    origin = float(shifted_list.property("originY"))
    assert abs(origin) > 0.1, (
        f"Fixture failed to create a nonzero ListView origin: {origin}"
    )
    # A thumb jump to the top must use originY, not the absolute zero that can
    # point to a stale/blank region. This is the reported Notifications fault.
    shifted_bar.scrollTo(0, 0)
    app.processEvents()
    near(shifted_list.property("contentY"),
         shifted_list.property("originY"), "origin-aware thumb to actual list top")
    near(shifted_bar.property("scrollRatio"), 0, "top marker after origin shift")
    # Moving from that shifted top keeps the origin offset and remains
    # proportional. Home must return to the same true top.
    assert bool(shifted_bar.moveBy(30, False))
    app.processEvents()
    assert float(shifted_bar.property("scrollRatio")) > 0
    assert bool(shifted_bar.handleKey(0x01000010, 0))
    app.processEvents()
    near(shifted_list.property("contentY"),
         shifted_list.property("originY"), "Home uses shifted list origin")
    near(shifted_bar.property("scrollRatio"), 0, "Home thumb at beginning")

    # Preserve legacy per-layer inactive fading unless explicitly requested.
    assert bar.setProperty("autoHide", False)
    assert inner.setProperty("contentHeight", inner.property("height"))
    app.processEvents()
    near(bar.property("opacity"), 1, "legacy persistent root remains full-opacity")
    assert bar.setProperty("visibilityMode", "persistent")
    app.processEvents()
    near(bar.property("opacity"), 0.34, "explicit persistent root inactive opacity")

    # Regression: live panes may detach/rebind while reveal mode is active.
    # Previously this produced repeated 'hovered of null' binding warnings.
    from PySide6.QtCore import qInstallMessageHandler
    teardown_warnings = []

    def capture_qt_message(mode, context, message):
        teardown_warnings.append(message)

    previous_handler = qInstallMessageHandler(capture_qt_message)
    try:
        assert bar.setProperty("visibilityMode", "reveal")
        app.processEvents()
        assert bar.setProperty("flickable", None)
        app.processEvents()
        # A reveal trigger can still be active through scroll/focus/pointer
        # state; the regression is about null-reference warnings, not value.
        assert bar.setProperty("flickable", inner)
        app.processEvents()
    finally:
        qInstallMessageHandler(previous_handler)

    assert not any("Cannot read property 'hovered' of null" in warning
                   or "Cannot read property 'containsMouse' of null" in warning
                   or "Cannot read property 'pressed' of null" in warning
                   for warning in teardown_warnings), teardown_warnings

    print("NeonScrollBar Qt runtime smoke: PASS")
finally:
    root.close()
    root.deleteLater()
    engine.deleteLater()
