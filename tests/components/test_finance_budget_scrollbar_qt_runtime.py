#!/usr/bin/env python3
"""Offscreen runtime checks for the ACTUAL FinanceBudgetScrollRail QML type.

Unlike a source-string check, this runs QML layout and asserts rendered item
geometry after a dynamic header height change, resize and mode switch.
It does not substitute for native Quickshell operator visual acceptance.
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
qml = Path(__file__).resolve().with_name(
    "finance_budget_scrollbar_runtime_harness.qml"
)
component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml)))
assert not component.isError(), [str(x) for x in component.errors()]
root = component.create()
assert root is not None, [str(x) for x in component.errors()]
app.processEvents()

def obj(name):
    item = root.findChild(QObject, name)
    assert item is not None, name
    return item

frame = obj("budgetFrame")
column = obj("budgetColumn")
viewport = obj("budgetViewport")
host = obj("budgetRailHost")
rail = obj("financeBudgetRailTrack")

def near(value, expected, label):
    value, expected = float(value), float(expected)
    assert abs(value - expected) <= 1.0, (
        f"{label}: got {value:.2f}, expected {expected:.2f}"
    )

def verify_alignment(label):
    app.processEvents()
    assert host.property("validHierarchy") is True, label
    near(host.property("x"), column.property("x") + viewport.property("x"),
         label + " overlay x")
    near(host.property("y"), column.property("y") + viewport.property("y"),
         label + " overlay y")
    near(host.property("width"), viewport.property("width"),
         label + " overlay width")
    near(host.property("height"), viewport.property("height"),
         label + " overlay height")
    assert rail.property("boxSideGeometry") is True, label
    assert rail.property("scrollable") is True, label
    assert host.property("visible") is True, label
    near(rail.property("x"),
         host.property("width") - rail.property("width") - 2,
         label + " right edge")
    near(rail.property("y"), 2, label + " track top")
    near(rail.property("height"), host.property("height") - 4,
         label + " track height")
    near(host.property("y") + rail.property("y"),
         column.property("y") + viewport.property("y") + 2,
         label + " exact viewport top")
    near(host.property("y") + rail.property("y") + rail.property("height"),
         column.property("y") + viewport.property("y") +
         viewport.property("height") - 2,
         label + " exact viewport bottom")

try:
    verify_alignment("original compact Budget")
    old_y = float(host.property("y"))
    assert root.setProperty("headerHeight", 142)
    for _ in range(5):
        app.processEvents()
        QTest.qWait(25)  # Let Qt Quick finish Column polish/layout.
    verify_alignment("grown header")
    new_y = float(host.property("y"))
    print("HEADER_RELAYOUT // old rail y", old_y,
          "new rail y", new_y,
          "viewport y", viewport.property("y"),
          "control height", obj("budgetColumn").property("height"), flush=True)
    assert new_y > old_y + 50, (
        f"Rail did not follow Column viewport after header grew: {old_y} -> {new_y}"
    )
    assert root.setProperty("summaryHeight", 10)
    app.processEvents()
    verify_alignment("reduced summary")
    assert root.setProperty("width", 470)
    assert root.setProperty("height", 650)
    app.processEvents()
    verify_alignment("resized Budget")

    assert root.setProperty("budgetActive", False)
    app.processEvents()
    assert host.property("visible") is False, "Inactive Budget overlay visible"
    assert rail.property("visible") is False, "Inactive Budget track visible"
    assert root.setProperty("budgetActive", True)
    app.processEvents()
    verify_alignment("Budget reactivated")

    # A non-scrollable Budget must have no interactive track.
    assert root.setProperty("dataHeight", 32)
    app.processEvents()
    assert rail.property("scrollable") is False
    assert rail.property("visible") is False
    print("Finance Budget live reactive geometry/mode Qt smoke: PASS")
finally:
    root.close()
    root.deleteLater()
    engine.deleteLater()
