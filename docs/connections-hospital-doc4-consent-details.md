# 🏥💜 DOC 4 // Hospital C5 exact operator review context

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5 protected Room consent  
**STAFF ROLE:** DOC 4 · external Hospital-compatible  
**SOURCE:** additive DOC 4 draft; merged native issuer #2056 remains the source baseline  
**PX DEPENDENCY:** PX #130 and #133 remain separately owned, draft, and uninstalled  
**STATE:** SOURCE-ONLY · PRODUCTION HOLD

## IMPLEMENTATION

The existing native issuer asks Polkit for interactive authorization after
validating the requesting executable, local login1 seat and protected PX
PREPARE review. The previous request included a single formatted
`polkit.message` and three structured details (Room, action, graph).

This milestone adds individually named source-derived detail fields for
Patient, repository, Room revision, active seat and preservation/retention
decision. A reviewed agent could use those fields to present the **exact**
operation and distinguish it from a generic password prompt.

| Polkit detail | Source |
| --- | --- |
| `hospital-room-id` | PX protected PREPARE, checked against native request |
| `hospital-action` | Validated TRASH or RESTORE |
| `hospital-graph` | PX authoritative expected graph digest |
| `hospital-patient-id` | PX authoritative Patient |
| `hospital-repository` | PX authoritative repository |
| `hospital-revision` | PX authoritative revision |
| `hospital-seat-id` | Actual login1 requester session/seat |
| `hospital-retention` | Already validated protected PREPARE retention and no-Burn invariant |

These are **request context**, not a proof that the operator saw them.
The Polkit agent is not under this patch's authority. A successful
`pkcheck` status may be caused by an effective local rule without an
actual visible challenge. Dynamic `--detail` values are not guaranteed
to be rendered by the agent. No trusted user-visible receipt or
cryptographically authenticated human-presence proof is emitted.

## VERIFY

A new isolated five-test source suite verifies separate TRASH/RESTORE
Polkit action IDs, exact structured fields and message, process identity,
nonzero-result and timeout denial, and absence of a synthetic human
approval flag. Host interactions are mocked; no native issuer, PX,
signing key, Room state, database or Polkit agent is used.

## RELEASE GATES

- Operator and responsible host/security owners must approve an actual
  trusted Polkit agent/consent flow that visibly renders the exact protected
  Room/Patient/action/revision/graph/retention, and prevent permissive or
  cached authorization in effective deployed rules.
- Independent verification must cover lock/seat transitions and
  requester/agent substitution during the interactive step.
- Root-managed key custody, trusted signed releases, installed PX
  writer + native receipt, retention policy, backup, migration, fencing,
  and independent Nurse 2 security review remain prerequisites.
- This PR never claims `permissionReady` as consent, changes QML, grants
  permission, provisions a key, installs policy, alters PX or activates Burn.

## NEXT

Reconcile the approved native display/agent evidence contract with
Hospital PX owner and DOC 1 host-trust work; independently test the
installed agent before requesting operator production acceptance.
