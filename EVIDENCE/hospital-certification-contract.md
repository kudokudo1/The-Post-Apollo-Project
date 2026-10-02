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
