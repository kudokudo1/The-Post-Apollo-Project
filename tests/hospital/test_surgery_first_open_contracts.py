#!/usr/bin/env python3
"""Surgery first-open usability regression contracts.

Source checks do not claim native Quickshell rendering success.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")
audit = (root / "services/hospital/HospitalAuditService.qml").read_text(
    encoding="utf-8"
)
policy = (root / "services/hospital/HospitalSurgeryStartupPolicy.js").read_text(
    encoding="utf-8"
)

problems = []


def require(condition, problem):
    if not condition:
        problems.append(problem)


require("property bool workforceRosterVisible: true" in host,
        "Surgery must open with the registered WORKERS roster")
require('root.workforceRosterVisible = true;' in host,
        "Reopening Hospital must restore the operator-focused worker view")
require('root.operationsSurface === "" && root.workforceRosterVisible' in host
        and "responsibilityService.refreshDurableGraph();" in host
        and "doctorService.refresh();" in host,
        "Entering Surgery must refresh PX workforce without waiting for Git audit")
require('"SHOW WORKERS"' in host and '"SHOW BRANCHES"' in host,
        "Existing toggle between registered workers and Git branches is preserved")
require('root.workforceRosterVisible ? [] : auditService.rooms' in host,
        "Git branch list must still read PX audit room records")
require("NO REGISTERED PX ROOMS // SHOW BRANCHES" in host,
        "Empty PX registry must be honestly explained")
require("GIT ROOM LIST NOT LOADED // PRESS AUDIT OR SHOW WORKERS" in host,
        "Missing Git audit must produce an actionable visible state")
require("ROOM AUDIT FAILED // " in host and "READING GIT OPERATING ROOMS" in host,
        "Failure and in-progress audit must be distinguished")
require("auditService.lastError" in host,
        "Audits must expose failures instead of leaving the list silent")
require("!root.workforceRosterVisible" in host
        and "root.ensureFirstRoomSelected()" in host
        and "function ensureFirstRoomSelected()" in host,
        "Git Room autoselection must be gated from WORKERS")
require("if (root.workforceRosterVisible || !menuOpen" in host,
        "Worker-first opening must not start a second automatic branch Room audit")

# The original race happened because requestOpenAudit() was called before
# floorService.discover(), which could clear the just-started scan.
start = host.index("onMenuOpenChanged: {")
end = host.index("onKeyboardActiveChanged: {", start)
open_handler = host[start:end]
require(open_handler.index("floorService.discover();")
        < open_handler.index("root.requestOpenAudit();"),
        "Floor discovery must be marked in flight before audit scheduling")
require("SurgeryStartupPolicy.canReuseFloor(" in open_handler,
        "Rapid opens reuse a recent Floor instead of rescanning Git worktrees")
require("root.floorDiscoveryReuseInterval" in open_handler
        and "root.lastFloorDiscoveryAt" in open_handler,
        "Floor reuse must be bounded by explicit in-session timestamps")
require("root.lastFloorDiscoveryAt = Date.now();" in host,
        "Successful Floor discovery records its cache timestamp")
require("onClicked: floorService.discover()" in host,
        "Operator LOCAL REFRESH must remain a direct unthrottled action")
require("onFloorsChanged: {" in host
        and "openAuditKick.restart();" in host,
        "Finishing discovery must wake queued audit")

start = host.index("function maybeRunOpenAudit() {")
end = host.index("onOperationsSurfaceChanged: {", start)
audit_fn = host[start:end]
require("SurgeryStartupPolicy.canReuseAudit(" in audit_fn
        and "auditService.available" in audit_fn
        and "auditService.lastError" in audit_fn
        and "auditService.snapshotFloorKey === key" in audit_fn
        and "auditService.snapshotRepository === repo" in audit_fn,
        "Timestamp may suppress retry only with a matching successful Floor audit")
require("auditService.runAudit(false);" in audit_fn,
        "Existing first-open audit execution remains available")
require("auditService.runAudit(false);" in host
        and "auditService.runAudit(true);" in host,
        "Manual and quiet audit paths must remain intact")
require("if (root.openAuditPending && root.menuOpen" in host
        and "openAuditKick.restart();" in host,
        "Pending audit must be retried when existing audit slot releases")
require("FLOOR INPUT // PREVIEW" in host
        and "FLOOR INPUT // STANDARD" in host,
        "Floor switch must be labeled as pointer input, not data loading")
require("LIVE FLOOR // OFF" not in host
        and "LIVE FLOOR // ON" not in host,
        "Misleading LIVE FLOOR data-gate label must be retired")
require('indexInteraction: root.floorIndexPilotEnabled' in host
        and 'root.floorIndexPilotEnabled = false;' in host,
        "Floor slider pilot semantics and read-only default preserved")
require("property int openAuditStaleInterval: 600000" in host,
        "Successful audit freshness interval preserved")
require("function canReuseAudit(" in policy
        and "function canReuseFloor(" in policy,
        "Reusable cache logic covered by pure fixtures")
require("property var rooms: []" in audit
        and "function resetResult()" in audit,
        "Original audit owns Git Rooms and reset boundaries")
require("floorKey: floorService.floorId" in host
        and "property string inFlightRepository:" in audit
        and "property string inFlightFloorKey:" in audit,
        "Audit records the target Floor and repository at process launch")
require("inFlightRepository !== String(repository ||" in audit
        and "inFlightFloorKey !== String(floorKey ||" in audit
        and "AUDIT RESULT DISCARDED // FLOOR CHANGED" in audit,
        "Late scan for another Floor must be discarded rather than published")
require("snapshotRepository = inFlightRepository;" in audit
        and "snapshotFloorKey = inFlightFloorKey;" in audit,
        "Successful audit snapshot records the identity it actually scanned")
require("snapshotRepository = \"\";" in audit
        and "snapshotFloorKey = \"\";" in audit,
        "Changing Floor invalidates snapshot provenance")


if problems:
    print("HOSPITAL SURGERY FIRST-OPEN CONTRACT // FAIL")
    for problem in problems:
        print(" - " + problem)
    raise SystemExit(1)
print("HOSPITAL SURGERY FIRST-OPEN CONTRACT // PASS // worker-first, nonblank states, valid snapshots, queued audits")
