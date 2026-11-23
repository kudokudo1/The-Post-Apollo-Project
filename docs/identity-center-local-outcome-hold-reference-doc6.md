# 🏥💜 DOC 6 // Identity V5 local durable UNKNOWN_HOLD reference

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center / Sign-In V5  
**STAFF ROLE //** DOC 6 · external Hospital-compatible, live registration unverified  
**BASE //** `454cb3b1d7c785f1243260b03a9c73b515ec0f46`  
**ASSIGNMENT //** Bounded durable command-outcome negative reference, **not** an authenticated native recovery service  
**PRODUCTION //** HOLD

## IMPLEMENTATION

Current merged DOC 6 signed command client [#2246](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2246) classifies attempted transmission vs successfully verified signed receipt inside its **Python process**. That marker disappears on process death. It cannot prove that an earlier BEGIN or CANCEL had no effects.

This reference implements `services/identity/local_command_outcome_hold_reference_v0.py`:

- Opens only a **pre-existing disposable test SQLite database** in `mode=rw` or `mode=ro`. It cannot create, install or discover a database. Test setup defines the one-row schema; the service is neither a production installer nor a protected root ledger.
- Before an eventual *hypothetical* command send, `reserve_before_possible_send()` can write exactly one opaque attempt UUID, command verb and SHA-256 of the host-issued request ID (when present), in an atomic SQLite `BEGIN IMMEDIATE` transaction, with `synchronous=FULL`. It does not store passwords, tokens, cookies or raw host request IDs.
- Once any local attempt is recorded, all further local reservations fail. A second process can inspect the existing record after a crash. A concurrent pair of separate test processes cannot both insert a row.
- Every inspection result has state `UNKNOWN_HOLD`, zero safe actions, false issuer-reconciled, false production-authority and all native action capabilities false. The **empty** database also reports `UNKNOWN_HOLD`, because the caller may have rolled back the local file to a pre-attempt backup.
- Missing/corrupt/wrong-schema databases refuse reservation and return a negative diagnostic. Local same-UID SQLite rollback/replacement is detectable only where it produces a visibly missing/corrupt or contradictory file. A valid older backup *cannot* be proven current by this source; that is why no positive result exists.
- No native command is issued or wrapped; this reference is **not connected** to `desktop_signed_command_client_v0.py`, the installed adapter, C5, CPU++ or the real host. It is a local crash/replay refusal rehearsal, **not** an enforced live pre-send fence.

The existing DOC 1 local development ledger cannot grant independent authority. The future protected custodian must keep signing, history, challenge/revocation and antirollback under separate administration. DOC 2 must supply actual installed host signer/process evidence, and an explicitly assigned Identity C5 owner must supply one-use authenticated operator intent.

## HOW TO USE

No UI action. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains read-only, with Sign In/Cancel/Retry disabled.

Only in disposable tests, create a test SQLite database using the test suite's `_FIXTURE` schema. Then reserve **without sending**:

```python
store = TestOnlyLocalOutcomeFence(absolute_test_db_path)
hold = store.reserve_before_possible_send(
    attempt_id="a" * 32,
    action="BEGIN",
)
assert hold.state == "UNKNOWN_HOLD"
assert hold.can_begin_sign_in is False
```

A new Python process can inspect the record, but it cannot clear it or derive permission to retry. **Do not run these fixtures against the operator workstation or real credentials.**

## VERIFY

Dedicated new workflow executes negative tests for:
- Empty history, successful local reservation, restart in the same and a new Python process.
- Duplicate attempt, second action, and two distinct local Linux processes racing to reserve the single row.
- Restoring a pre-attempt backup; empty but valid rolled-back DB still refuses any action.
- Missing/corrupt/wrong-version store, malformed UUID/action/request ID, invalid row data, no plaintext request ID.
- No native dispatcher import or `send/settle/clear/retry` API.
- Existing Identity V5 diagnostic, mandatory installed adapter-only source test and CPU++ fixed-offline regressions.

Exact-head GitHub CI and independent Nurse 2 review must be verified **before** any merge. These are negative CI fixtures, not actual production process/seat, signer, or protected C5 consent tests.

## WATCH OUT FOR

**SQLite durability is not trusted custody.** `synchronous=FULL` and `BEGIN IMMEDIATE` provide ordinary transaction/crash semantics on the runner; they cannot prevent a same-UID worker or backup from replacing the entire file, and they cannot prove original host side effects after lost acknowledgments. Even a valid local recorded attempt is an *untrusted* clue. **Never** implement an `is_clear`, `can_retry`, `safe_to_recover` or `production_authority` path from this database.

The reservation is not currently wired into the signed command client's `sendall`. Wiring to real native commands would be new security-sensitive work requiring DOC 1/2/C5 owner evidence and independent code review. This reference alone does **not** close the crash window for the current experimental client; it specifies and tests a conservative persistence mechanism for a future reviewed adapter.

## CHECKLIST

- [x] Read current Syntagma AGENTS and Hospital agent/report protocols; check main and DOC 6 source ownership.
- [x] Preserve merged #2236 admission diagnostic and #2246 local client marker.
- [x] Implement test-only SQLite one-row write-ahead negative reference and no authority API.
- [x] Add isolated forked-process/restart/rollback/corruption/concurrency tests and dedicated workflow.
- [ ] Exact-head CI success and repair.
- [ ] Independent Nurse 2 **pre-merge** review.
- [ ] Operator merge approval.
- [ ] Protected external issuer, signed host outcome query, original C5 one-use consent and crash/replay native acceptance.

## NEXT

Review CI and request Nurse 2's exact-head source/CI security audit before merging. Under the DOC 6 native integration assignment, the next owner-dependent milestone is a **versioned, read-only, independent issuer outcome lookup**, with challenge, host/process/seat and one-use C5 binding, plus rollback-resistant storage and no local fallback. Until that real trust provider exists, local diagnostics must stay at `UNKNOWN_HOLD`.

## DECISIONS

This is a development reference only, NOT a proposed new authority deployment or finalized production protocol. No C3e/C4b/C5/CPU++ ownership changes, no provider login, workstation/NAS writes, protected key generation, live Hospital registration, automatic merge or native activation. Operator controls final acceptance.
