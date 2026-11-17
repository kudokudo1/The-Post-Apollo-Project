#!/usr/bin/env python3
"""ScrollPane V2 actual QML runtime: full track, layout policy and interaction.

This tests the real shared component in a Market-like host and cannot
substitute for operator visual acceptance of the full Finance/Quickshell UI.
"""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

app = QGuiApplication([])
engine = QQmlEngine()
path = Path(__file__).resolve().with_name("neon_scroll_pane_v2_harness.qml")
component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
assert not component.isError(), [str(e) for e in component.errors()]
root = component.create()
assert root is not None, [str(e) for e in component.errors()]

def lookup(name):
    obj = root.findChild(QObject, name)
    assert obj is not None, f"Qt object missing: {name}"
    return obj

host = lookup("marketBody")
panel = lookup("marketList")
pane = lookup("sharedMarketPane")
viewport = lookup("neonScrollPaneViewport")
rail = lookup("neonScrollPaneTrack")
rows = lookup("marketRows")

def refresh():
    for _ in range(5):
        app.processEvents()
        QTest.qWait(20)

def close(a, b, label):
    assert abs(float(a) - float(b)) <= 1, (
        f"{label}: observed={a}, expected={b}"
    )

def verify(policy, name):
    refresh()
    assert pane.property("validPolicy") is True, name
    assert pane.property("viewportPolicy") == policy, name
    close(panel.property("height"), pane.property("preferredExtent"),
          name + " policy allocation")
    close(pane.property("height"), panel.property("height"),
          name + " component height")
    close(viewport.property("height"), pane.property("height"),
          name + " viewport height")
    close(rail.property("y"), 2, name + " top")
    close(rail.property("height"), viewport.property("height") - 4,
          name + " bottom/track span")
    close(rail.property("x"),
          pane.property("width") - rail.property("width") - 2,
          name + " right gutter")
    assert rail.property("boxSideGeometry") is True, name
    assert rail.property("scrollable") is True, name
    assert rail.property("visible") is True, name
    assert rows.property("height") > viewport.property("height"), name
    assert rail.activeHandleExtent() < rail.property("trackLength"), name

try:
    verify("fill", "narrow-full")
    close(panel.property("height"), host.property("height"),
          "full list fills body")
    assert root.setProperty("policy", "split")
    verify("split", "split-layout")
    close(panel.property("height"),
          round(float(host.property("height")) * 0.46), "split ratio")
    assert root.setProperty("policy", "fixed")
    verify("fixed", "fixed-layout")
    close(panel.property("height"), 205, "explicit fixed allocation")

    assert root.setProperty("policy", "fill")
    assert root.setProperty("height", 620)
    assert root.setProperty("width", 430)
    verify("fill", "resized-full")
    close(panel.property("height"), host.property("height"),
          "resized full list")

    # The same thumb must still control its assigned viewport after resize.
    remaining = float(viewport.property("contentHeight")) - float(
        viewport.property("height"))
    assert remaining > 100
    assert viewport.setProperty("contentY", remaining)
    refresh()
    close(viewport.property("contentY"), remaining, "scroll at bottom")
    assert float(rail.property("scrollRatio")) > 0.99

    # Switching away from Market must not leave an interactive visible rail.
    assert root.setProperty("listActive", False)
    refresh()
    assert panel.property("visible") is False
    assert rail.property("visible") is False
    assert root.setProperty("listActive", True)
    verify("fill", "reopened list")

    # Short contents must hide the proportional indicator automatically.
    assert root.setProperty("countRows", 1)
    refresh()
    assert rail.property("scrollable") is False
    assert rail.property("visible") is False

    # Invalid modes must fail into the safe full-height policy.
    assert root.setProperty("policy", "unknown")
    refresh()
    assert pane.property("validPolicy") is False
    close(panel.property("height"), host.property("height"),
          "unknown policy fallback")

    print("ScrollPane V2 real Qt viewport/layout geometry and scrolling: PASS")
finally:
    root.close()
    root.deleteLater()
    engine.deleteLater()
