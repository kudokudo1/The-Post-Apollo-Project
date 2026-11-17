# CLOCK // BG1-B2B7 Signed Role-Bound Release Preflight

**State:** Disposable real-kernel-process composition, DENY-ONLY.
**No installed Clock signing root, no Quickshell pause, no writer transfer,
no native background alarm action.**

## IMPLEMENTATION

B2B2 already knows how to inspect an independently signed Clock role policy,
the actual interpreter inode, exact entrypoint bytes/argv and the same
SO_PEERPIDFD-bound process. B2B5 already verifies a signed single-use response
over a Unix socket, binds it to the original synthetic alarm digest/epochs,
and consumes its challenge in a durable SQLite replay ledger.

Those were previously **independent observations**. This milestone creates
`AlarmRoleBoundReleasePreflight.py` to compose them:

1. Caller provides two independently verified and **disposable** Clock
   objects. The wrapper rejects arbitrary objects, production paths and
   absence of its explicit `synthetic_only=True` fixture guard.
2. Before proceeding, the two signed policies must agree on:
   `clock-ui-bridge` role, release epoch **and** sequence, expected
   interpreter, UID/GID, and the independently pinned PID and process
   start ticks. A signature valid for an unrelated role or process does
   not cross this boundary.
3. Before issuing a challenge, the B2B2 origin verifier rechecks the live
   process executable, entrypoint digest, argv and kernel peer. The B2B5
   receipt fixture issues its source-bound one-use challenge, then origin
   is verified again.
4. Before and after consuming the signed response, the complete signed
   origin measurement is repeated. The B2B5 source checksum and replay
   ledger must still match. A process exit, changed original source,
   modified program or replay refuses.
5. Return **only evidence** of an observed origin and reply. All results
   contain `roleAuthenticated=false`, `writerStopped=false`,
   `releaseAcknowledged=false`, `canTransferOwnership=false`,
   `ownsRealAlarmFile=false`, `canRing=false`, `canNotify=false`.

The test suite launches a disposable real Linux Python process that signs
a challenge under a test-only Ed25519 old-writer key. Distinct ephemeral
issuer roots sign the role policy and receipt enrollment policy. It proves
the *same process* satisfied both independent observations. The fixture
changes NO saved alarm data, and the external old process is never Quickshell.

## WHY STILL DENY

- Signed origin is **not an installed-role grant**: B2B2 deliberately
  returns `role_authenticated=False` even when its signature, executable
  hash and PID evidence match.
- B2B5's signed receipt is a reply from a live process. It does **not**
  prove the process stopped writing, flushed FileView, or ceded exclusive
  authority to a canonical successor.
- The B2B6 mounted QML barrier remains read-only `ACTIVE`. Both
  QML pause/release methods still return refusals. Existing Clock
  scheduling, audio and STOP/SNOOZE are unchanged.
- Identity C4b is a separate owner/dependency; never repurpose its keys
  or claim that its signed gateway is Clock authority.

This module has no CLI, service unit, RPM install, QML entry point, nor
background alarm runner. Successful observation is NOT authorization.

## VERIFY

Dedicated CI runs the new role+reply integration cases using real
SO_PEERPIDFD sockets and separate signed policies, then reruns the B2B2,
B2B5, B2B6 and B2B1 regressions. Exact four-file change guard prevents
unexpected edits to live Clock, Identity, Connections or BG2.

## NEXT IMPLEMENTATION

1. Obtain operator-approved independent **installed Clock native role**
   provisioning and an enforceable process/session supervisor; coordinate
   with the separate Silverblue/Identity worker and release-root owner.
2. Build the true Quickshell `QUIESCING` state transition: reject new
   alarms/ticks, complete every previously accepted FileView save/queue,
   retain local emergency silence, and obtain an independently witnessed
   durable final saved-source digest.
3. Require the protected supervisor to enforce old-writer revocation
   through exit/restart before accepting the signed release, then
   atomically migrate the canonical writer and demonstrate rollback.
4. Only after single-writer authority and delivery acknowledgement
   are real may BG2 background audio/notification actuation be enabled.

## HOSPITAL

PATIENT // The-Post-Apollo-Project
ROOM // Clock / Reliable Background Alarm Ownership
ROLE // External Hospital-compatible DOC, not live Hospital registered
ASSIGNMENT // BG1-B2B7 same-peer role+release trust-chain composition
SCOPE // New isolated Python module, tests, CI, docs only
PERMISSIONS // Source changes to draft PR only; no local host installation
RECOVERY // Branch PR and exact CI; no host/QML state changed
NEXT // Protected installed Clock authority + live writer quiescence
DECISIONS // Deny all real ownership/ringing; operator approval needed for merge
