#!/usr/bin/env python3
"""Offscreen Qt smoke of the real CloseButton's geometry and glow-state values."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest


def near(actual, expected, label):
    assert abs(float(actual) - expected) < 0.015, (
        f"{label}: got {actual}, expected {expected}"
    )


app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="close-button-qt-") as temp:
    # The shared ActionButton declares the Quickshell import but does not
    # instantiate Quickshell types, so a module-only test stub is sufficient.
    stub = Path(temp) / "Quickshell"
    stub.mkdir()
    (stub / "qmldir").write_text("module Quickshell\nStub 1.0 Stub.qml\n", encoding="utf-8")
    (stub / "Stub.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")

    engine = QQmlEngine()
    engine.addImportPath(temp)
    harness = Path(__file__).resolve().with_name("close_button_runtime_harness.qml")
    component = QQmlComponent(engine, harness.as_uri())
    if component.isError():
        raise RuntimeError("QML load: " + "; ".join(map(str, component.errors())))
    window = component.create()
    if window is None:
        raise RuntimeError("QML create: " + "; ".join(map(str, component.errors())))

    try:
        button = window.findChild(QObject, "universalCloseButton")
        assert button is not None, "CloseButton not found in real QML harness"

        def check_alignment(stage):
            app.processEvents()
            assert window.property("sourceAligned") is True, (
                f"{stage}: the sampled glyph halo lost its exact source position"
            )

        def glows(stage, glyph, soft, wide):
            app.processEvents()
            near(button.property("effectiveContentGlowOpacity"), glyph, f"{stage} glyph")
            near(button.property("effectiveSoftGlowOpacity"), soft, f"{stage} soft")
            near(button.property("effectiveWideGlowOpacity"), wide, f"{stage} wide")

        near(button.property("width"), 34, "default width")
        near(button.property("height"), 32, "17:16 default")
        assert button.property("label") == "×"
        assert button.property("destructive") is False
        check_alignment("initial")
        glows("idle", .34, .48, .22)

        # Selection remains red with a positive glow and does not hide the glyph.
        button.setProperty("keyboardSelected", True)
        check_alignment("keyboard focus")
        glows("keyboard focus", .72, .70, .32)
        button.setProperty("keyboardSelected", False)

        # Horizontal resizing preserves the operator-approved aspect ratio
        # and moves the glyph sampler along with its actual text.
        button.setProperty("width", 51)
        near(button.property("height"), 48, "scaled ratio")
        check_alignment("resized")
        button.setProperty("width", 34)
        check_alignment("restored")

        # Mouse move, hold and release test the actual inherited pointer engine.
        QTest.mouseMove(window, QPoint(5, 5))
        app.processEvents()
        glows("resting", .34, .48, .22)

        QTest.mouseMove(window, QPoint(50, 50))
        QTest.qWait(30)
        assert button.property("hovered") is True, "hover was not delivered"
        glows("hover", .72, .70, .32)
        check_alignment("hover")

        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(50, 50))
        app.processEvents()
        assert button.property("pressed") is True, "mouse press was not delivered"
        glows("pressed", 1.0, 1.0, 1.0)
        check_alignment("pressed")

        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(50, 50))
        app.processEvents()
        assert window.property("closeRequests") == 1, "close request not emitted exactly once"
        glows("released/hover", .72, .70, .32)

        # Disable does not silently extinguish any of the three layers.
        button.setProperty("available", False)
        app.processEvents()
        assert button.property("effectiveContentGlowOpacity") > 0
        assert button.property("effectiveSoftGlowOpacity") > 0
        assert button.property("effectiveWideGlowOpacity") > 0
        check_alignment("unavailable")
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

print("Universal CloseButton Qt source-aligned states: PASS")
