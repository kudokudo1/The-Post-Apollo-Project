#!/usr/bin/env python3
"""Offscreen Qt smoke: real ReloadButton semantics and source-aligned glow."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest


def near(actual, expected, label):
    assert abs(float(actual) - expected) < .015, (
        f"{label}: got {actual}, expected {expected}"
    )


def same_color(actual, expected, label):
    assert actual.isValid() and expected.isValid(), f"{label}: invalid QColor"
    assert actual.name() == expected.name(), (
        f"{label}: got {actual.name()}, expected {expected.name()}"
    )


app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="reload-button-qt-") as temp:
    # ActionButton imports but does not instantiate Quickshell. This avoids
    # changing the user's desktop or requiring a Wayland compositor.
    stub = Path(temp) / "Quickshell"
    stub.mkdir()
    (stub / "qmldir").write_text(
        "module Quickshell\nStub 1.0 Stub.qml\n", encoding="utf-8"
    )
    (stub / "Stub.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")
    engine = QQmlEngine()
    engine.addImportPath(temp)
    harness = Path(__file__).resolve().with_name("reload_button_runtime_harness.qml")
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(harness)))
    if component.isError():
        raise RuntimeError("QML load: " + "; ".join(map(str, component.errors())))
    window = component.create()
    if window is None:
        raise RuntimeError("QML create: " + "; ".join(map(str, component.errors())))

    try:
        button = window.findChild(QObject, "universalReloadButton")
        assert button is not None, "ReloadButton not found"
        yellow = window.property("expectedYellow")
        orange = window.property("expectedOrange")
        magenta = window.property("expectedMagenta")
        black = window.property("expectedBlack")

        def colors(stage, fill, foreground, border, glow):
            app.processEvents()
            for name, expected in (
                ("fillColor", fill),
                ("foregroundColor", foreground),
                ("activeBorderColor", border),
                ("contentGlowColor", glow),
                ("softGlowColor", glow),
                ("wideGlowColor", glow),
            ):
                same_color(button.property(name), expected, stage + " " + name)
            assert window.property("sourceAligned") is True, stage

        def glows(stage, glyph, soft, wide):
            app.processEvents()
            near(button.property("effectiveContentGlowOpacity"), glyph, stage + " glyph")
            near(button.property("effectiveSoftGlowOpacity"), soft, stage + " soft")
            near(button.property("effectiveWideGlowOpacity"), wide, stage + " wide")

        near(button.property("width"), 35, "default width")
        near(button.property("height"), 32, "default height")
        assert button.property("label") == "⟳"
        assert button.property("destructive") is False
        colors("idle", black, yellow, yellow, yellow)
        glows("idle", .34, .48, .22)

        QTest.mouseMove(window, QPoint(50, 50))
        QTest.qWait(40)
        assert button.property("hovered") is True, "mouse hover not delivered"
        colors("hover", orange, yellow, yellow, yellow)
        glows("hover", .72, .70, .32)

        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(50, 50))
        app.processEvents()
        assert button.property("pressed") is True
        colors("pressed", yellow, black, black, yellow)
        glows("pressed", 1.0, 1.0, 1.0)

        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(50, 50))
        app.processEvents()
        assert window.property("reloadRequests") == 1, "reload request not emitted once"
        colors("released hover", orange, yellow, yellow, yellow)

        QTest.mouseMove(window, QPoint(5, 5))
        QTest.qWait(30)
        button.setProperty("selected", True)
        colors("owner-selected", orange, yellow, yellow, yellow)
        glows("owner-selected", .72, .70, .32)
        button.setProperty("selected", False)
        button.setProperty("keyboardSelected", True)
        colors("keyboard-selected", orange, yellow, yellow, yellow)
        glows("keyboard-selected", .72, .70, .32)
        button.setProperty("keyboardSelected", False)

        # A second consumer may choose its own semantic value. Only the hover
        # surface is orange by default; the glow follows the semantic color.
        button.setProperty("semanticColor", magenta)
        colors("alternate semantic", black, magenta, magenta, magenta)
        button.setProperty("selected", True)
        colors("alternate selected", orange, magenta, magenta, magenta)
        button.setProperty("selected", False)

        # Disabled/quiet controls retain a positive halo rather than losing
        # an effect layer to an accidental zero-opacity state.
        button.setProperty("available", False)
        app.processEvents()
        assert button.property("effectiveContentGlowOpacity") > 0
        assert button.property("effectiveSoftGlowOpacity") > 0
        assert button.property("effectiveWideGlowOpacity") > 0

    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

print("ReloadButton Qt color, glyph alignment and click semantics: PASS")
