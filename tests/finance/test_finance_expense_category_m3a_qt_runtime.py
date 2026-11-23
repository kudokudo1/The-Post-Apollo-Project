#!/usr/bin/env python3
"""Real M3a expense-category QML in a headless fictional Qt fixture.

No Quickshell process, Actual API, live accounts, financial writer or permit.
"""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QT_QUICK_BACKEND","software")
from PySide6.QtCore import QObject,QMetaObject,QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent,QQmlEngine

app=QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="financew-m3a-expense-") as temp:
    stub=Path(temp)/"Quickshell"
    stub.mkdir()
    (stub/"qmldir").write_text("module Quickshell\nStub 1.0 Stub.qml\n")
    (stub/"Stub.qml").write_text("import QtQuick\nItem {}\n")
    engine=QQmlEngine()
    engine.addImportPath(temp)
    path=Path(__file__).resolve().with_name(
        "finance_expense_category_m3a_runtime_harness.qml")
    component=QQmlComponent(engine,QUrl.fromLocalFile(str(path)))
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
    def as_value(obj,name):
        data=prop(obj,name)
        return data.toVariant() if hasattr(data,"toVariant") else data
    def setprop(obj,name,value):
        assert obj.setProperty(name,value),name
        app.processEvents()

    try:
        pane=root.findChild(QObject,"actualExpenseCategoryPreview")
        assert pane is not None
        assert prop(pane,"open") is False
        assert prop(pane,"sourceReady") is True
        invoke(root,"openFixture")
        assert prop(pane,"open") is True
        invoke(root,"selectGroceries")
        assert prop(pane,"selectedCategoryId")=="groceries"
        invoke(root,"propose")
        plan=as_value(pane,"proposal")
        assert plan["ok"] is True,plan
        assert plan["writeAllowed"] is False
        assert plan["savesToActual"] is False
        assert plan["estimatedAvailableAfterCents"]==6250
        assert plan["toBudgetAfterCents"] is None
        invoke(root,"selectCoffee")
        assert not as_value(pane,"proposal"),"category change retained stale result"
        invoke(root,"propose")
        plan=as_value(pane,"proposal")
        assert plan["ok"] is True
        assert plan["estimatedAvailableAfterCents"]==-750
        assert plan["estimatedOverspent"] is True

        invoke(root,"switchMonth")
        assert prop(pane,"open") is False
        assert not as_value(pane,"proposal")
        invoke(root,"beginIncome")
        assert prop(pane,"open") is False
        invoke(root,"resetSource")
        invoke(root,"beginIncome")
        assert prop(pane,"open") is False, "income must refuse at open"

        invoke(root,"openFixture")
        invoke(root,"selectGroceries")
        invoke(root,"propose")
        assert as_value(pane,"proposal")["ok"] is True
        invoke(root,"duplicateCategory")
        assert prop(pane,"open") is False
        invoke(root,"openFixture")
        invoke(root,"selectGroceries")
        assert prop(pane,"selectedCategoryId")=="", "duplicate picker must refuse"
        # Force malformed selection directly to test policy's defensive
        # refusal, even when a caller bypasses the normal picker.
        setprop(pane,"selectedCategoryId","groceries")
        invoke(root,"propose")
        assert prop(pane,"errorText")=="CATEGORY AMBIGUOUS OR UNAVAILABLE"

        invoke(root,"breakSource")
        assert prop(pane,"sourceReady") is False
        assert prop(pane,"open") is False
        invoke(root,"openFixture")
        assert prop(pane,"open") is False
        invoke(root,"noSource")
        assert prop(pane,"sourceReady") is False
        print("FinanceW M3a actual expense preview QML with fictional data: PASS")
    finally:
        root.close()
        root.deleteLater()
        engine.deleteLater()
        app.processEvents()
