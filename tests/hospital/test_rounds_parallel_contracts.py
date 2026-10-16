#!/usr/bin/env python3
"""Rounds concurrency contract: bounded, independent audit slots."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
s = (root / "services/hospital/HospitalRoundsService.qml").read_text()
for token in (
    "HospitalAuditService { id: auditProbeA }",
    "HospitalAuditService { id: auditProbeB }",
    "HospitalAuditService { id: auditProbeC }",
    "function scanNext()",
    "function finishSlot(slot)",
    "Object.keys(inFlightFloors).length === 0",
    "completedFloors += 1",
    "captureCurrentFloor(floor, probe)",
    "Qt.callLater(scanNext)",
    'status: "AUDIT_ERROR"',
    'status: "LOCAL_ONLY"',
):
    assert token in s, f"missing Rounds concurrency safeguard: {token}"
for legacy in ("scanInFlight", "finishCurrentFloor", "currentFloor", "auditProbe.runAudit"):
    assert legacy not in s, f"stale sequential audit code: {legacy}"
assert s.count("HospitalAuditService { id: auditProbe") == 3
assert "probe.runAudit(true)" in s
assert s.count("onRunningChanged()") == 3
print("HOSPITAL ROUNDS // BOUNDED PARALLEL AUDIT CONTRACT PASS")
