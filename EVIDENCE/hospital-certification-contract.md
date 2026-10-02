# Hospital Certification Contract

## Purpose

Hospital owns the meaning of surgical readiness.

Git and GitHub provide repository and automation evidence.
PX performs the requested operation.
Hospital evaluates that evidence and advances or blocks the room.

## Certification lifecycle

PREPARE
→ CANDIDATE
→ VERIFIED
→ CERTIFIED
→ ARMED
→ INTEGRATING
→ POST_OP
→ IN_MAIN

A room can also enter:

- BLOCKED — evidence failed, drift was detected, or a required condition was not met.
- REOPENED — a previously blocked/reviewed room is deliberately returned to the certification process.

## State meanings

### CANDIDATE

A valid PREPARE snapshot has been accepted.

The packet freezes:

- repository
- team/room
- branch
- room HEAD
- target base
- target base HEAD
- integration mode
- diff totals
- changed files
- rehearsal evidence when present

### VERIFIED

The candidate was checked without SHA drift.

Verification requires:

- current room HEAD equals candidate HEAD
- current base HEAD equals candidate base HEAD
- supplied checks report a passing/clean result

GitHub workflow/run evidence can be attached through the provider contract without Hospital implementing another workflow reader.

### CERTIFIED

The verified evidence has been accepted as sufficient for integration.

The certified HEAD is frozen.

### ARMED

Certification has been frozen and the room is explicitly cleared for the integration operation.

### INTEGRATING

PX has accepted the armed snapshot and the integration operation has started.

### POST_OP

Integration completed and the room is waiting for post-operative verification.

### IN_MAIN

Post-op verification is clean and the room is contained as expected.

## Evidence packet

The service stores a versioned packet containing:

- recorded timestamp
- room identity
- repository/branch
- candidate, verified, certified, armed and post-op SHAs
- base and base SHA
- relation and integration mode
- diff totals
- changed files
- rehearsal result
- checks
- workflow/run evidence
- post-op result
- transition reason
- transition-specific details

The packet is persisted in Quickshell's per-shell data area rather than written into the patient repository. This keeps certification history from dirtying the development worktree.

## Provider boundary

Doc 3 owns the Git/GitHub evidence provider.

Hospital consumes evidence through plain data:

- checks
- runs
- jobs/steps/logs
- conclusions
- repository/branch/commit facts

Hospital does not create a second GitHub Actions reader.

## Drift rule

A certification is tied to the exact SHA that was inspected.

If the room HEAD or target base HEAD changes before verification/certification/arming, Hospital blocks the transition and requires the room to be reopened/reprepared.

## Initial implementation

services/hospital/HospitalCertificationService.qml implements the state machine and persistent event history.

services/hospital/HospitalCertificationCoordinator.qml is the backend bridge from the existing HospitalRoomService snapshots into the certification service. It keeps the UI from having to know the certification internals.

services/hospital/HospitalHistoryService.qml provides the persistent Hospital-wide event timeline.

services/hospital/HospitalOperatingAuthorityService.qml provides the serialized host-slot owner/queue contract.

The UI integration is intentionally separate so the service contract can stabilize before another lane edits HospitalW.qml.
## Restart and authority recovery

The operating slot is persistent. A coordinator may recover an existing lease only when the persisted owner team, branch, and HEAD match the selected room snapshot. Team identity alone is not sufficient.

A same-team request that attempts to change the branch or HEAD of an already-held slot is treated as an ownership collision and is refused rather than silently rewriting the authority snapshot.

## Evidence contract identity

Certification accepts the Git/GitHub verification packet only when it identifies itself as schema version 1 from provider `post-apollo.git-evidence`.

Hospital also rejects evidence when the provider reports that the exact-SHA query or inspected run targeted a different SHA than the candidate.



## Verification commit point

Verification uses two remote snapshot checks.

1. Hospital checks the candidate room HEAD and base HEAD before requesting Git/GitHub evidence.
2. GitEvidenceProvider gathers exact-SHA evidence.
3. Hospital checks the same remote room HEAD and base HEAD again immediately before committing the VERIFIED transition.

This closes the evidence-request race: a branch that moves while GitHub evidence is being collected cannot become VERIFIED against stale remote state.

The coordinator's legacy direct `verify(checks, runs)` injection path is disabled. Production verification must enter through the Git evidence provider contract.

## Evidence retention

Verification checks and workflow/run evidence are retained as certification-owned state after VERIFIED.

Later transitions such as CERTIFIED, ARMED, INTEGRATING, POST_OP, and IN_MAIN must carry forward the evidence that justified verification rather than rebuilding a packet that silently drops it.

PX PREPARE exposes both:

- `files` — the existing short operator preview
- `changed_files` — the complete changed-file evidence list

Hospital freezes the complete list into the certification snapshot when the extended PX contract is available.

## Exact host-slot identity

A HOST lease requires a non-empty team, branch, and exact HEAD.

Same-team ownership is not sufficient to recover or reuse a lease. Recovery requires the persisted lease id, branch, and HEAD to all be present and to match the selected room exactly.

If Hospital restarts after HOST acquisition but before the ARMED transition, a matching recovered lease still passes through `armCertified()`; recovering authority does not skip the certification state transition.
