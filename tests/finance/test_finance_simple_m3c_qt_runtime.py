#!/usr/bin/env python3
"""Real FinanceW D9 expense editor + M3a category pane, fictional Qt data only."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QT_QUICK_BACKEND","software")
from PySide6.QtCore import QObject,QMetaObject,QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent,QQmlEngine

app=QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="financew-m3c-view-") as temp:
    stub=Path(temp)/"Quickshell"
    stub.mkdir()
    (stub/"qmldir").write_text("module Quickshell\nStub 1.0 Stub.qml\n")
    (stub/"Stub.qml").write_text("import QtQuick\nItem {}\n")
    engine=QQmlEngine()
    engine.addImportPath(temp)
    path=Path(__file__).resolve().with_name(
        "finance_simple_m3c_ui_runtime_harness.qml")
    component=QQmlComponent(engine,QUrl.fromLocalFile(str(path)))
    if component.isError():
        raise RuntimeError("QML load: "+"; ".join(map(str,component.errors())))
    root=component.create()
    if root is None:
        raise RuntimeError("QML create: "+"; ".join(map(str,component.errors())))

    def invoke(obj,method):
        assert QMetaObject.invokeMethod(obj,method),method
        app.processEvents()
    def value(obj,key):
        app.processEvents()
        v=obj.property(key)
        return v.toVariant() if hasattr(v,"toVariant") else v
    def setprop(obj,key,val):
        assert obj.setProperty(key,val),key
        app.processEvents()
    try:
        draft=root.findChild(QObject,"actualM3cTransactionDraft")
        pane=root.findChild(QObject,"actualM3cCategoryPreview")
        assert draft is not None and pane is not None
        assert value(draft,"allowCategoryPreview") is True
        assert value(draft,"categoryPreviewArmed") is False

        invoke(draft,"begin")
        assert value(draft,"open") is True
        # Incomplete expense draft cannot open a category picker.
        invoke(draft,"requestCategoryPreview")
        assert value(root,"previewCount")==0
        assert value(pane,"open") is False

        setprop(draft,"dateText","2026-11-23")
        setprop(draft,"payeeText","Fictional Supermarket")
        setprop(draft,"amountText","12.50")
        assert value(draft,"validationError")==""
        invoke(draft,"requestCategoryPreview")
        assert value(root,"previewCount")==1
        assert value(draft,"categoryPreviewArmed") is True
        assert value(pane,"open") is True

        invoke(pane,"nextCategory")
        assert value(pane,"selectedCategoryId")=="groceries"
        invoke(pane,"calculate")
        plan=value(pane,"proposal")
        assert plan["ok"] is True,plan
        assert plan["readOnly"] is True
        assert plan["savesToActual"] is False
        assert plan["estimatedAvailableAfterCents"]==6250

        # Calling existing CONFIRM SAVE directly must not bypass the UI.
        setprop(draft,"reviewed",True)
        invoke(draft,"requestCommit")
        assert value(root,"savedCount")==0
        invoke(pane,"clear")
        assert value(draft,"categoryPreviewArmed") is True
        invoke(draft,"requestCommit")
        assert value(root,"savedCount")==0

        # Edits invalidate the old category plan. The fail-closed hold
        # survives until the operator discards the category plan.
        invoke(draft,"requestCategoryPreview")
        invoke(pane,"nextCategory")
        invoke(pane,"calculate")
        assert value(pane,"proposal")["ok"] is True
        setprop(draft,"amountText","13.00")
        assert value(pane,"open") is False
        assert value(draft,"categoryPreviewArmed") is True
        invoke(draft,"requestCommit")
        assert value(root,"savedCount")==0

        # Explicit DISCARD returns only to old UNCATEGORIZED Save behavior.
        invoke(draft,"discardCategoryPreview")
        assert value(draft,"categoryPreviewArmed") is False
        assert value(draft,"reviewed") is False
        setprop(draft,"reviewed",True)
        invoke(draft,"requestCommit")
        assert value(root,"savedCount")==1
        sent=value(root,"savedPayload")
        assert sent["action"]=="create"
        assert sent["amountCents"]==-1300
        assert "categoryId" not in sent
        assert "category" not in sent

        # Income is never eligible for categorized-expense preview.
        invoke(draft,"clear")
        invoke(draft,"begin")
        setprop(draft,"dateText","2026-11-23")
        setprop(draft,"payeeText","Fictional Pay")
        setprop(draft,"amountText","10.00")
        setprop(draft,"direction","income")
        invoke(draft,"requestCategoryPreview")
        assert value(pane,"open") is False
        assert value(root,"previewCount")==2

        # A new source snapshot clears an in-flight category proposal
        # and any stale draft context through the existing source handlers.
        setprop(draft,"direction","expense")
        invoke(draft,"requestCategoryPreview")
        assert value(draft,"categoryPreviewArmed") is True
        invoke(root,"refreshSource")
        assert value(pane,"open") is False
        assert value(draft,"categoryPreviewArmed") is False
        invoke(root,"switchMonth")
        assert value(pane,"open") is False
        print("FinanceW Simple M3c real editor/category QML no-save integration: PASS")
    finally:
        root.close()
        root.deleteLater()
        engine.deleteLater()
        app.processEvents()
