#!/usr/bin/env python3
"""FinanceW Budget Simple/Advanced selector integration and no-write contract."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
qml = (root / "widgets/FinanceW.qml").read_text(encoding="utf-8")

# One budget and one set of services; Simple is initial presentation state.
assert 'property string budgetExperienceMode: "simple"' in qml
assert 'readonly property bool advancedOpen: budgetExperienceMode === "advanced"' in qml
assert 'property string budgetSection: "budget"' in qml
assert qml.count("FinanceServices.FinanceBudgetReadService {") == 1
assert qml.count("FinanceBudgetGrid {") == 1
assert qml.count("FinanceQuickAddPane {") == 1
assert qml.count("FinanceAccountsPane {") == 1
assert qml.count("FinanceCategoriesPane {") == 1
assert qml.count("FinanceTransactionDraftPane {") == 1
assert qml.count("FinanceServices.FinanceTransactionWriteService {") == 1
assert qml.count("FinanceServices.FinanceAllocationWriteService {") == 1

# Exact same Actual snapshot and existing guarded writers in either mode.
for preserved in (
    "snapshot: financeBudget.snapshot",
    "financeFundingWrite.submit(payload);",
    "financeAllocationWrite.submit(payload);",
    "financeWrite.submit(payload);",
    "financeCategoryWrite.submit(payload);",
    "financeCategoryGroupWrite.submit(payload);",
):
    assert preserved in qml, preserved

# Mode controls precede section tabs, are mutually selected, and cannot
# override active draft/write recovery constraints.
assert qml.index("id: budgetExperienceSelector") < qml.index("id: budgetSectionTabs")
assert qml.index("id: budgetSectionTabs") < qml.index("id: quickAddMoney")
assert 'objectName: "budgetSimpleModeAction"' in qml
assert 'objectName: "budgetAdvancedModeAction"' in qml
assert 'selected: root.budgetExperienceMode==="simple"' in qml
assert 'selected: root.budgetExperienceMode==="advanced"' in qml
assert 'available: !root.budgetExperienceSwitchBlocked' in qml
assert 'onLeftClicked: root.selectBudgetExperience("simple")' in qml
assert 'onLeftClicked: root.selectBudgetExperience("advanced")' in qml

guard = qml.split("readonly property bool budgetExperienceSwitchBlocked:",1)[1].split(
    "function selectBudgetExperience(next)",1)[0]
for protected in (
    "transactionDraftPane.open",
    "quickAddPane.open",
    "guidedFundingPane.expanded",
    "allocationPreviewPane.open",
    'financeCategoriesPane.openMode !== ""',
    'financeCategoriesPane.groupDraftMode !== ""',
    'financeDrafts.state === "pending"',
):
    assert protected in guard, protected
for service in (
    "financeWrite", "financeFundingWrite", "financeAllocationWrite",
    "financeCategoryWrite", "financeCategoryGroupWrite",
):
    for state in ("pending", "uncertain"):
        assert f'{service}.state === "{state}"' in guard, (service, state)

transition = qml.split("function selectBudgetExperience(next)",1)[1].split(
    "function selectBudgetSection(section)",1)[0]
for required in (
    'next !== "simple" && next !== "advanced"',
    "if (next === budgetExperienceMode) return true;",
    "if (budgetExperienceSwitchBlocked) return false;",
    "budgetExperienceMode = next;",
    "fundingReviewOpen = false;",
):
    assert required in transition, required
for forbidden in ("submit(", "upsert(", "remove(", "refresh(", "saveRequested(",
                  "Process {", "createCategory(", "setBudgetAmount("):
    assert forbidden not in transition, forbidden

assert "id: advancedBudgetDetails" in qml
assert re.search(r"id:\s*advancedBudgetDetails\s+width: parent.width"
                 r"\s+spacing: 7\s+visible: root.advancedOpen", qml)
assert 'root.advancedOpen=!root.advancedOpen' not in qml
assert "id: advancedToggle" not in qml
assert 'text: "FINISH OR CLOSE ACTIVE EDITORS BEFORE SWITCHING MODES"' in qml
assert 'text: root.advancedOpen' in qml
assert "HIDE ADVANCED" not in qml

# Disabling a view must not silently disable ordinary budget/category tabs.
for section in ("budget", "transactions", "accounts", "categories"):
    assert '{key:"'+section+'"' in qml
assert 'visible: root.budgetSection==="categories"' in qml
assert 'visible: root.budgetSection==="transactions"' in qml
assert 'visible: root.budgetSection==="accounts"' in qml
print("FinanceW Simple M1 source/authority/transition contracts: PASS")
