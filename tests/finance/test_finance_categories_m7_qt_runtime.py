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

        # M8: search is a pure view filter, not a source or writer mutation.
        def category_rows():
            return matching_items("categoryFilteredRow")

        summary = matching_items("categorySearchSummary")
        empty = matching_items("categorySearchEmptyState")
        clear = matching_items("categoryClearSearchAction")
        assert len(summary) == len(empty) == len(clear) == 1
        assert len(category_rows()) == 2
        assert prop(clear[0], "available") is False
        assert prop(summary[0], "text") == "SHOWING 2 / 2 CATEGORIES"

        setprop(pane, "filterText", "RENT")
        assert len(category_rows()) == 1
        assert prop(summary[0], "text") == "SHOWING 1 / 2 CATEGORIES"
        assert prop(clear[0], "available") is True
        setprop(pane, "filterText", "wAnTs")
        assert len(category_rows()) == 1

        setprop(pane, "filterText", "not-a-real-category")
        assert len(category_rows()) == 0
        assert prop(empty[0], "visible") is True
        assert prop(empty[0], "text") == "NO SEARCH MATCHES // CLEAR SEARCH"
        invoke(pane, "clearCategorySearch")
        assert prop(pane, "filterText") == ""
        assert len(category_rows()) == 2
        assert prop(clear[0], "available") is False

        # M10: sort only the displayed view, never the underlying snapshot.
        # Invalid balances go last, and ties preserve source order.
        sorter = matching_items("categoryLowestAvailableAction")
        assert len(sorter) == 1
        assert prop(sorter[0], "available") is True
        assert prop(sorter[0], "selected") is False

        def displayed_ids():
            value = prop(pane, "displayed")
            return [row["id"] for row in value.toVariant()]

        assert displayed_ids() == ["rent", "coffee"]
        invoke(pane, "toggleLowestAvailableSort")
        assert prop(sorter[0], "selected") is True
        assert displayed_ids() == ["coffee", "rent"]

        setprop(pane, "filterText", "RENT")
        assert displayed_ids() == ["rent"]
        invoke(pane, "clearCategorySearch")
        invoke(root, "mixedAvailableBalanceFixture")
        assert displayed_ids() == [
            "overdrawn", "coffee", "groceries", "rent", "unknown"
        ], displayed_ids()
        assert prop(pane, "overspentCount") == 1

        invoke(pane, "toggleOverspentFilter")
        assert displayed_ids() == ["overdrawn"]
        invoke(pane, "toggleOverspentFilter")
        assert displayed_ids() == [
            "overdrawn", "coffee", "groceries", "rent", "unknown"
        ]
        invoke(root, "refreshFixture")
        assert prop(pane, "lowestAvailableFirst") is True
        assert displayed_ids()[0] == "overdrawn"
        invoke(root, "switchMonth")
        assert prop(pane, "lowestAvailableFirst") is False
        assert displayed_ids() == [
            "rent", "coffee", "groceries", "overdrawn", "unknown"
        ]
        invoke(root, "resetFixture")
        assert displayed_ids() == ["rent", "coffee"]
        invoke(pane, "toggleLowestAvailableSort")
        assert displayed_ids() == ["coffee", "rent"]
        invoke(root, "noBudgetFixture")
        assert prop(sorter[0], "available") is False
        assert prop(pane, "lowestAvailableFirst") is False
        invoke(root, "resetFixture")
        assert displayed_ids() == ["rent", "coffee"]

        # M9: overspent-only is a read-only attention filter. A negative
        # available balance, not a category's name or budget size, controls it.
        attention = matching_items("categoryOverspentOnlyAction")
        assert len(attention) == 1
        assert prop(pane, "overspentCount") == 0
        assert prop(attention[0], "selected") is False
        assert prop(attention[0], "label") == "OVERSPENT ONLY // 0"

        invoke(pane, "toggleOverspentFilter")
        assert prop(pane, "onlyOverspent") is True
        assert prop(attention[0], "selected") is True
        assert len(category_rows()) == 0
        assert prop(empty[0], "text") == "NO OVERSPENT CATEGORIES THIS MONTH"

        invoke(root, "overspentCoffeeFixture")
        assert prop(pane, "onlyOverspent") is True
        assert prop(pane, "overspentCount") == 1
        assert len(category_rows()) == 1
        assert prop(attention[0], "label") == "OVERSPENT ONLY // 1"

        setprop(pane, "filterText", "Rent")
        assert len(category_rows()) == 0
        assert prop(empty[0], "text") == (
            "NO OVERSPENT SEARCH MATCHES // CLEAR SEARCH OR FILTER"
        )
        invoke(pane, "clearCategorySearch")
        assert prop(pane, "filterText") == ""
        assert prop(pane, "onlyOverspent") is True
        assert len(category_rows()) == 1

        # Malformed or nonnumeric balance values do not become overspent.
        invoke(root, "invalidBalanceFixture")
        assert prop(pane, "overspentCount") == 0
        assert len(category_rows()) == 0
        invoke(pane, "toggleOverspentFilter")
        assert prop(pane, "onlyOverspent") is False
        assert len(category_rows()) == 2

        # A same-source refresh preserves filter intent; changing the month
        # or losing the source resets it so another budget is not obscured.
        invoke(root, "overspentCoffeeFixture")
        invoke(pane, "toggleOverspentFilter")
        setprop(pane, "filterText", "wants")
        invoke(root, "refreshFixture")
        assert prop(pane, "onlyOverspent") is True
        assert prop(pane, "filterText") == "wants"
        assert len(category_rows()) == 1
        invoke(root, "switchMonth")
        assert prop(pane, "onlyOverspent") is False
        assert prop(pane, "filterText") == ""
        assert len(category_rows()) == 2

        invoke(root, "emptyCategoriesFixture")
        assert len(category_rows()) == 0
        assert prop(summary[0], "text") == "SHOWING 0 / 0 CATEGORIES"
        assert prop(empty[0], "text") == "NO CATEGORIES IN THIS BUDGET"
        invoke(root, "noBudgetFixture")
        assert prop(attention[0], "available") is False
        assert len(category_rows()) == 0
        assert prop(summary[0], "text") == "CATEGORIES // NO AUTHENTICATED BUDGET"
        assert prop(empty[0], "text") == "LOAD A BUDGET TO VIEW CATEGORIES"
        invoke(root, "resetFixture")
        assert len(category_rows()) == 2

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

        # The category-name editor has the same snapshot invalidation
        # guarantee. A stale name cannot retain a previously armed preview.
        invoke(root, "resetFixture")
        invoke(root, "openRentCategoryRename")
        assert prop(pane, "openMode") == "rename"
        assert prop(pane, "selectedCategoryId") == "rent"
        setprop(pane, "draftName", "Housing")
        setprop(pane, "previewVisible", True)
        setprop(pane, "approvalArmed", True)
        invoke(root, "changeCategoryName")
        assert prop(pane, "openMode") == ""
        assert prop(pane, "approvalArmed") is False
        assert prop(pane, "previewVisible") is False

        # Navigating away from Categories discards an unsent group draft.
        invoke(root, "resetFixture")
        invoke(pane, "beginCreateGroup")
        setprop(pane, "groupDraftName", "Emergency")
        setprop(pane, "groupPreviewVisible", True)
        setprop(pane, "groupApprovalArmed", True)
        setprop(pane, "visible", False)
        assert prop(pane, "groupDraftMode") == ""
        assert prop(pane, "groupPreviewVisible") is False
        assert prop(pane, "groupApprovalArmed") is False
        setprop(pane, "visible", True)

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

        print("FinanceW Categories M10 real-pane Qt sorting/overspent/search lifecycle: PASS")
    finally:
        root.close()
        root.deleteLater()
        engine.deleteLater()
        app.processEvents()
