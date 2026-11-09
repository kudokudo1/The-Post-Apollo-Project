#!/usr/bin/env python3
"""Surgery management is inline, arm/confirm gated, and Session-free."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
host = (ROOT / "widgets/HospitalW.qml").read_text()
view = (ROOT / "widgets/HospitalWorkforceManagerView.qml").read_text()
service = (ROOT / "services/hospital/HospitalWorkforceRoomCreateService.qml").read_text()
policy = (ROOT / "services/hospital/HospitalWorkforceManagerPolicy.js").read_text()
problems = []

def check(ok, label):
    if not ok:
        problems.append(label)

check('property bool workforceManagerExpanded: false' in host
      and 'id: managerToggleMouse' in host
      and '"MANAGE +"' in host
      and 'onClicked: {' in host,
      "MANAGE + expands within Surgery's current roster")
check('HospitalWorkforceManagerView {' in host
      and 'id: inlineWorkforceManager' in host
      and 'active: root.menuOpen && root.workforceRosterVisible' in host
      and 'rooms: responsibilityService.durableRooms' in host
      and 'sessions: responsibilityService.durableSessions' in host,
      "Manager must use existing durable PX records inside scrolling roster")
check('root.workforceManagerExpanded = false;' in host,
      "Surgery reset or SHOW BRANCHES must close the nested manager")
check('text: "EDIT NAME"' in host and 'function openRosterIdentityEditor' in host,
      "Existing rename editor remains independently accessible")
for label in ("ROOM", "CHAT", "QUICK", "LINKS"):
    block = host.split('label: "' + label + '"', 1)[1][:230]
    check('contentGlowEnabled: false' in block,
          "One aligned outer glow for " + label + " roster action")
check('softGlowEnabled: true' in (ROOT / "components/HospitalActionButton.qml").read_text(),
      "Existing single outer glow remains active")
for marker in ('mode: "WORKER"', 'mode === "ROOM"', 'mode === "JOB"',
               'id: workerNameField', 'id:roomNameField',
               'id:roomRepositoryField', 'id:jobGoalField',
               'id:jobPermissionsField', 'model: root.doctors.slice(',
               'model: root.rooms.slice(',
               'role: root.workerRole', 'source: "'):
    if marker == 'source: "':
        continue
    check(marker in view, "Missing inline management field/control: " + marker)
check('model: [' in view and 'code:"INT"' in view
      and 'code:"NRS"' in view and 'code:"DOC"' in view,
      "Intern, Nurse, Doctor selectable, not conflated with Provider")
check('function review(kind)' in view and 'function confirm(kind)' in view
      and 'armedKind !== kind' in view and 'armedKey !== signature(kind)' in view
      and 'disarm(); // one-shot' in view,
      "All mutations must require a fresh exact one-shot confirmation")
check('doctorService.saveDoctor(p.id, p.name, p.role, "ACTIVE")' in view
      and 'doctorService.releaseDoctor(chosen.id)' in view,
      "Create and release use the existing PX Doctor writer")
check('root.retirePlan.ready' in view
      and 'Worker still owns a Room' in policy
      and 'Worker still has a nonterminal Session' in policy,
      "Retirement cannot silently detach a Room or operating Session")
check('roomCreate.create(p)' in view
      and 'root.selectedRoomId' in view
      and 'inlineAssignment.createAssignment(' in view
      and '"PLANNING"' in view,
      "Create unstaffed Room and only draft Assignment from same Surgery surface")
check('room-bind' in service
      and 'room-name-set' in service
      and 'String(result.id || "") !== root.pending.id' in service,
      "Room creation must verify generated identity and report partial name save")
check('createsSession: false' in policy
      and 'launchesProvider: false' in policy
      and 'assignsDoctor: false' in policy
      and 'activatesAssignment: false' in policy,
      "No hidden provider execution or Assignment activation")
for bad in ('"agent", "turn"', '"agent", "quick"',
            '"session-create"', '"assignment-activate"',
            '"orchestrate-ready"', '"git", "push"'):
    check(bad not in view and bad not in service,
          "No execution or orchestration from workforce setup: " + bad)
check('value="READ"' in view
      and 'READ only is the default.' in view,
      "Draft Assignment must begin read-only and explain permission limits")

if problems:
    print("SURGERY INLINE WORKFORCE // FAIL")
    for issue in problems:
        print(" - " + issue)
    raise SystemExit(1)
print("SURGERY INLINE WORKFORCE // PASS // nested review, create-only intent, retained controls, single glow")
