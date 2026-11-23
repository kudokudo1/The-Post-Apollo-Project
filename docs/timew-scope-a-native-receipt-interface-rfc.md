# TimeW Scope A // Native receipt interface RFC and untrusted lineage shadow

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Desktop & Brave Recovery · Scope A  
**STAFF ROLE //** TimeW owner DOC, external Hospital-compatible; live Hospital registration unverified  
**STATUS //** PROPOSED contract requirements and test-only diagnostic comparison. **NOT APPROVED CANONICAL WIRE. PRODUCTION RESTORE HOLD.**

## Mechanism and current evidence

TimeW's merged [#2207](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2207) provides exact in-memory binary64 coordinates; [#2260](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2260) compares initial CURRENT, desired PENDING, reported post-resize CURRENT and reported final CURRENT. Both deny native authority.

SwayPX's reviewed [#176](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/176) demonstrates a real compositor timeout may apply CURRENT and arrange the scene without successful configure ACK or independently verified presentation. SwayPX [#178](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/178) is an open, unmerged native diagnostic lineage experiment: a process-generated boot tag plus monotonic local lifetime/transaction counters, actual XDG map/unmap, and exact PENDING value comparison. **Its transaction counter is not issued at transaction_commit.** Its scale/transform and seat/output/workspace epoch records are not a source-signed packet. The C header explicitly forbids exposing the private interface through IPC.

DOC 5's merged [#2259](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2259) models C5 SPENT→native timeout and lost-ACK recovery as permanently denied caller-controlled observations. DOC 1's merged [#2258](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2258) hardens deny-only local IPC diagnostics. **Neither creates a production trust root, genuine signed native receipt or rollback-resistant C5 ledger.**

## Scope of this TimeW implementation

\`tests/timew/TimeWScopeALineageDiagnosticShadow.py\` is deliberately confined to tests. It reviews two caller-created dictionaries made from the numeric *diagnostic* tag/epoch/scale/transform names in #178, with strict type, range and exact-field checks. It rejects lost samples, malformed data, stale boot/lifetime/transaction tags, changed seat/session/output/workspace epochs, one-ULP scale drift, changed transform, reported timeout, revocation, host exit, missing live surface and locked seat. **Even a complete exact match is \`MATCHED_DIAGNOSTIC_UNTRUSTED_HOLD\`, never permission.** No native pointers, C struct bytes, keys, decoded source packets or C5 claims are accepted as trust.

This is **not an approved serialization, cross-process contract, receipt decoder, runtime importer, canonical schema or future guarantee of compatibility with #178**. It does not assume that a fabricated pair of snapshots proves anything about the real compositor. The diagnostic names here must not be treated as accepted external API fields.

## Proposed joint acceptance requirements (not yet approved)

| Evidence boundary | Required proof before native TimeW continuation | Owner to specify |
| --- | --- | --- |
| Source and authority | Independent installed compositor release/process/host identity, active physical operator seat and enrolled signing root, with exact audience, revocation and current challenge | C3e DOC 1 + C4b DOC 2 + SwayPX |
| Target | Exactly one operator-selected, currently mapped non-fullscreen floating XDG, native object and boot/lifetime/output/workspace/seat generation, no stale/reused pointer, no app_id-only selection | SwayPX |
| Operation | One exact checkpoint/window/operation/intent/grant/source context, original/target *binary64* x/y/width/height, transform/scale and logical layout coordinate semantics | TimeW + SwayPX + C5 DOC 5 |
| Wire | An independently versioned canonical signed packet with explicit byte order, lengths, strict unknown-field/version refusal, domain separation, replay protection and key rotation | Joint TimeW/SwayPX/C3e/C4b/C5 decision |
| Consent | Actual trusted operator-visible review of the full immutable operation and protected *one-use SPENT before any first effect* with durable rollback-resistant history and revocation precedence | DOC 5 + C3e owner |
| Resize | Genuine source-protected resize dispatch identity, client configure ACK vs forced timeout, fresh **post-resize** x/y/width/height, selected lifetime and independent settled/presented frame proof | SwayPX |
| Move | Only after authenticated settled resize, source-authenticated distinct move dispatch and final exact geometry + terminal presentation, with same selected identity and full context | SwayPX + TimeW |
| Crash | Missing receipt, unknown outcome, duplicate/late ACK, timeout, host exit, revocation, rolled-back/forked history or restarted native source must produce UNKNOWN/HOLD with **no automatic MOVE, retry, undo or new grant** | TimeW + DOC 5 + C3e/C4b |
| Compatibility | Historical integer-only V1/V2 checkpoint, journal and restore paths remain unchanged; any fractional persisted lane must be separately versioned and reviewed | TimeW |

## Known blockers and ownership decisions needed

1. **SwayPX:** Agree how actual selected XDG object lifetime, operator selection, native transaction_commit generation, ready-vs-timeout and independently settled frame will be captured; #178's local tags alone do not qualify.
2. **DOC 1/DOC 2:** Agree installed signer, source release/host/seat and independently protected current-history root. Local SQLite and one-request CI IPC are not sufficient.
3. **DOC 5:** Agree trusted display/consent and independent SPENT keeper, revoke ordering and terminal recovery.
4. **TimeW:** After joint acceptance, implement an independently versioned parser and protected receipt consumer in a separate reviewable PR; do **not** widen old V1/V2 rows in place.
5. **Nurse 2 and operator:** Require exact-head review before merge where possible and separate authorization for native trial, merge, installation and production Restore.

## Verification

The new CI validates the test-only comparison and re-runs the existing TimeW exact/fractional/SQLite/journal regressions. It creates no native process, socket, signer, database, IPC, window command, QML binding or host modification.

**DECISIONS //** The only operative rule retained here is **PRODUCTION RESTORE HOLD**. The proposed proof table and field set are **not approved**, and any future owner acceptance must be recorded separately in [TimeW coordination #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067).
