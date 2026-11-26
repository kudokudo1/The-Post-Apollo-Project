#!/usr/bin/env python3
"""Real QML ActionButton label/glow geometry smoke, not GPU pixel certification."""

import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QUrl, QPoint, Qt
from PySide6.QtTest import QTest
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
        assert button.property("contentGlowEnabled") is True
        nearly(button.property("contentGlowIdleOpacity"), .35, "inherited idle glyph glow")
        nearly(button.property("contentGlowHoverOpacity"), .65, "inherited hover glyph glow")
        nearly(button.property("contentGlowPressedOpacity"), .85, "inherited pressed glyph glow")
        nearly(button.property("contentGlowSelectedOpacity"), 1.0, "inherited selected glyph glow")
        nearly(button.property("contentGlowRadius"), 7, "preserved glyph radius")
        nearly(button.property("contentGlowSamples"), 7, "preserved glyph samples")
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

        red = window.findChild(QObject, "redActionButton")
        close = window.findChild(QObject, "redActionCloseComparison")
        normal = window.findChild(QObject, "redNormalComparison")
        custom = window.findChild(QObject, "redExplicitComparison")
        assert red and close and normal and custom
        def color(obj, prop):
            return obj.property(prop).name()
        def move(x, y):
            QTest.mouseMove(window, QPoint(x, y))
            app.processEvents()
        move(450, 210)
        assert red.property("redActionFace") is True
        assert close.property("redActionFace") is False
        assert normal.property("redActionFace") is False
        def outline(item):
            return item.findChild(QObject, "actionButtonNormalPerimeter")
        def broad(item, name):
            return item.findChild(QObject, name)
        def check_safe(item):
            assert item.property("washSafePerimeter") is True
            assert outline(item).property("active") is True
            assert not broad(item, "actionButtonBroadSoftGlow").property("visible")
            assert not broad(item, "actionButtonBroadWideGlow").property("visible")
        for item, point in ((button, (40, 30)), (normal, (240, 95))):
            check_safe(item)
            assert color(item, "color") == color(item, "idleFillColor")
            move(*point)
            assert item.property("hovered")
            assert color(item, "color") == color(item, "hoverFillColor")
            assert color(item, "activeBorderColor") == color(item, "hoverBorderColor")
            assert abs(item.property("stateContentGlowOpacity") - .65) < .001
            QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(*point))
            app.processEvents()
            assert item.property("pressed")
            assert color(item, "color") == color(item, "pressedFillColor")
            assert abs(item.property("stateContentGlowOpacity") - .85) < .001
            QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(*point))
            app.processEvents()
            assert color(item, "color") == color(item, "hoverFillColor")
            assert item.setProperty("selected", True)
            app.processEvents()
            assert color(item, "color") == color(item, "selectedFillColor")
            assert abs(item.property("stateContentGlowOpacity") - 1.0) < .001
            check_safe(item)
            move(450,210)
            assert item.setProperty("visible", False)
            app.processEvents()
            assert not outline(item).property("active")
            assert item.setProperty("visible", True)
            app.processEvents()
            assert color(item, "color") == color(item, "selectedFillColor")
            check_safe(item)
            assert item.setProperty("selected", False)
            app.processEvents()
            assert color(item, "color") == color(item, "idleFillColor")
            assert item.setProperty("keyboardSelected", True)
            app.processEvents()
            assert color(item, "color") == color(item, "keyboardSelectedFillColor")
            assert item.setProperty("keyboardSelected", False)
            app.processEvents()
            assert color(item, "color") == color(item, "idleFillColor")
        special = window.findChild(QObject, "deliberateBroadComparison")
        quiet = window.findChild(QObject, "quietComparison")
        for item in (red, close, special):
            assert item.property("washSafePerimeter") is False
            assert not outline(item).property("active")
            assert broad(item, "actionButtonBroadSoftGlow").property("visible")
        assert quiet.property("washSafePerimeter") is True
        assert not outline(quiet).property("active")
        assert not broad(quiet, "actionButtonBroadSoftGlow").property("visible")
        assert not quiet.property("contentGlowEnabled")
        assert color(custom, "foregroundColor") == color(custom, "idleForegroundColor")
        assert color(red, "foregroundColor") == color(red, "idleForegroundColor")
        assert color(red, "foregroundColor") != color(red, "accentColor")
        assert color(red, "activeBorderColor") == color(red, "accentColor")
        assert color(red, "contentGlowColor") == color(red, "accentColor")
        idle = [red.property(k) for k in ("stateContentGlowOpacity", "stateSoftGlowOpacity", "stateWideGlowOpacity")]
        move(240, 30)
        assert red.property("hovered") is True
        assert abs(red.property("stateContentGlowOpacity") - .65) < .001
        assert color(red, "fillColor") == color(red, "hoverFillColor")
        assert color(red, "foregroundColor") == color(red, "idleForegroundColor")
        assert color(red, "activeBorderColor") == color(red, "accentColor")
        QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(240,30))
        app.processEvents()
        assert red.property("pressed") is True
        assert abs(red.property("stateContentGlowOpacity") - .85) < .001
        assert color(red, "fillColor") == color(red, "pressedFillColor")
        assert color(red, "foregroundColor") == color(red, "pressedForegroundColor")
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(240,30))
        app.processEvents()
        assert abs(red.property("stateContentGlowOpacity") - .65) < .001
        move(450,210)
        assert abs(red.property("stateContentGlowOpacity") - .35) < .001
        assert red.setProperty("selected", True)
        app.processEvents()
        assert color(red, "foregroundColor") == color(red, "accentColor")
        assert color(red, "fillColor") == color(red, "idleFillColor")
        assert all(red.property(k) > v for k,v in zip(
            ("stateContentGlowOpacity", "stateSoftGlowOpacity", "stateWideGlowOpacity"),idle))
        assert red.setProperty("selected", False)
        app.processEvents()
        assert color(red, "foregroundColor") == color(red, "idleForegroundColor")
        assert color(close, "foregroundColor") == color(close, "accentColor")
        mode = window.findChild(QObject, "hierarchyModeButton")
        glow = mode.findChild(QObject, "modePrimaryGlow")
        assert mode and glow
        def mode_strength(expected):
            app.processEvents()
            assert abs(glow.property("opacity") - expected) < .001
        mode_strength(.45)
        move(70, 185)
        assert mode.property("hovered")
        mode_strength(.75)
        QTest.mousePress(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(70,185))
        mode_strength(.95)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(70,185))
        mode_strength(.75)
        assert mode.setProperty("selected", True)
        mode_strength(1.0)
        move(450,210)
        mode_strength(1.0)
        assert mode.setProperty("selected", False)
        mode_strength(.45)
    finally:
        window.close()
        window.deleteLater()
        app.processEvents()

print("ActionButton offscreen sampled label/glow alignment: PASS")
