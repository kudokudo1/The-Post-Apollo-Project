# Clock BG1-B2B13 // Durable Protected Release Floor + Session Issuer

**STATE:** Source-only controller contract and disposable real-process CI.
**ACTUATION:** Disabled. No production Clock signing key, enrollment
controller, root-owned state directory, systemd service or QML pause
is installed by this change. An issued test enrollment is not a
permission to control, stop, replace or ring alarms.

## IMPLEMENTATION // What happens to actual bytes

B2B12 already reads a Clock controller-signed per-session JSON document
and its Ed25519 signature from protected paths and checks the
accepted Linux socket's original kernel pidfd against the signer,
program, release and process identity. But it does not create a
signed session or persist a monotonic release version.

`AlarmClockReleaseFloorController.py` implements the **producer
contract**, scoped to one trusted controller process, NOT a network
issuer endpoint. It has no CLI, private-key loader, key generator,
systemd unit or self-enrollment socket command.

**Production fixed paths (proposed, not installed):**

- Controller-only durable state:
  `/var/lib/post-apollo/clock/controller-v1/clock-release-floor-v1.sqlite3`
  (root-owned directory 0700, database 0600).
- Session records consumable by the B2B12 native reader:
  `/run/post-apollo/clock/sessions-v1/clock-ui-bridge-session-v1.json`
  and `clock-ui-bridge-session-v1.sig`, root-owned 0644 in a
  root-controlled directory.
- Installed B2B9 signed program role and independently pinned
  public Clock root:
  `/usr/share/post-apollo/clock/trust-v1/`.

**The controller enforces:**

1. Production invocation requires root UID/EUID, fixed protected
   directories and safe root-owned ancestors. Disposable CI mode
   uses explicit `bg1-clock-controller-fixture` and
   `bg1-protected-session-fixture` directories under a private
   0700 temp root. These cannot be substituted for production paths.
2. A pre-provisioned **external** Ed25519 signing key is supplied
   by the independently privileged controller. Its public key
   must exactly match the already installed B2B9 Clock release-root
   and independently pinned SHA-256 fingerprint. Neither an arbitrary
   peer nor the session document may nominate its own trust anchor.
3. A real AF_UNIX accepted socket is measured through B2B9's
   signed installed program, interpreter, argv, UID/GID, original
   SO_PEERPIDFD and kernel start ticks. The signed role release
   epoch/sequence is the requested session version. The caller cannot
   declare an arbitrary PID, release or file path for issuance.
4. A single SQLite row retains the highest issued
   `releaseEpoch` and `releaseSequence`, boot UUID, original PID
   and start ticks, installed signer digest and signed-session
   SHA-256. `BEGIN IMMEDIATE`, rollback journal DELETE and
   `synchronous=FULL` atomically refuse duplicate or older release
   versions across process/fixture restarts and competing issuers.
   An already enrolled old process also cannot request another
   enrollment at a higher release version.
5. The kernel peer is reverified immediately before transaction
   commit. **Only after the floor commits**, the controller
   atomically publishes each bounded manifest/signature file and
   syncs the containing directory. The two files are a pair, not
   one filesystem atomic operation. Readers must refuse a mixed
   pair (B2B12 verifies signature and exact source bytes).
6. A crash after floor commit but before both files publish does
   not silently roll the floor back or reissue the same version.
   A new independently signed *higher* release is required to
   recover. The controller does not issue a writer lease, release
   acknowledgment, authenticated QML pause, audio or notification.

Output flags always remain
`roleAuthenticated=false`,
`writerStopped=false`,
`releaseAcknowledged=false`,
`oldWriterRestartPrevented=false`,
`ownsRealAlarmFile=false`,
`canTransferOwnership=false`,
`canRing=false` and `canNotify=false`.

## WATCH OUT FOR // What is NOT provided

- Neither the root-only controller nor its signing key is installed,
  and its process is not started or supervised. A future **approved**
  Clock-specific protected issuer must hold the key and invoke this
  contract. Do not replace it with Identity/Connections signing keys.
- The B2B12 user's native supervisor still has
  `APPROVED_CLOCK_RELEASE_ROOT_SHA256 = None` and
  `APPROVED_CLOCK_RELEASE_FLOOR = None`. It continues to refuse
  all production enrolled sessions; this PR does not edit it.
- The controller-side SQLite highest-issued floor is not yet
  consumed by the read-only installed supervisor. Binding a
  root-owned **reader view of this floor** and ensuring safe
  monotonic recovery across reboot is the next separate integration.
  Without it, a copied previously signed manifest may still pass
  a verifier whose independently supplied floor was stale.
- A sufficiently privileged root attacker can roll back local
  root-owned files. Production needs independent release-root
  custody, system boot chain and protected update policy; this
  source-only model does not claim hardware-backed anti-rollback.
- B2B13 does **not** prevent new Quickshell processes from opening
  the real V2 alarm file. The mounted QML barrier remains ACTIVE.

## VERIFY

Disposable CI launches a real Linux AF_UNIX process and uses a
separately generated test-only Clock Ed25519 issuer. It checks:
B2B12 reader compatibility with the issued signed session, exact
kernel process, one-use monotonic floor, concurrent attempts,
independent signer fingerprint, different-process higher version,
signed policy rollback, changed entrypoint, dead process, 0600
SQLite, symlink and unsafe mode refusal, and post-commit publication
failure that blocks same-version reissue. It reruns B2B9/B2B10/
B2B11/B2B12, B2B1 and B2B6 regressions.

All tests write only ephemeral temporary CI files. No local host,
real Quickshell, installed keys, systemd, audio or alarms changed.

## NEXT // Actual implementation

1. Build a protected root-owned **read-only release-floor view** for
   the normal native Clock supervisor; require its current floor
   before accepting an installed session, with a race/restart-safe
   process lifecycle.
2. Coordinate the separately owned C4b/Silverblue installation for
   **Clock-specific** signing key custody, privilege separation and
   approved controller service, without borrowing Identity trust.
3. Integrate authenticated `QUIESCING` into the actual mounted
   Quickshell writer. Finish accepted FileView saves/queue and
   persist a final revision, preserving emergency local STOP.
4. Enforce old-writer exit/restart denial and one canonical writer,
   then independently validate BG2 audible alarm delivery and
   recovery on Silverblue.

## HOSPITAL CHECKPOINT

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC, no verified live Hospital session
ASSIGNMENT // BG1-B2B13 source-level protected controller release-floor + session issuance
SCOPE // 4 new Clock-owned files; no changes to other Rooms
PERMISSIONS // Draft GitHub source and CI only; no merge or host activation
RECOVERY // PR exact-head logs, 4-file scope guard, no host rollback
DECISIONS // No production key or authority granted, all actuation denied
