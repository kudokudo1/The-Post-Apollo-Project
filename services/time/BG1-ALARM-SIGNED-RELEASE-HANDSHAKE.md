# CLOCK // BG1-B2B5 Signed Old-Writer Release Handshake Fixture

**State:** real Linux AF_UNIX process and signed one-use receipt prototype.
DISPOSABLE TEST ONLY. No live Quickshell bridge, no writer pause, no production
Clock signing authority and no audio or notification activation.

## Concrete mechanism

A fixture-specific old-writer process connects over AF_UNIX. The verifier
uses the merged BG1-B2B1 kernel SO_PEERPIDFD witness to bind the accepted
socket to the same still-running Linux process, UID/GID, executable and
start ticks. The expected PID and ticks must be independently pinned by a
trusted supervisor; this prototype's CI pins those from a disposable child.

A separately pinned Ed25519 release-root public key authenticates a
Clock-only canonical policy with strict purpose and exact field set:
- old role clock-ui-bridge, original V2 source scope
- minimum release epoch/sequence floor
- expected interpreter and UID/GID
- SHA-256 identity of the approved *separate old-writer signing public key*

The public signer comes from the independent enrollment, NOT from the socket.
Never use Identity Center's signing root or C3e synthetic keys as a Clock
grant. The test uses throwaway keys generated in CI, not installed keys.

The verifier validates the original disposable V2 JSON through the existing
B0 observer validation, checks the exact SHA-256 of its bytes via O_NOFOLLOW,
and issues a 256-bit random challenge bound to its digest, old/new owner
epochs and pinned peer identity.

The challenge hash is stored in a 0600 SQLite replay ledger under an existing
0700 synthetic fixture directory, using BEGIN IMMEDIATE and synchronous FULL.
The challenge expires after 5 seconds. Its raw secret is never persisted.
A real test client signs a canonical release *response* with its Ed25519
private key. The verifier compares that signature with the independently
pinned signer, rechecks the same kernel process, exact issued challenge,
owner epochs and source digest, and consumes the challenge transactionally.
A repeated response or stale, forged, expired, wrong-scope or wrong-process
response is rejected.

The result is only:
- signatureObserved = true
- independentlyPinnedSignerMatched = true
- peerProcessMatched = true
- writerStopped = false
- releaseAcknowledged = false
- canTransferOwnership = false
- ownsRealAlarmFile = false
- canRing = false
- canNotify = false

## Why this is not the live handoff

**Signing a sentence saying "I released the file" does not stop a process
from writing.** The current AlarmManagerService.qml still uses FileView,
whose onSaved callback can queue more saves, and its schedule timer and
STOP/SNOOZE paths still run.

The independent authority and installed release evidence are not yet
provisioned. The signed-origin observer in PR #1959 remains review-only and
also grants no ownership. PR #1965 rehearses a candidate writer but has
no actual Quickshell quiescence. PR #1968 only reports local drain and always
refuses release.

Thus this fixture cannot produce a production release or enable BG2. The
source JSON is **never** written by the verifier. No real key storage, RPM
install, Quickshell service, bridge socket, QML API or BG2 process is changed.

## Testing and limitations

Dedicated CI spawns a real disposable Python process and exercises signature
verification, wrong signer/release root, role/purpose mismatch, false epoch,
source mutation, kernel peer exit, expiry, replay after verifier restart,
transaction contention and mode/path refusal. It reruns existing BG1
kernel-peer, synthetic broker, atomic shadow and durable owner-claim tests.

The fixture's Ed25519 key is deliberately copied through a test-only pipe,
which is not acceptable production key custody. Executable entrypoint bytes
and the approved service's installed role are not independently observed in
this milestone; BG1-B2B2 and a native host protector must supply that
additional evidence. The SQLite record proves one-time observation, NOT
old-writer quiescence. A digest check cannot make a foreign FileView write
participate in its transaction.

## Next implementation

1. Obtain operator-approved, independently provisioned Clock-specific
   release root + installed Quickshell bridge and background worker identity.
2. Build and native-test an internal Quickshell write barrier that refuses new
   writes and drains pending and queued FileView saves, stops timer updates,
   preserves local emergency STOP/audio silence, and survives restart.
3. Only after the old writer is *actually* fenced, bind the durable signed
   response to the witnessed source revision and acknowledge release.
4. Promote a single durable writer through protected migration/rollback,
   then separately authorize/verify BG2 audible delivery.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock / Background Alarm Ownership
ROLE // External Hospital-compatible DOC, not live registered
ASSIGNMENT // BG1-B2B5 signed one-use old-writer protocol evidence
PERMISSIONS // GitHub source/docs/tests/CI only, no merge/activation
RECOVERY // Private test replay ledger; inspect PR, commit, exact CI
DECISIONS // Only observation, no real writer release or ring grant
NEXT // Native old-writer default-deny barrier and protected installed authority
