#!/usr/bin/env python3
"""Read-only local PX Doctor succession capability probe and Room display."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
view = (root / "widgets/HospitalRoomSuccessorView.qml").read_text()
service = (root / "services/hospital/HospitalDoctorSuccessionCapabilityService.qml").read_text()
policy = (root / "services/hospital/HospitalDoctorSuccessionCapabilityPolicy.js").read_text()
issues = []


def check(ok, name):
    if not ok:
        issues.append(name)


check('HospitalDoctorSuccessionCapabilityService {' in view
      and 'enabled: root.active' in view,
      "Probe must be lazy and scoped to open Room recovery")
check('pxSuccessionCapability.refresh();' in view
      and 'root.refreshRequested();' in view,
      "Existing refresh must re-probe local capability and Room evidence")
check('LOCAL PX COMMAND //' in view
      and 'pxSuccessionCapability.reason' in view,
      "Show exact source state in existing recovery view")
check('NO REPLACEMENT BUTTON YET' in view
      and 'PX authority and atomic revalidation remain mandatory' in view,
      "No mutation UI or false authority claims")
check('function evaluate(exitCode, stdoutText, stderrText)' in policy
      and '"--previous-provider-id"' in policy
      and '"--new-session-id"' in policy
      and '"--confirm"' in policy,
      "Require complete PX succession CLI help signature")
check('authorityVerified: false' in policy
      and 'replacementAuthorized: false' in policy,
      "Command detection is never operator authentication")
check('"agent", "session-succeed", "--help"' in service
      and 'capabilityProcess.exec([' in service,
      "Execute only the help capability probe")
check('onEnabledChanged:' in service
      and 'if (!root.enabled)' in service
      and 'pendingRefresh' in service,
      "Discard inactive/stale capability responses")
check('No Session' not in service,
      "No fake Session status is synthesized")
for forbidden in ('"session-succeed", "--confirm"', '"session-succeed", "--json"',
                  '"quick", "GO"', 'room-bind', 'session-attach-atomic',
                  'session-succeed-atomic', 'session-runtime',
                  'session-create', 'doctor-put'):
    check(forbidden not in service,
          "No mutation command in capability service: " + forbidden)

if issues:
    print("HOSPITAL SUCCESSION CAPABILITY UI // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)

print("HOSPITAL SUCCESSION CAPABILITY UI // PASS // lazy --help and honest authority boundary")
