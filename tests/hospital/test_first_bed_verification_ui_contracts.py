#!/usr/bin/env python3
"""No write actions: reuse existing Floor discovery and verify one Git Bed in Surgery."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
manager = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
host = (root / "widgets/HospitalW.qml").read_text()
policy = (root / "services/hospital/HospitalFirstBedVerificationPolicy.js").read_text()
probe = (root / "services/hospital/HospitalFirstBedProbeService.qml").read_text()
issues = []

def check(ok, message):
    if not ok:
        issues.append(message)

check('HospitalWorkforceManagerView {' in host
      and 'knownBeds: floorService.allBeds' in host
      and 'bedsDiscovering: floorService.discovering' in host
      and 'bedDiscoveryError: floorService.lastError' in host,
      "Reuse existing Floor Git inventory, never a second crawler")
check('onDiscoverBedsRequested:' in host
      and 'floorService.discover();' in host
      and 'if (!floorService.discovering)' in host,
      "FIND BEDS explicitly repeats only the read-only Floor discovery")
check('HospitalFirstBedProbeService {' in manager
      and 'id: bedProbe' in manager
      and 'onSelectedRoomIdChanged:' in manager
      and 'bedProbe.invalidate();' in manager,
      "Invalidate candidate Git evidence when selecting another Room")
check('readonly property var bedChoices: BedPolicy.candidateRows({' in manager
      and 'readonly property var bedPlan: BedPolicy.assess({' in manager
      and 'rooms: root.rooms' in manager
      and 'sessions: root.sessions' in manager,
      "Candidate must be checked against Room, Bed, Session and Patient ownership")
check('GIT BED // VERIFY EXISTING WORKTREE BEFORE STAFFING' in manager
      and 'label: "VERIFY BED"' in manager
      and 'label: "FIND BEDS"' in manager
      and 'root.bedPlan.blockers.slice(' in manager,
      "On-demand verification stays inside STAFFING and shows blockers")
check('GIT VERIFIED //' in manager
      and 'PX BED REGISTRATION STILL REQUIRES AUTHENTICATED APPROVAL.' in manager,
      "Do not imply Git metadata verification authorizes PX Bed registration")
check('verifiedForReview: blockers.length === 0' in policy
      and 'registrationAuthorized: false' in policy
      and 'authorityVerified: false' in policy,
      "Git evidence grants no operator authority")
check('room.bedPath' in policy and 'room.branch' in policy
      and 'Room has Session history' in policy
      and 'Room is already staffed' in policy
      and 'Select an unclaimed, non-live, clean Bed' in policy,
      "Refuse occupied Rooms, registered Beds, and historical Sessions")
check('probeProcess.exec(["python3", "-c", inspect, selected]);' in probe
      and 'GIT_OPTIONAL_LOCKS' in probe
      and 'git(\'remote\',\'get-url\',\'origin\')' in probe
      and 'git(\'status\',\'--porcelain=v1\'' in probe,
      "Path passed as argv and fresh Git origin, state and branch read")
check('probeProcess.startedGeneration === root.generation' in probe
      and 'probeProcess.stdoutDone' in probe
      and 'probeProcess.exitSeen' in probe,
      "Discard stale or incomplete Git subprocess responses")
for forbidden in ('"room-bind"', '"room-put"', '"session-create"',
                  '"agent", "turn"', '"git", "switch"',
                  '"git", "checkout"', '"git", "clean"',
                  '"git", "commit"', '"git", "push"'):
    check(forbidden not in probe and forbidden not in policy,
          "Read-only Git verification cannot mutate anything: " + forbidden)
if issues:
    print("SURGERY FIRST GIT BED // FAIL")
    for issue in issues:
        print(" - " + issue)
    raise SystemExit(1)
print("SURGERY FIRST GIT BED // PASS // reused Floor, on-demand Git evidence and no PX registration")
