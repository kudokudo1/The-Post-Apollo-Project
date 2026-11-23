#!/usr/bin/env python3
"""Actual Envelope Move preview QML, fictional data and no financial writer."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QT_QUICK_BACKEND","software")
from PySide6.QtCore import QObject,QMetaObject,QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent,QQmlEngine

app=QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="financew-m2a-qml-") as temp:
    stub=Path(temp)/"Quickshell"
    stub.mkdir()
    (stub/"qmldir").write_text("module Quickshell\nStub 1.0 Stub.qml\n")
    (stub/"Stub.qml").write_text("import QtQuick\nItem {}\n")
    engine=QQmlEngine()
    engine.addImportPath(temp)
    harness=Path(__file__).resolve().with_name(
        "finance_envelope_move_m2a_runtime_harness.qml")
    component=QQmlComponent(engine,QUrl.fromLocalFile(str(harness)))
    if component.isError():
        raise RuntimeError("QML load: "+"; ".join(map(str,component.errors())))
    root=component.create()
    if root is None:
        raise RuntimeError("QML create: "+"; ".join(map(str,component.errors())))

    def invoke(obj,name):
        assert QMetaObject.invokeMethod(obj,name),name
        app.processEvents()
    def prop(obj,name):
        app.processEvents()
        return obj.property(name)
    def setprop(obj,name,value):
        assert obj.setProperty(name,value),name
        app.processEvents()
    def value(obj,name):
        data=prop(obj,name)
        return data.toVariant() if hasattr(data,"toVariant") else data
    try:
        pane=root.findChild(QObject,"realEnvelopeMovePane")
        assert pane is not None
        assert prop(pane,"open") is False
        assert prop(pane,"sourceReady") is True
        invoke(pane,"begin")
        assert prop(pane,"open") is True
        invoke(pane,"cycleFrom")
        assert prop(pane,"fromCategoryId")=="groceries"
        invoke(pane,"cycleTo")
        assert prop(pane,"toCategoryId")=="groceries"
        setprop(pane,"toCategoryId","fuel")
        setprop(pane,"amountText","25.50")
        invoke(pane,"calculate")
        plan=value(pane,"proposal")
        assert plan["ok"] is True,plan
        assert plan["savesToActual"] is False
        assert plan["moveCents"]==2550
        assert plan["toBudgetAfterCents"]==4000
        assert plan["fromBudgetedAfterCents"]==17450
        assert plan["toBudgetedAfterCents"]==7550

        setprop(pane,"amountText","250.00")
        assert not value(pane,"proposal"),"Edited amount retained stale preview"
        invoke(pane,"calculate")
        assert prop(pane,"errorText")=="NOT ENOUGH AVAILABLE IN SOURCE ENVELOPE"
        setprop(pane,"amountText","10.00")
        setprop(pane,"toCategoryId","utilities")
        invoke(pane,"calculate")
        plan=value(pane,"proposal")
        assert plan["ok"] is True
        assert plan["toAvailableAfterCents"]==0
        assert plan["destinationRemainsOverspent"] is False

        # Same source object refresh and a month change both discard
        # prior preview; the widget cannot silently recycle stale numbers.
        invoke(root,"updateBalances")
        assert prop(pane,"open") is False
        assert not value(pane,"proposal")
        invoke(pane,"begin")
        setprop(pane,"fromCategoryId","groceries")
        setprop(pane,"toCategoryId","fuel")
        setprop(pane,"amountText","1.00")
        invoke(pane,"calculate")
        assert value(pane,"proposal")["ok"] is True
        invoke(root,"newMonth")
        assert prop(pane,"open") is False
        assert not value(pane,"proposal")
        invoke(root,"dropSource")
        assert prop(pane,"sourceReady") is False
        invoke(pane,"begin")
        assert prop(pane,"open") is False
        print("FinanceW Simple M2a actual QML fictional move preview: PASS")
    finally:
        root.close()
        root.deleteLater()
        engine.deleteLater()
        app.processEvents()
