# TimeW M4 // Read-only local exact-capture preview (Scope A)

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Scope A, local-first ordinary data  
**STAFF ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**PHASE //** Source/CI preview contract, no TimeW.qml changes  
**PRODUCTION RESTORE // HOLD**

## Mechanism

Merged [TimeW M3 #2284](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2284) stores ordinary local, caller-supplied CURRENT logical coordinates as exact IEEE754 binary64 bits in a separate v3 SQLite file. That store does not know which native window was selected, what SwayPX acknowledged, whether an image was presented, or whether a C5 operator grant was independently spent. The [operator's decision](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067#issuecomment-7099013916) remains **local normal data now; separate protected hardware later**.

This milestone adds the separate services/time/MachineV3LocalExactCapturePreview.py **read-only** adapter. It mirrors the existing MachineRestoreReviewV2.py design: bounded JSON records, non-authorizing status, stable output fields, zero safe actions, and one explicit CLI mode. It only calls LocalExactCaptureStore.for_checkpoint() to inspect one requested v4 checkpoint ID from **one explicitly supplied local DB path**. There is no automatic XDG discovery, desktop read, unscoped listing, Sway or Brave process inspection, network call, SQLite write, GUI import or programmatic capture.

- **LOCAL_CAPTURES_UNTRUSTED_HOLD**: local entries exist but are **not** source-authenticated, selected-window evidence, consent, settled frames or native receipts.
- **NO_LOCAL_CAPTURES**: absent local DB or no rows for that checkpoint, with no file/directory creation.
- **UNAVAILABLE_HOLD**: strict malformed input, schema refusal, invalid geometry or oversized JSON. Fixed generic response without DB path, checkpoint ID or partial rows.
- Coordinates use both Python float repr() and float.hex() strings, avoiding accidental display rounding of neighboring binary64 values. These are **view formats, not signed wire formats**.
- Multiple windows are shown only for the exact checkpoint. The preview must not print URL, window title, process ID, grant/key, app credentials or full database path.

## Developer-only usage (not yet connected to TimeW UI)

On a separately approved test checkout with an already-created disposable v3 database, a developer may **read** one checkpoint without running the live TimeW application. Invoke Python with -B -I on services/time/MachineV3LocalExactCapturePreview.py followed by the exact arguments: preview, an absolute path ending post-apollo/machine/v3-exact-local-captures.db, and a version-4 checkpoint UUID.

For example, use a disposable v3 SQLite fixture in CI. This reads only the explicit path, emits bounded JSON and exits. It refuses save/restore/execute/enumerate-all arguments. If the database is absent, it does not create it. Do not run against the operator's desktop data without a separately approved host inspection context.

The native TimeW UI **has not gained a new preview button**; the source is an isolated inspection layer for later UI integration. Do not describe these JSON previews as native verified geometry or allow their values to drive Restore.

## Verification and scope

- Disposable temporary v3 DB and fresh isolated child Python CLI cover zero-file reads, two local windows at one checkpoint, another unrelated checkpoint, exact fractional and one-ULP display, no write on preview, malformed requests, forgeable authority flags, valid-bit substitution, corrupted-bit fail-closed and no partial result leaks.
- Re-run M3 storage tests and existing exact binary64, fractional observation, V2 SQLite and journal regressions.
- Review two **new** source files, one workflow and this note; no changes to V1/V2 storage, TimeW.qml, live Save, C5 SPENT, SwayPX/Connections, GUI or native runner.
- Independent Nurse 2 exact-head review **before merge**. An eventual user-facing read-only browse control needs its own UI/host-scope review. Native Restore requires separately accepted source enrollment, selected surface, true ACK/frame settlement and protected C5 custody.

**DECISIONS //** Local ordinary data remains local, future NAS/custodian migration is separate. This preview grants zero authority, makes no host changes and cannot be promoted into an authenticated native receipt. **Production Restore HOLD**.
