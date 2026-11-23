#!/usr/bin/env python3
"""FinanceW Simple M2b writer authority: M2c mounts view-only UI only."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
writer=(root/"scripts/finance/write_envelope_move.mjs").read_text()
guard=(root/"scripts/finance/envelope_move_guard.mjs").read_text()
rootqml=(root/"widgets/FinanceW.qml").read_text()
pane=(root/"widgets/FinanceEnvelopeMovePreviewPane.qml").read_text()
existing=(root/"scripts/finance/write_allocation.mjs").read_text()

# The M2c mounted preview never activates the separate M2b financial writer.
assert 'write_envelope_move.mjs' not in rootqml
assert 'write_envelope_move.mjs' not in pane
assert "FINANCEW_ENVELOPE_MOVES_APPROVED" not in rootqml
assert "FINANCEW_ENVELOPE_MOVES_APPROVED" not in pane
assert "signal saveRequested" not in pane
assert "signal moveRequested" not in pane
assert rootqml.count('FinanceEnvelopeMovePreviewPane {') == 1
assert "setBudgetAmount(" not in rootqml
assert "setBudgetAmount(" not in pane

# This is a NEW, explicit, operator-controlled permit, not the pre-existing
# per-category allocation permit. No installer/settings auto-provisions it.
assert 'join(config,"envelope-moves-enabled")' in writer
assert '"FINANCEW_ENVELOPE_MOVES_APPROVED"' in writer
assert 'allocation-writes-enabled' not in writer
assert "transaction-writes-enabled" not in writer
assert "financew-envelope-move-" in writer
assert 'FINANCEW_ENVELOPE_MOVE_RESULT ' in writer
assert 'validateEnvelopeMoveCommand(command)' in writer
assert 'executeEnvelopeMove({' in writer
assert 'const journalName="envelope-move-"+command.requestId+".json";' in writer
assert 'action:"allocation:move-envelope"' in writer

# Same global lock and durable journal directory as the existing D12 writer.
for code in (writer,existing):
    assert 'join(homedir(),".local","state","financew","operations")' in code
    assert 'const lockPath=join(journalDir,".write-lock");' in code
    assert 'await open(lockPath,"wx",0o600)' in code
    assert "recovery-needed" in code
    assert 'entry.status!=="committed"' in code
assert 'await file.sync();' in writer
assert 'await fsyncDirectory(journalDir);' in writer
assert 'attempted=true;' in writer
assert 'if(attempted)return "uncertain";' in writer
assert 'if(priorNames.includes(journalName)' in writer
assert 'name.endsWith("-"+command.requestId+".json")' in writer
assert 'readActualServerURL()' in writer
assert '"http://127.0.0.1:5006"' in writer
assert '.update(serverURL+"\\0"+syncId)' in writer
assert 'if(command.sourceKey!==expectedKey)' in writer
assert 'const password=await privateFile(' in writer
assert 'const syncId=await privateFile(' in writer

# Preflight BOTH categories before the irreversible attempted marker.
for needle in (
    "export function validateEnvelopeMoveCommand(input)",
    "export function preflightEnvelopeMove(input,budget)",
    "export async function executeEnvelopeMove({api,input,recordAttempt})",
    'input.action!=="move-envelope"',
    "input.fromCategoryId===input.toCategoryId",
    "from.budgeted!==cmd.expectedFromBudgetedCents",
    "from.balance!==cmd.expectedFromAvailableCents",
    "to.budgeted!==cmd.expectedToBudgetedCents",
    "to.balance!==cmd.expectedToAvailableCents",
    "budget.toBudget!==cmd.expectedToBudgetCents",
    "cmd.moveCents>from.balance",
    "cmd.moveCents>from.budgeted",
    "await recordAttempt(cmd);",
    "await api.setBudgetAmount(cmd.month,cmd.fromCategoryId,checked.nextFromBudgeted);",
    "await api.setBudgetAmount(cmd.month,cmd.toCategoryId,checked.nextToBudgeted);",
    "await api.sync();",
    "const after=await api.getBudgetMonth(cmd.month);",
    "after.toBudget!==checked.toBudgetUnchanged",
    'refuse("uncertain-write")',
):
    assert needle in guard,needle
assert guard.index("await recordAttempt(cmd);") < guard.index(
    "await api.setBudgetAmount(cmd.month,cmd.fromCategoryId")
assert guard.index("await api.setBudgetAmount(cmd.month,cmd.toCategoryId") < guard.index(
    "await api.sync();")
assert "rollback" in guard.lower()  # Documentation explicitly refuses rollback
assert "transaction" in guard.lower()  # Never claim the pair is database-atomic
assert "await api.setBudgetAmount" not in writer
assert "writeFile(" not in guard
for forbidden in ("Process {","LocalStorage","fetch(",
                  "FINANCEW_ENVELOPE_MOVES_APPROVED","createPermit(",
                  "replay(", "retry("):
    assert forbidden not in guard,forbidden
print("FinanceW Simple M2b guarded writer remains dormant after M2c: PASS")
