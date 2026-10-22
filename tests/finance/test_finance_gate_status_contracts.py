#!/usr/bin/env python3
"""FinanceW D13 read-only allocation gate and funding readiness UI."""
from pathlib import Path

root=Path(__file__).resolve().parents[2]
widget=(root/"widgets/FinanceW.qml").read_text()
service=(root/"services/finance/FinanceAllocationGateCheck.qml").read_text()
probe=(root/"scripts/finance/check_allocation_gate.mjs").read_text()
writer=(root/"scripts/finance/write_allocation.mjs").read_text()

assert 'FinanceServices.FinanceAllocationGateCheck {' in widget
assert 'id: allocationGateCheck' in widget
assert 'id: checkAllocationLock' in widget
assert 'label: "CHECK WRITE LOCK"' in widget
assert 'onLeftClicked: allocationGateCheck.check()' in widget
assert 'text: allocationGateCheck.message' in widget
assert widget.index('id: checkAllocationLock') < widget.index('id: allocationPreviewPane')
assert 'financeBudget.snapshot.toBudgetCents === 0' in widget
assert 'financeBudget.snapshot.toBudgetCents < 0' in widget
assert 'NO UNALLOCATED FUNDS' in widget
assert 'REVIEW INCOME AND OPENING BALANCES IN ACTUAL' in widget
assert 'UNALLOCATED FUNDS AVAILABLE FOR CATEGORY PLANNING' in widget

assert 'Quickshell.shellPath("scripts/finance/check_allocation_gate.mjs")' in service
assert 'FINANCEW_ALLOCATION_GATE ' in service
assert 'lockCheck.state="checking"' not in service  # state changes only on explicit check
assert 'state = "checking";' in service
assert 'state: "unchecked"' in service
assert 'if (probe.running || state === "checking")' in service
assert 'WRITES LOCKED // NO ALLOCATION PERMIT' in service
assert 'PERMIT DETECTED // DO NOT TEST LIVE WRITES' in service
assert 'UNSAFE PERMISSION FILE // REVIEW REQUIRED' in service
assert 'onExited: function(exitCode, exitStatus)' in service
assert "FINANCEW_ALLOCATION_RESULT" not in service
assert 'Process {' in service
for forbidden in ("stdinEnabled: true","writeFile(","LocalStorage","Settings {",
                  "Qt.openUrlExternally","setBudgetAmount(","api."):
    assert forbidden not in service,forbidden
assert 'import {lstat,readFile} from "node:fs/promises";' in probe
assert 'info.isFile()' in probe
assert '(info.mode & 0o077)!==0' in probe
assert 'permit-present' in probe and 'unsafe' in probe and 'locked' in probe
for forbidden in ("@actual-app/api","writeFile(","mkdir(","open(","unlink("):
    assert forbidden not in probe,forbidden
# D13 may only inspect the gate, never alter the D12c writer requirements.
assert 'privateFile(join(config,"allocation-writes-enabled"))' in writer
assert 'FINANCEW_ALLOCATION_WRITES_APPROVED' in writer
print("FinanceW D13 permission probe and funding status contracts: PASS")
