#!/usr/bin/env python3
"""Headless Qt smoke of the real FinanceCategoriesPane, not just source strings.

Fictional read-only source. No Quickshell process, write service, Actual API,
permission marker or live operator budget. This is not native acceptance.
"""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QObject, QMetaObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem


app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="financew-categories-m7-qml-") as temp:
    # ActionButton imports Quickshell but this harness must never start one.
    stub = Path(temp) / "Quickshell"
    stub.mkdir()
    (stub / "qmldir").write_text(
        "module Quickshell\nStub 1.0 Stub.qml\n", encoding="utf-8")
    (stub / "Stub.qml").write_text("import QtQuick\nItem {}\n",
                                   encoding="utf-8")

    engine = QQmlEngine()
    engine.addImportPath(temp)
    harness = Path(__file__).resolve().with_name(
        "finance_categories_m7_runtime_harness.qml")
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(harness)))
    if component.isError():
        raise RuntimeError("QML load: " + "; ".join(map(str, component.errors())))
    root = component.create()
    if root is None:
        raise RuntimeError("QML create: " + "; ".join(map(str, component.errors())))

    def invoke(obj, name):
        assert QMetaObject.invokeMethod(obj, name), f"QML method did not run: {name}"
        app.processEvents()

    def prop(obj, name):
        app.processEvents()
        return obj.property(name)

    def setprop(obj, name, value):
        assert obj.setProperty(name, value), f"QML property not set: {name}"
        app.processEvents()

    try:
        pane = root.findChild(QObject, "actualCategoriesPane")
        assert pane is not None, "real Categories pane was not instantiated"

        def visual_descendants(item):
            found = []
            for child in item.childItems():
                found.append(child)
                found.extend(visual_descendants(child))
            return found

        def matching_items(name):
            return [item for item in visual_descendants(pane)
                    if item.objectName() == name]

        def group_labels():
            return sorted(str(prop(x, "text")) for x in
                          matching_items("categoryGroupCountLabel"))

        def rename_actions():
            return matching_items("categoryGroupRenameAction")

        print("Qt fixture groups:", str(prop(pane, "groups"))[:500],
              "visual children:", len(visual_descendants(pane)),
              "label nodes:", len(matching_items("categoryGroupCountLabel")),
              flush=True)

        assert group_labels() == [
            "Empty // 0 CATEGORIES", "Needs // 1 CATEGORIES",
            "Wants // 1 CATEGORIES"
        ], group_labels()
        assert len(rename_actions()) == 3
        assert all(prop(x, "available") for x in rename_actions())

        # New group has a real QML lifecycle. No writer is instantiated.
        invoke(pane, "beginCreateGroup")
        assert prop(pane, "groupDraftMode") == "create"
        setprop(pane, "groupDraftName", "Utilities")
        setprop(pane, "groupPreviewVisible", True)
        setprop(pane, "groupApprovalArmed", True)
        assert prop(pane, "groupProposalEligible") is True

        # Editing a draft MUST disarm; old approval cannot survive an edit.
        setprop(pane, "groupDraftName", "Health")
        assert prop(pane, "groupPreviewVisible") is False
        assert prop(pane, "groupApprovalArmed") is False
        assert prop(pane, "groupProposalEligible") is False

        # Same-month refresh keeps editable draft, but invalidates preview.
        setprop(pane, "groupPreviewVisible", True)
        setprop(pane, "groupApprovalArmed", True)
        invoke(root, "refreshFixture")
        assert prop(pane, "groupDraftMode") == "create"
        assert prop(pane, "groupPreviewVisible") is False
        assert prop(pane, "groupApprovalArmed") is False
        assert prop(pane, "groupProposalEligible") is False

        # Explicit cancellation clears the draft without submitting a write.
        invoke(pane, "clearGroupDraft")
        assert prop(pane, "groupDraftMode") == ""
        assert prop(pane, "groupDraftName") == ""
        assert prop(pane, "groupSubmitted") is False

        # A changed month invalidates even an armed, unsent draft.
        invoke(pane, "beginCreateGroup")
        setprop(pane, "groupDraftName", "Transportation")
        setprop(pane, "groupPreviewVisible", True)
        setprop(pane, "groupApprovalArmed", True)
        invoke(root, "switchMonth")
        assert prop(pane, "groupDraftMode") == ""
        assert prop(pane, "groupPreviewVisible") is False
        assert prop(pane, "groupApprovalArmed") is False
        assert prop(pane, "groupSubmitted") is False

        invoke(root, "resetFixture")
        invoke(root, "openNeedsRename")
        assert prop(pane, "groupDraftMode") == "rename"
        assert prop(pane, "groupDraftId") == "needs"
        setprop(pane, "groupDraftName", "Essentials")
        setprop(pane, "groupPreviewVisible", True)
        setprop(pane, "groupApprovalArmed", True)
        invoke(root, "changeGroupName")
        assert prop(pane, "groupDraftMode") == ""
        assert prop(pane, "groupPreviewVisible") is False

        # Income-group rows are never renameable, even in an unexpected
        # source, and an ambiguous group ID cannot arm a preview.
        invoke(root, "resetFixture")
        invoke(root, "addIncomeGroup")
        actions = rename_actions()
        assert len(actions) == 4
        assert sum(prop(x, "available") is False for x in actions) == 1
        invoke(root, "openIncomeRename")
        assert prop(pane, "groupDraftMode") == ""

        invoke(root, "resetFixture")
        invoke(root, "corruptGroupIdentity")
        invoke(root, "openNeedsRename")
        assert prop(pane, "groupDraftMode") == ""
        invoke(pane, "beginCreateGroup")
        setprop(pane, "groupDraftName", "Housing")
        assert prop(pane, "groupProposalEligible") is False

        print("FinanceW Categories M7 real-pane Qt lifecycle/count smoke: PASS")
    finally:
        root.close()
        root.deleteLater()
        engine.deleteLater()
        app.processEvents()
