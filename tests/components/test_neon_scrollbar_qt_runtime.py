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
if any(obj is None for obj in (bar, inner, outer, horizontal_bar, horizontal_pane)):
    raise AssertionError("QML harness did not expose the three target objects")

def near(value, expected, label):
    if abs(float(value) - expected) > 0.05:
        raise AssertionError(f"{label}: got {value!r} expected {expected!r}")

try:
    assert bar.property("nestedScrollMode") == "contain"
    assert bar.property("nestedPaneDetected") is True, "nested hierarchy was not detected"
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
    print("NeonScrollBar Qt runtime smoke: PASS")
finally:
    root.close()
    root.deleteLater()
    engine.deleteLater()
