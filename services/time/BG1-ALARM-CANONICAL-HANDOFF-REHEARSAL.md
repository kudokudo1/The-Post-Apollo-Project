# CLOCK // BG1-B2B3 Two-Phase Canonical Writer Handoff Rehearsal

**State:** disposable synthetic fixture, no live AlarmManagerService bridge,
no installed role, no production authority, no sound or notification.

## Why this milestone exists

The merged BG1-B2A shadow already updates an alarm state and an occurrence
receipt together. The live Quickshell V2 AlarmManagerService, however, still
atomically replaces time-alarms-v2.json without consulting the BG1 broker.
Giving both Quickshell and a background process access to that file would
create a dangerous concurrent writer race. An observed file digest alone
cannot make two unrelated writes atomic.

This milestone rehearses the **handoff transaction**, not production takeover.

## Actual files and processes

New AlarmCanonicalHandoffFixture.py accepts only a disposable directory
named bg1-canonical-fixture alongside a disposable synthetic-quickshell
source directory, and requires synthetic_only=True and an explicit
32-byte throwaway old-writer HMAC secret. The source file must be an
absolute time-alarms-v2.json, owner-only 0600, in the synthetic directory.

It reads this source with O_NOFOLLOW, validates its actual bytes and V2 shape,
and **never writes it**. All candidate alarm content, owner epoch, version,
revision, synthetic release challenge and occurrence receipts are committed
as one SQLite row in alarm-canonical-fixture-v1.sqlite3, mode 0600, under
a pre-existing 0700 private fixture directory.

The SQLite connection uses an exclusive immediate writer transaction,
synchronous FULL, DELETE rollback journal and secure_delete. A test can
inject a crash immediately before COMMIT to prove the transaction rolls back
both alarm content and the receipt. Multiple processes sharing the fixture
must observe one revision sequence; a stale revision or owner epoch refuses.

## Two-phase owner transition

1. PREPARE: verify the exact SHA-256 of the untouched source and copy V2
   state into the candidate with revision 0 and a random single-use challenge.
2. SYNTHETIC RELEASE: a disposable old-writer test key authenticates an HMAC
   over the source scope, exact source digest, old owner epoch and challenge.
   A wrong key, replay or stale revision refuses. This is a fixture stand-in,
   **not proof the real Quickshell FileView has stopped writing**.
3. CANDIDATE TAKEOVER: require release plus a strictly higher owner epoch,
   and recheck the original source digest before/after the candidate commit.
   This never transfers ownership of the real V2 file.
4. CANDIDATE ACTION: check exact expected revision and owner epoch and
   unchanged source bytes, then atomically persist a synthetic tick,
   occurrence receipt, STOP/SNOOZE or bounded note edit together. Reuse the
   existing BG1-B2A occurrence identity and B0 due eligibility rules.
5. OBSERVE / RECOVER: a fresh fixture process reads the committed SQLite
   row and continues from the durable candidate revision, or refuses
   corruption, changed source, stale epoch, stale action or a missing receipt.

All returned operation receipts explicitly include:
candidateOnly = true; ownsRealAlarmFile = false;
canRing = false; canNotify = false.

No live Quickshell QML, signed-origin PR #1959, broker, observer, audio,
Notifications, systemd or Identity/Connections file is modified.

## Real test evidence

The dedicated workflow executes:
- prepared/released/candidate phase sequencing and wrong-release denial
- duplicate and stale revision/epoch refusals, wrong ring generation refusal
- atomic due tick+receipt, STOP+receipt, SNOOZE+receipt and note updates
- real two-process SQLite contender: exactly one can win a CAS revision
- injected pre-COMMIT crash and recovery using a fresh store instance
- source changed before/after takeover, corruption, symlinks, permissions
- privacy: no alarm title or note in status receipts
- earlier BG1-A/B1/B2A/B2B1 regression suites and exact four-file scope.

## What is still missing for a real single writer

The code deliberately cannot prove the actual Quickshell writer has yielded.
A synthetic HMAC is no substitute for an independently supervised,
authenticated Quickshell bridge. There is a time-of-check/time-of-use gap
between reading the original JSON bytes and committing the candidate DB.
The old FileView can still write after the digest check. That is why the
candidate **never** becomes a real canonical alarm store here.

Before real migration:
1. Get an approved Clock-specific signed install and independently witnessed
   old/new process roles, release floor and protected session from the owner
   of the Identity/Connections security boundary (not by reusing their keys).
2. Add a default-deny Quickshell writer pause and durable acknowledged
   release; route *all* UI Save, scheduler tick, STOP, SNOOZE and note receipts
   through the future canonical writer, not a separate FileView.
3. Fence each action with a trusted owner epoch and revision. Prove the old
   writer cannot resume after handoff, including crash, rollback, logout
   and user service restart.
4. Migrate and preserve the existing V2 file with verified backup, restore,
   completeness and rollback witnesses; do not auto-promote on partial state.
5. Only after safe handoff, separately verify audio and notifications and
   explicitly authorize BG2 background delivery.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock · Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC (not live-registered)
ASSIGNMENT // BG1-B2B3 disposable canonical handoff rehearsal
PERMISSIONS // GitHub source/tests/CI/docs only, no merge or host changes
RECOVERY // Exact source hash + candidate phase/revision/epoch + SQLite row;
            all tests restart against the same private fixture
NEXT // Verified old-writer quiescence bridge, signed role trust, true
        single-writer cutover contract
DECISIONS // Deny-only fixture; no production authority or alarm actuation
