# Clock BG1-B2B14 // Signed Current-Floor Native Admission

**STATE:** Implemented in source and disposable Linux CI, **deny-only**.
**LIVE CLOCK:** Quickshell remains the sole writer. Its mounted barrier is
hard-coded `ACTIVE`. There is no installed signing key, release-floor
custodian, native service, release permission or background alarm activation.

## IMPLEMENTATION

B2B13 introduced a root-only SQLite **highest-issued** version.
A normal unprivileged Clock supervisor cannot open its 0600 root-owned
database, and an old signed session could otherwise pass B2B12 if the
supervisor used a stale independent version floor. B2B14 gives the
controller a root-published, signed floor **observation** in the same
protected session directory the normal native supervisor can read.

- `clock-current-floor-v1.json` and `.sig` under the existing fixed
  `/run/post-apollo/clock/sessions-v1` directory. The JSON is canonical,
  domain-separated from session enrollment and installed role signatures,
  and signed with the already independently pinned Clock issuer.
- The signed floor contains the exact boot UUID, Clock-only role, version
  (`releaseEpoch`, `releaseSequence`), SHA-256 of the exact
  newly signed session JSON, and state `BLOCKED` or `CURRENT`.
- `AlarmCurrentFloorWitness.py` reads root-controlled files without
  following symlinks and validates the signature using B2B9's
  independently pinned installed Clock public root. It refuses missing,
  torn or forged pairs, unsafe file modes, wrong boot, stale version and
  `BLOCKED`. It does not open the root-only controller database.
- The B2B13 issuer acquires a controller-only `flock` **across the
  entire transaction and publication**, so two cooperating controllers
  cannot publish different sessions out of order. It checks the old
  signed floor against its durable SQLite row and refuses unreviewed
  legacy state, mismatched or missing floor records and non-increasing
  release versions.
- After verifying the real original SO_PEERPIDFD process and signed
  program, it publishes and fsyncs `BLOCKED` **before** committing
  a newer SQLite floor. It then commits the new floor under an immediate
  transaction, publishes and fsyncs `CURRENT` tied to the *new*
  session digest, then publishes/fsyncs the new signed session files.
- The normal native supervisor's installed-session inspection now
  verifies the same signed `CURRENT` state and exact session digest
  **before and after** B2B12's kernel-peer signed enrollment
  verification. This path is still default OFF because
  `APPROVED_CLOCK_RELEASE_ROOT_SHA256` and
  `APPROVED_CLOCK_RELEASE_FLOOR` remain `None`.

## CRASH / RESTART PROPERTY

The signed JSON and signature are separately atomic file publishes,
not one transactional pair. A crash after the first file replacement
creates a mismatched signature and refuses. After the `BLOCKED` pair,
a crash before or after SQLite commit leaves admissions blocked. After
`CURRENT` is published, the older session's digest no longer matches
the signed current floor, including if the new session pair is only
partially published. An old floor can't be accepted by a verifier
observing the protected higher-version role.

A crash during **`BLOCKED` publication** may leave an inconsistent
floor pair requiring an explicit trusted recovery operation. This is
intentional, not automatic acceptance. An existing B2B13 SQLite floor
without an accompanying signed snapshot requires an approved migration
or reset with preserved release evidence. Never infer a floor from a
user-supplied session or silently clear a lock.

A fully privileged attacker capable of rolling back the root-owned
Clock trust, signed floor AND release-version state is outside this
source-only model. Independent protected update and boot-chain custody
remain required before claiming production anti-rollback.

**Important:** The two snapshot reads on either side of identity
measurement do NOT form an atomic authorization lease. An update
could occur immediately afterward. Thus the supervisor still returns
only observation evidence and hard-denies all `REQUEST_PAUSE`,
`RELEASE_WRITER`, `TAKE_OWNERSHIP`, `RING_ALARM` actions.

## VERIFY

Disposable CI runs a real Linux Unix-socket old-writer process and
separate rootless ephemeral Ed25519 issuer. Cases cover:
- Current signed floor plus B2B12 reader and actual same kernel peer
- Prior signed session superseded by a higher signed version
- Signed `BLOCKED` state, missing/forged/torn floor or wrong signer
- Wrong boot, version, schema, extra fields and file permissions
- Crash before SQLite update, after SQL commit and before session
- Signed floor changed between two verifier observations
- Legacy ledger without floor refused (supervised migration required)
- Existing B2B13/B2B12/B2B11/B2B10/B2B9, B2B1 kernel and mounted
  B2B6 QML tests remain green.

This is CI-only source verification. Native root-owned Silverblue
issuer/supervisor privilege and crash testing remain separate and
require operator authorization. No live alarm, host or service changed.

## NEXT IMPLEMENTATION

1. Coordinate an operator-approved Clock-specific signer, independent
   root pin, root-owned session issuer service, safe runtime directory,
   protected release-floor custody, and supervised boot recovery.
   Purpose-separated Identity/Connections keys are NOT Clock authority.
2. Implement an **authenticated Quickshell `QUIESCING` handshake** that
   stops new edits while draining every accepted `FileView` save and
   queue, then persists final V2 source revision evidence.
3. Enforce old-writer revocation and restart denial through an actually
   protected Clock supervisor, then transfer to exactly one canonical
   writer with rollback/crash verification.
4. Enable/test BG2 audible alarm and notification delivery only after
   the native Silverblue acceptance and explicit operator approval.

## HOSPITAL

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
ROLE // External Hospital-compatible DOC; live registration unverified
ASSIGNMENT // BG1-B2B14 signed current-floor publisher and native observer
SCOPE // 11 Clock-owned files, including four inherited workflow guards
PERMISSION // Draft PR only; no merge, host mutation, key installation
RECOVERY // PR, exact-head CI; no host rollback because nothing deployed
DECISION // Deny all writer release, ownership takeover, ringing, notify
