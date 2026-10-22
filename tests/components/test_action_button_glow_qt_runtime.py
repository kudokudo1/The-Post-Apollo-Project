#!/usr/bin/env python3
"""Real QML ActionButton label/glow geometry smoke, not GPU pixel certification."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="quickshell-test-import-") as temp:
    # ActionButton imports Quickshell but does not use any of its QML types;
    # a module-only stub is sufficient to test its real QtQuick geometry.
    stub = Path(temp) / "Quickshell"
    stub.mkdir()
    (stub / "qmldir").write_text(
        "module Quickshell\nStub 1.0 Stub.qml\n", encoding="utf-8"
    )
    (stub / "Stub.qml").write_text(
        "import QtQuick\nItem {}\n", encoding="utf-8"
    )

    engine = QQmlEngine()
    engine.addImportPath(temp)
    path = Path(__file__).resolve().with_name("action_button_glow_runtime_harness.qml")
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
    if component.isError():
        raise RuntimeError("QML load: " + "; ".join(map(str, component.errors())))
    window = component.create()
    if window is None:
        raise RuntimeError("QML create: " + "; ".join(map(str, component.errors())))

    def nearly(got, expected, meaning):
        assert abs(float(got) - float(expected)) <= 0.1, (
            f"{meaning}: got {got}, expected {expected}"
        )

    def inspect(stage):
        app.processEvents()
        assert window.property("localOrigin") is True, stage
        assert window.property("customUsesFallback") is True, stage
        assert window.property("hasSource") is True, stage
        nearly(window.property("glowX"), window.property("expectedX"), stage + " x")
        nearly(window.property("glowY"), window.property("expectedY"), stage + " y")
        nearly(window.property("glowWidth"), window.property("glyphWidth"), stage + " width")
        nearly(window.property("glowHeight"), window.property("glyphHeight"), stage + " height")

    try:
        button = window.findChild(QObject, "glowLabelButton")
        assert button is not None, "ActionButton instance was not found"
        inspect("initial")
        assert button.setProperty("label", "ARCHIVE / CONFIRM")
        inspect("new label")
        assert button.setProperty("width", 250)
        inspect("resized button")
        assert button.setProperty("contentPadding", 29)
        inspect("adjusted label width")
        assert button.setProperty("selected", True)
        inspect("selected")
        assert button.setProperty("selected", False)
        inspect("unselected")
        assert button.setProperty("available", False)
        inspect("unavailable")
        assert button.setProperty("available", True)
        inspect("available")
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

print("ActionButton offscreen sampled label/glow alignment: PASS")
