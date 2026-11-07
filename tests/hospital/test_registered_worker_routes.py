#!/usr/bin/env python3
"""Hospital WORKERS card => registered Room transcript / pinned PX Quick.

A focused source contract; it does not interact with any real Hospital Session.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
host = (root / "widgets/HospitalW.qml").read_text(encoding="utf-8")
view = (root / "widgets/HospitalRegisteredWorkerView.qml").read_text(encoding="utf-8")
reader = (root / "services/hospital/HospitalWorkerTranscriptService.qml").read_text(
    encoding="utf-8"
)
policy = (root / "services/hospital/HospitalWorkerSessionPolicy.js").read_text(
    encoding="utf-8"
)
errors = []


def check(condition, message):
    if not condition:
        errors.append(message)


check("HospitalRegisteredWorkerView {" in host, "exact Room inspector mounted in Surgery")
check('root.operationsSurface === "registeredWorker"' in host, "distinct view route")
check('root.openRosterSession(rosterRow.rosterData, "chat")' in host,
      "card CHAT opens registered Room directly")
check('root.openRosterSession(rosterRow.rosterData, "quick")' in host,
      "card QUICK opens registered Room directly")
check('root.rosterFocusedRoomId = id' in host, "durable Room ID pinned")
check('root.rosterFocusedSessionId = String(current.sessionId || "")' in host,
      "Session ID pinned from the same registered Room")
check('String((rows[i] || {}).roomId || "") === id' in host,
      "navigation finds exact registered Room")
check('visible: root.operationsSurface === "chat"' in host,
      "legacy interactive Room CHAT preserved")
check('function openRoomQuick()' in host, "legacy QUICK preserved")
check('root.rosterCurrentRoomIndex' in host, "legacy Git selection preserved")
check('text: "REC // " + rosterRow.sessionState' in host,
      "registered status explicitly shown as recorded, not live heartbeat")

check("HospitalWorkerTranscriptService {" in view, "read-only transcript component")
check('roomId: root.active ? root.pinnedRoomId : ""' in view,
      "transcript keyed by persistent Room ID")
check('"hospital", "messages", wanted' in reader, "PX Room messages read only")
for forbidden in ("room-bind", "room-put", "session-create",
                  "agent turn", "agent quick", "message-append"):
    check(forbidden not in reader, "transcript does not mutate: " + forbidden)
check('readProcess.exec([' in reader, "messages loaded by isolated Process")
check('requested === String(root.roomId || "").trim()' in reader,
      "stale Room response must not be rendered on another Room")
check('lastError = ""' in reader, "reader tracks errors")
check("root.runtimeStatusVerified" in view, "fresh PX runtime status required")
check("SessionPolicy.sessionMatches(" in view, "Session matched by exact Room")
check("SessionPolicy.statusMatches(" in view, "runtime payload must match Session")
check("SessionPolicy.canIssueQuick(" in view, "command follows pure safety policy")
check("runtime.quick(command)" in view, "intentional explicit Quick dispatch")
check("runtime.refresh()" in view, "exact Session runtime refreshed")
check("No command is sent by opening this panel." in view,
      "no automatic GO/CONTINUE when opening view")
check("CHAT is read-only" in view, "operator told this is a read-only transcript")
check("Not a ChatGPT browser tab" in view, "browser session not falsely connected")
check('"GO", "CONTINUE", "STATUS", "REPORT",' in policy,
      "narrow command allowlist")
check('state.runtimeSessionMatches' in policy, "status payload identity gate")
check('state.runtimeStatusVerified' in policy, "verified status gate")
check('state.hasError || state.busy' in policy, "errors and concurrent work gate")

if errors:
    print("HOSPITAL REGISTERED WORKER ROUTES // FAIL")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)
print("HOSPITAL REGISTERED WORKER ROUTES // PASS")
