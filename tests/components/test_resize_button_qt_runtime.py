#!/usr/bin/env python3
"""Real offscreen Qt test for shared ResizeButton arrows and base effects.

This is not a native desktop/Wayland screenshot or GPU pixel certification.
"""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest


def near(actual, expected, name):
    assert abs(float(actual) - float(expected)) < 0.015, (
        f"{name}: got {actual}, expected {expected}"
    )


def check_identity(button, direction, label, delta, hex_color):
    assert button.property("direction") == direction
    assert button.property("label") == label
    assert button.property("sizeDelta") == delta
    assert button.property("increasing") is (delta > 0)
    assert button.property("directionValid") is True
    assert button.property("accentColor").name().lower() == hex_color.lower()


def glow(button, glyph, soft, wide, name):
    near(button.property("effectiveContentGlowOpacity"), glyph, f"{name} glyph")
    near(button.property("effectiveSoftGlowOpacity"), soft, f"{name} soft")
    near(button.property("effectiveWideGlowOpacity"), wide, f"{name} wide")


def check_visual(button, label, identity, fill, ink, border, glows):
    """Check active colors plus the three actual glow-plane colors/opacities."""
    for prop, expected in (
        ("accentColor", identity),
        ("fillColor", fill),
        ("foregroundColor", ink),
        ("activeBorderColor", border),
        ("contentGlowColor", identity),
        ("softGlowColor", identity),
        ("wideGlowColor", identity),
    ):
        color = button.property(prop)
        assert color.name().lower() == expected.lower(), (
            f"{label} {prop}: {color.name()}, expected {expected}"
        )
    glow(button, *glows, name=label)


def ink_centered(window, name):
    assert window.property("downInkCentered") is True, f"{name}: down ink offset"
    assert window.property("upInkCentered") is True, f"{name}: up ink offset"


