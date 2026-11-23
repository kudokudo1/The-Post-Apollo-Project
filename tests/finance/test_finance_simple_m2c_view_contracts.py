#!/usr/bin/env python3
"""FinanceW Simple M2c mount of a view-only envelope move preview.

This contract checks integration into the actual FinanceW QML source,
while the existing Qt suite loads the real child preview component.
Neither source validation nor offscreen Qt is a live-budget acceptance.
"""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
menu=(root/"widgets/FinanceW.qml").read_text(encoding="utf-8")
pane=(root/"widgets/FinanceEnvelopeMovePreviewPane.qml").read_text(encoding="utf-8")
writer=(root/"scripts/finance/write_envelope_move.mjs").read_text(encoding="utf-8")

# Exactly one shared read-only snapshot; no extra ledger, bridge or writer.
assert menu.count("FinanceEnvelopeMovePreviewPane {")==1
assert menu.count("FinanceServices.FinanceBudgetReadService {")==1
assert menu.count("FinanceBudgetGrid {")==1
assert 'id: envelopeMovePreviewPane' in menu
assert 'objectName: "financeBudgetEnvelopeMovePreview"' in menu
assert 'snapshot: financeBudget.snapshot' in menu
assert 'write_envelope_move.mjs' not in menu
assert 'write_envelope_move.mjs' not in pane
assert 'envelope-moves-enabled' not in menu
assert 'FINANCEW_ENVELOPE_MOVES_APPROVED' not in menu

# The view-only button is in the existing Budget tab directly between
# Add Money and the grid, with unchanged sections and no fake save action.
assert menu.count('id: moveEnvelopePreviewAction')==1
assert 'objectName: "moveEnvelopePreviewAction"' in menu
assert 'label: envelopeMovePreviewPane.open' in menu
assert '"HIDE MOVE MONEY PREVIEW" : "MOVE MONEY // PREVIEW"' in menu
assert 'visible: root.budgetExperienceMode==="simple"' in menu
assert 'available: envelopeMovePreviewPane.open || root.envelopeMoveLaunchReady' in menu
assert 'onLeftClicked: {' in menu
assert 'envelopeMovePreviewPane.clear();' in menu
assert 'envelopeMovePreviewPane.begin();' in menu
assert menu.index('id: quickAddPane') < menu.index(
    'id: moveEnvelopePreviewAction') < menu.index(
    'id: envelopeMovePreviewPane') < menu.index(
    'id: financeBudgetGrid')
assert menu.count('id: budgetSectionTabs')==1
assert menu.count('id: transactionsSectionContent')==1

# Source, month and amount are revalidated by the pure read-only plan.
for phrase in (
    'snapshot.schemaVersion===1',
    'snapshot.readOnly===true',
    'snapshot.source==="actual-budget"',
    '/^[a-f0-9]{64}$/.test(snapshot.sourceKey)',
    'Number.isSafeInteger(snapshot.toBudgetCents)',
    'Array.isArray(snapshot.categories)',
    'onSnapshotChanged: clear()',
    'onFromCategoryIdChanged: invalidatePreview()',
    'onToCategoryIdChanged: invalidatePreview()',
    'onAmountTextChanged: invalidatePreview()',
    'MoveRules.previewEnvelopeMove(snapshot,fromCategoryId,',
    'text: "PREVIEW ONLY // NO CHANGES SAVED // WRITER NOT CONNECTED"',
):
    assert phrase in pane,phrase

# Opening is only permitted in Simple's current Budget tab, with a ready
# source and no other editor or unresolved financial write.
ready=menu.split('readonly property bool envelopeMoveLaunchReady:',1)[1].split(
    'function selectBudgetExperience(next)',1)[0]
for phrase in (
    'menuOpen',
    'selectedMainMode === "budget"',
    'selectedBudgetSubMode === "budget"',
    'budgetExperienceMode === "simple"',
    'budgetSection === "budget"',
    'financeBudget.state === "ready"',
    '!financeBudget.loading',
    '!budgetExperienceSwitchBlocked',
    'envelopeMovePreviewPane.sourceReady',
    'envelopeMovePreviewPane.choices.length >= 2',
):
    assert phrase in ready,phrase

guard=menu.split('readonly property bool budgetExperienceSwitchBlocked:',1)[1].split(
    'readonly property bool envelopeMoveLaunchReady:',1)[0]
assert 'envelopeMovePreviewPane.open' in guard
assert '!envelopeMovePreviewPane.open' in menu
assert '&& !envelopeMovePreviewPane.open' in menu

# Dispose preview on close and when leaving the Budget area; no stale
# approval/preview can reappear after switching tabs, modes or months.
close=menu.split('onMenuOpenChanged:',1)[1].split('onKeyboardActiveChanged:',1)[0]
assert 'envelopeMovePreviewPane.clear();' in close
for signal, next_signal, condition in (
    ('function onSelectedMainModeChanged()',
     'function onSelectedBudgetSubModeChanged()', 'root.selectedMainMode!=="budget"'),
    ('function onSelectedBudgetSubModeChanged()',
     'function onBudgetSectionChanged()', 'root.selectedBudgetSubMode!=="budget"'),
    ('function onBudgetSectionChanged()',
     'function mainModeName()', 'root.budgetSection!=="budget"'),
):
    segment=menu.split(signal,1)[1].split(next_signal,1)[0]
    assert condition in segment,signal
    assert 'envelopeMovePreviewPane.clear();' in segment,signal

# A displayed preview is never a money movement. No save/event bridges
# exist in the mounted child, and the M2b CLI is still dormant.
assert "signal saveRequested" not in pane
assert "signal moveRequested" not in pane
assert "onSaveRequested" not in pane
assert "onMoveRequested" not in pane
assert "setBudgetAmount(" not in pane
assert "setBudgetAmount(" not in menu
assert "Process {" not in pane
assert 'join(config,"envelope-moves-enabled")' in writer
print("FinanceW Simple M2c root-mounted preview, no financial-write bridge: PASS")
