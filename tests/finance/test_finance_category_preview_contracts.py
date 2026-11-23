#!/usr/bin/env python3
"""FinanceW category draft UI is preview-only and isolated from financial writes."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceCategoriesPane.qml").read_text()
plan=(root/"services/finance/FinanceCategoryPlan.js").read_text()
group_plan=(root/"services/finance/FinanceCategoryGroupPlan.js").read_text()
read=(root/"scripts/finance/actual_readonly.mjs").read_text()
menu=(root/"widgets/FinanceW.qml").read_text()

for expected in (
    'property string openMode: ""',
    'property string sourceAtOpen: ""',
    'property string monthAtOpen: ""',
    'function beginCreate()',
    'function beginRename(row)',
    'function clearDraft()',
    'onSnapshotChanged:',
    'onVisibleChanged: if(!visible)clearDraft()',
    'CategoryPlan.previewCategoryPlan(',
    '"+ NEW CATEGORY"',
    'label: "RENAME"',
    'label: "PREVIEW"',
    'label: "CANCEL"',
    'label: "EDIT SET"',
    'previewVisible=categoryPane.plan.ok',
    'NOT SAVED // ACTUAL IS UNCHANGED',
):
    assert expected in pane, expected

for expected in (
    'snapshot.readOnly!==true',
    'snapshot.source!=="actual-budget"',
    'snapshot.sourceKey',
    'snapshot.month',
    'Array.isArray(snapshot.categoryGroups)',
    'mode!=="create" && mode!=="rename"',
    'current.name.trim().toLowerCase()===name.toLowerCase()',
    'NAME ALREADY USED IN THIS GROUP',
    'savesToActual:false',
):
    assert expected in plan, expected

for expected in (
    'groupRows.push({id:group.id,name:group.name})',
    'groupId: group.id',
    'categoryGroups: groupRows',
    'unexpected-category-group-identity',
):
    assert expected in read, expected

for code in (pane,plan):
    for forbidden in (
        'Process {','LocalStorage','Settings {','writeFile(',
        'createCategory(','updateCategory(','deleteCategory(',
        'api.','FINANCEW_CATEGORY_WRITES_APPROVED',
        'category-writes-enabled','financeFundingWrite.submit(',
        'financeAllocationWrite.submit('
    ):
        assert forbidden not in code, forbidden

# M4 expense-group controls are explicitly preview-only and remain in the
# Categories pane, without changes to shared FinanceW navigation or writers.
for expected in (
    'import "../services/finance/FinanceCategoryGroupPlan.js" as GroupPlan',
    'property string groupDraftMode: ""',
    'property string groupSourceAtOpen: ""',
    'property string groupMonthAtOpen: ""',
    'property string groupOriginalNameAtOpen: ""',
    'readonly property var groupPlan: GroupPlan.previewGroupPlan(',
    'function clearGroupDraft()',
    'function beginCreateGroup()',
    'function beginRenameGroup(row)',
    'onGroupDraftNameChanged:',
    'groupApprovalArmed=false;',
    'groupPreviewVisible=false;',
    'label: "PREVIEW GROUP"',
    'label: "CANCEL GROUP"',
    'label: "RENAME GROUP"',
    'CLOSE GROUP" : "+ NEW GROUP"',
    'NOT SAVED // ACTUAL GROUP UNCHANGED',
    'categoryPane.groupPlan.ok',
):
    assert expected in pane, expected

for expected in (
    'snapshot.readOnly!==true',
    'snapshot.source!=="actual-budget"',
    'snapshot.sourceKey',
    'snapshot.month',
    'Array.isArray(snapshot.categoryGroups)',
    'mode!=="create" && mode!=="rename"',
    'GROUP NAME ALREADY USED',
    'GROUP CHANGED // REVIEW AGAIN',
    'savesToActual:false',
):
    assert expected in group_plan, expected

for forbidden in (
    'Process {','LocalStorage','Settings {','writeFile(',
    'createCategoryGroup(','updateCategoryGroup(','deleteCategoryGroup(',
    'api.','FINANCEW_CATEGORY_WRITES_APPROVED','category-writes-enabled',
    'saveRequested(','FINANCEW_CATEGORY_RESULT'
):
    assert forbidden not in group_plan, forbidden

# M7 category-group clarity uses the authenticated category->group IDs only.
# It adds no writer, no authorization, and no shared FinanceW routing.
for expected in (
    'AMBIGUOUS GROUP IDS // REFRESH',
    'INCOME GROUP CANNOT BE RENAMED',
    'other.id===g.id',
    'current.is_income===true',
):
    assert expected in group_plan, expected

for expected in (
    'row.is_income===true',
    'g.id===row.id',
    'g.name===row.name',
    'groupRow.modelData.name+" // "',
    'categoryPane.categories.filter(function(c)',
    'c.groupId===groupRow.modelData.id;',
    ').length+" CATEGORIES"',
    'groupRow.modelData.is_income!==true',
    'g.id===groupRow.modelData.id;',
):
    assert expected in pane, expected

# M8 category search must be a pure local view/filter with explicit states.
# No new source process, financial writer, or permission gate.
for expected in (
    'function clearCategorySearch()',
    'filterText="";',
    'objectName: "categorySearchInput"',
    'objectName: "categoryClearSearchAction"',
    'label: "CLEAR SEARCH"',
    'available: categoryPane.filterText.length>0',
    'onLeftClicked: categoryPane.clearCategorySearch()',
    'text: "SEARCH CATEGORIES / GROUPS"',
    'objectName: "categorySearchSummary"',
    '"SHOWING "+categoryPane.displayed.length+" / "',
    'objectName: "categoryFilteredRow"',
    'objectName: "categorySearchEmptyState"',
    'NO SEARCH MATCHES // CLEAR SEARCH',
    'NO CATEGORIES IN THIS BUDGET',
    'LOAD A BUDGET TO VIEW CATEGORIES',
):
    assert expected in pane, expected

# M9 view-only attention filters; existing write boundaries remain unchanged.
for needle in (
    'property bool onlyOverspent: false',
    'readonly property int overspentCount:',
    'function toggleOverspentFilter()',
    'objectName: "categoryOverspentOnlyAction"',
    'selected: categoryPane.onlyOverspent',
    'NO OVERSPENT CATEGORIES THIS MONTH',
    'NO OVERSPENT SEARCH MATCHES // CLEAR SEARCH OR FILTER',
):
    assert needle in pane, needle

# M6 adds a separately gated service; group proposal policy remains pure.
assert 'signal groupSaveRequested(var payload)' in pane
assert 'FinanceCategoryGroupWriteService' not in pane
assert 'createCategoryGroup(' not in pane
assert 'updateCategoryGroup(' not in pane

# The existing guarded allocation entry point remains the only action
# available through the list's EDIT SET link.
assert 'id: financeCategoriesPane' in menu
assert 'onEditBudgetRequested: function(category)' in menu
assert 'financeBudgetGrid.choose(category);' in menu
print("FinanceW category and group preview policies remain non-mutating: PASS")
