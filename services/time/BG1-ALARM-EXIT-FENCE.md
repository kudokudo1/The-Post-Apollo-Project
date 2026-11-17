# Clock BG1-B2B8 // Durable observed OLD-writer process exit

**Status:** fixture-only; real Linux `SO_PEERPIDFD` process-exit observation
following B2B7 signed origin+reply. No active alarm release or new writer.

## Mechanism

B2B7 checks a real test subprocess's signed program identity, OS peer,
one-use signed old-writer response and exact saved V2 source digest. B2B8
adds an **independent durable exit observation ledger**.

1. `prepare` requires the real B2B7 chain, a private disposable
   `synthetic-quickshell/time-alarms-v2.json`, a digest and increasing
   old/new owner epoch. The shared test process must still be the same
   independently pinned signed process. Its B2B7 challenge is issued.
2. The existing 0700 fixture directory contains a new owner-only 0600
   SQLite ledger with one row for this alarm-source scope. The prepared
   row records only epoch numbers, source SHA-256, pinned PID/start ticks
   and challenge digest. SQLite uses `BEGIN IMMEDIATE`, `synchronous=FULL`
   and rollback journal DELETE for atomic commits. No alarm names/notes.
3. `observe_signed_reply` invokes B2B7's full signed origin and one-use
   response checks again; it only transitions to `SIGNED_REPLY_OBSERVED`.
   A signed reply **is not** a process-exit claim.
4. `observe_process_exit` must see that the **same pinned kernel pidfd**
   is signaled, after the signed reply, with the exact original saved
   source SHA-256 still present. Only then the row advances to
   `PROCESS_EXIT_OBSERVED` durably.
5. After a fresh interpreter/fixture restart, `refuse_old_epoch` reads
   the persisted record and refuses the retired synthetic epoch or any
   older one. A newer epoch is only reported as a **candidate**, with
   `canTransferOwnership=false` and `canRing=false`.

The protected evidence chain now demonstrates a signed test old writer
**actually exited**, which B2B7 alone did not establish. All successful
outputs explicitly maintain:
`oldWriterRestartPrevented=false`,
`releaseAcknowledged=false`,
`canTransferOwnership=false`,
`ownsRealAlarmFile=false`,
`canRing=false`, `canNotify=false`.

## Security boundary

This ledger can fence only *cooperative test participants* that consult
this same fixture. It **cannot stop a new Quickshell process from writing**
to its V2 FileView, cannot make its future restart see the retired epoch,
and cannot prove the user-owned source file is unchanged by an unrelated
writer between a digest check and a transaction commit. The existing
QML writer remains the actual alarm owner in immutable `ACTIVE` state.
`FileView.blockWrites` must NOT be used as a lock; it is a synchronous
I/O setting, not an ownership gate.

The tests use ephemeral signer secrets and a disposable test subprocess;
they do not enroll an installed Clock role. C4b Silverblue/Identity
remains separately owned and is not a Clock root signer or authority.

## Verification and recovery

The dedicated CI covers real AF_UNIX signed old-writer responses followed
by kernel pidfd exit, an in-flight live-process refusal, missing signature,
tampered source, replay, wrong PID/start ticks, unsafe disk permissions,
concurrent prepare calls and restart retrieval of the retired epoch.
Existing B2B7, B2B5, B2B1 and mounted QML B2B6 tests run again.

No live QML, broker, Identity, Connections, installation, scheduler, sound
or notification source changes are made. The SQLite fixture is disposable.

## Next implementation

1. Coordinate **independent installed Clock process authority** and
   protected restart supervision; do not substitute a signed Identity
   gateway for the Clock role.
2. Wire authenticated `QUIESCING` into the *real* old writer. Block
   edits and ticks, finish pending/queued FileView saves and persist
   the final source revision, preserving local emergency STOP.
3. Make an installed/protected supervisor enforce old-writer restart
   refusal, not merely record test exit; then permit the durable
   one-canonical-writer takeover and independent BG2 alarm delivery.
4. Native Silverblue run: prove crash, logout, suspend, reboot and
   recovery without duplicate alarms. Operator approval before activation.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC, not registered live
ASSIGNMENT // BG1-B2B8 durable old-test-writer exit evidence
SCOPE // New isolated Python fixture, tests, CI and docs only
PERMISSIONS // GitHub draft PR; no host writes/merge or production change
RECOVERY // PR branch, exact-head CI, fixture only
DECISIONS // No real writer ownership or BG2 grants, operator review required
