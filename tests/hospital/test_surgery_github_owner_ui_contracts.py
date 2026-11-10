#!/usr/bin/env python3
"""GitHub account and repository names remain separate in Surgery Room creation."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
view = (root / "widgets/HospitalWorkforceManagerView.qml").read_text()
account = (root / "services/hospital/HospitalGitHubOwnerService.qml").read_text()
policy = (root / "services/hospital/HospitalGitHubOwnerPolicy.js").read_text()
room = (root / "services/hospital/HospitalWorkforceRoomCreateService.qml").read_text()
host = (root / "widgets/HospitalW.qml").read_text()
errors = []
def check(ok, desc):
    if not ok: errors.append(desc)

check('HospitalWorkforceManagerView {' in host
      and 'suggestedRepository: patientService.repository' in host
      and 'root.workforceManagerExpanded' in host,
      "Retain existing Surgery manager and live Patient suggestion")
check('id: roomOwnerField' in view
      and 'id: roomRepoField' in view
      and 'id:roomRepositoryField' not in view
      and 'GITHUB OWNER // ACCOUNT OR ORGANIZATION' in view
      and 'REPOSITORY // PROJECT NAME ON THAT GITHUB ACCOUNT' in view,
      "Owner and repository are separate, labeled inputs")
check('GITHUB OWNER = the account or organization hosting the repository' in view
      and 'NOT the worker, Doctor or person assigned the job' in view
      and 'OWNER = WHOSE GITHUB ACCOUNT // REPOSITORY = WHICH PROJECT' in view,
      "Explain GitHub ownership as distinct from Hospital worker ownership")
check('readonly property string selectedGitHubRepository:' in view
      and 'GitHubOwnerPolicy.compose(roomOwnerField.value, roomRepoField.value)' in view
      and 'repository: root.selectedGitHubRepository' in view,
      "Original PX Room creator receives only the composed owner/repo slug")
check('GitHubOwnerPolicy.suggestion(root.suggestedRepository,' in view
      and 'root.roomOwnerManuallyEdited' in view
      and 'root.roomRepositoryManuallyEdited' in view
      and 'onTextEdited: managerField.edited()' in view,
      "Autofill does not overwrite explicit user edits")
check('label: "USE MY GITHUB"' in view
      and 'label: "USE PATIENT"' in view
      and 'onTriggered: root.useOwnGitHub()' in view
      and 'onTriggered: root.useCurrentPatient()' in view,
      "Provide explicit account and current Patient autofill controls")
check('GitHubOwnerPolicy.ownerOptions(root.rooms,' in view
      and 'label: "RECENT GITHUB OWNER // " + modelData.owner' in view
      and 'OWNER KNOWN FROM ANOTHER ROOM, NOT AN AUTHENTICATED ACCOUNT' in view,
      "Recent owner suggestions use Hospital records but never claim login authority")
check('HospitalGitHubOwnerService {' in view
      and 'gh api user --jq .login' in account
      and 'gh api user/emails' not in account
      and '--method PATCH' not in account
      and 'gh auth login' not in account,
      "Reuse the existing gh account identity with a narrow read-only call")
check('onRefreshed:' in view
      and 'root.applyRoomSuggestions();' in view
      and 'if (!root.roomOwnerManuallyEdited && proposed.owner)' in view
      and 'if (!root.roomRepositoryManuallyEdited && proposed.repository)' in view,
      "Late Git account results cannot clobber manual owner/repo")
check('roomCreate.create(p)' in view
      and 'function confirm(kind)' in view
      and 'armedKey !== signature(kind)' in view
      and 'GITHUB.COM/' in view,
      "Original review and confirm gates remain, with visible full URL")
check('"hospital", "room-bind", id' in room
      and '"hospital", "room-name-set", root.pending.id' in room,
      "Existing PX Room persistence remains unchanged")
for phrase in ('CREATE SESSION','"agent", "turn"','"git", "push"',
               'room-bed-claim','session-attach','credential'):
    check(phrase not in account, "Account reader cannot launch or mutate: " + phrase)
check('function splitRepository' in policy
      and 'function suggestion' in policy
      and 'function ownerOptions' in policy
      and 'function compose' in policy,
      "Pure owner selection source supports current Patient and known owners")
if errors:
    print("HOSPITAL GITHUB ROOM OWNER // FAIL")
    for error in errors: print(" - " + error)
    raise SystemExit(1)
print("HOSPITAL GITHUB ROOM OWNER // PASS // explicit account owner, Patient selection and safe autofill")
