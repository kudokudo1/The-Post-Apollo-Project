#!/usr/bin/env python3
"""FinanceW category draft UI is preview-only and isolated from financial writes."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
pane=(root/"widgets/FinanceCategoriesPane.qml").read_text()
plan=(root/"services/finance/FinanceCategoryPlan.js").read_text()
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
    'label: "+ NEW CATEGORY"',
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
    'current.name===name',
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

# The existing guarded allocation entry point remains the only action
# available through the list's EDIT SET link.
assert 'id: financeCategoriesPane' in menu
assert 'onEditBudgetRequested: function(category)' in menu
assert 'financeBudgetGrid.choose(category);' in menu
print("FinanceW category draft/preview isolation: PASS")