app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="resize-button-qt-") as temp:
    # ActionButton imports Quickshell but uses no Quickshell native types.
    stub = Path(temp) / "Quickshell"
    stub.mkdir()
    (stub / "qmldir").write_text("module Quickshell\nStub 1.0 Stub.qml\n", encoding="utf-8")
    (stub / "Stub.qml").write_text("import QtQuick\nItem {}\n", encoding="utf-8")

    engine = QQmlEngine()
    engine.addImportPath(temp)
    harness = Path(__file__).resolve().with_name("resize_button_runtime_harness.qml")
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(harness)))
    if component.isError():
        raise RuntimeError("QML load: " + "; ".join(map(str, component.errors())))
    window = component.create()
    if window is None:
        raise RuntimeError("QML create: " + "; ".join(map(str, component.errors())))

    try:
        down = window.findChild(QObject, "resizeDownButton")
        up = window.findChild(QObject, "resizeUpButton")
        assert down is not None and up is not None

        near(down.property("width"), 30, "down width")
        near(down.property("height"), 30, "down height")
        near(up.property("width"), 30, "up width")
        near(up.property("height"), 30, "up height")
        assert down.property("labelPixelSize") == 17
        assert up.property("labelPixelSize") == 17
        check_identity(down, "down", "⮟", -1, "#ED981A")
        check_identity(up, "up", "⮝", 1, "#A46AFF")

        assert down.property("destructive") is False
        assert up.property("destructive") is False
        assert up.property("wideGlowEnabled") is True
        assert down.property("trackLabelGlowLocally") is True
        assert window.property("downAligned") is True
        assert window.property("upAligned") is True
        ink_centered(window, "up/down 30px")
        check_visual(down, "down idle", "#ED981A", "#1B0623", "#ED981A", "#ED981A", (.34, .48, .22))
        check_visual(up, "up idle", "#A46AFF", "#1B0623", "#A46AFF", "#A46AFF", (.34, .48, .22))

        down.setProperty("width", 28)
        app.processEvents()
        near(down.property("height"), 28, "compact keeps square")
        assert window.property("downAligned") is True
        ink_centered(window, "down 28px")
        down.setProperty("width", 30)

        # Keyboard selected state is inherited, not independently recreated.
        down.setProperty("keyboardSelected", True)
        app.processEvents()
        check_visual(down, "keyboard selected", "#ED981A", "#F2BE4E", "#ED981A", "#ED981A", (.72, .70, .32))
        down.setProperty("keyboardSelected", False)

        # CloseButton-style three-plane glows preserve the orange/purple
        # identity through hover and press, with a black pressed glyph/border.
        QTest.mouseMove(window, QPoint(5, 5))
        app.processEvents()
        check_visual(down, "down rest", "#ED981A", "#1B0623", "#ED981A", "#ED981A", (.34, .48, .22))

        QTest.mouseMove(window, QPoint(45, 45))
        QTest.qWait(30)
        assert down.property("hovered") is True
        check_visual(down, "down hover", "#ED981A", "#F2BE4E", "#ED981A", "#ED981A", (.72, .70, .32))
        assert window.property("downAligned") is True

        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(45, 45))
        app.processEvents()
        assert down.property("pressed") is True
        check_visual(down, "down pressed", "#ED981A", "#ED981A", "#1B0623", "#1B0623", (1.0, 1.0, 1.0))
        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(45, 45))
        app.processEvents()
        assert window.property("downRequests") == 1
        assert window.property("lastDownDelta") == -1
        check_visual(down, "down released", "#ED981A", "#F2BE4E", "#ED981A", "#ED981A", (.72, .70, .32))

        # The other arrow has the same base states and the opposite request.
        QTest.mouseMove(window, QPoint(124, 46))
        QTest.qWait(30)
        assert up.property("hovered") is True
        check_visual(up, "up hover", "#A46AFF", "#F2BE4E", "#A46AFF", "#A46AFF", (.72, .70, .32))
        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(124, 46))
        app.processEvents()
        check_visual(up, "up pressed", "#A46AFF", "#A46AFF", "#1B0623", "#1B0623", (1.0, 1.0, 1.0))
        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(124, 46))
        app.processEvents()
        assert window.property("upRequests") == 1
        assert window.property("lastUpDelta") == 1
        check_visual(up, "up released", "#A46AFF", "#F2BE4E", "#A46AFF", "#A46AFF", (.72, .70, .32))

        # All four exact glyphs use the same two semantic directions.
        down.setProperty("direction", "left")
        up.setProperty("direction", "right")
        app.processEvents()
        check_identity(down, "left", "⮜", -1, "#ED981A")
        check_identity(up, "right", "⮞", 1, "#A46AFF")
        check_visual(down, "left hover", "#ED981A", "#1B0623", "#ED981A", "#ED981A", (.34, .48, .22))
        check_visual(up, "right hover", "#A46AFF", "#F2BE4E", "#A46AFF", "#A46AFF", (.72, .70, .32))
        assert window.property("downAligned") is True
        assert window.property("upAligned") is True
        ink_centered(window, "left/right 30px")
        up.setProperty("width", 28)
        down.setProperty("width", 28)
        app.processEvents()
        ink_centered(window, "left/right 28px")
        up.setProperty("width", 30)
        down.setProperty("width", 30)

        # No unexpected events from a disabled or unsupported button.
        down.setProperty("available", False)
        app.processEvents()
        near(down.property("opacity"), .34, "disabled fade")
        assert down.property("interactive") is False
        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(45, 45))
        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(45, 45))
        app.processEvents()
        assert window.property("downRequests") == 1

        down.setProperty("available", True)
        down.setProperty("direction", "diagonal")
        app.processEvents()
        assert down.property("directionValid") is False
        assert down.property("interactive") is False
        QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(45, 45))
        QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(45, 45))
        app.processEvents()
        assert window.property("downRequests") == 1
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

print("Universal ResizeButton Qt arrow/input/glow smoke: PASS")
