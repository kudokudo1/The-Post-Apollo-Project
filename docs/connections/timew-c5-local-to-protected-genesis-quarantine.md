# 🏥💜 DOC 5 // TimeW C5 local-history quarantine at future protected cutover

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Connections C5 ↔ TimeW Scope A  
**STAFF ROLE //** DOC 5, external Hospital-compatible (live registration unverified)  
**ASSIGNMENT //** Local C5 fixture-history nonpromotion and future independent custody recovery boundary  
**STATE //** Source/CI-only negative reference; not an accepted native wire, protected service or production cutover  
**PRODUCTION //** TimeW Restore HOLD

## DECISIONS // Operator storage strategy is accepted

The operator's [2026-11-23 direction](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067#issuecomment-7099013916), also [recorded for C3e/C4b/C5](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119#issuecomment-7099015686), is final for the development **sequence**:

1. Normal TimeW checkpoint/layout/journal/capture data may remain local while the software is developed. TimeW owner [draft #2284](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2284) is implementing a separately named, untrusted exact-binary64 local capture store in its **own** files. DOC 5 does not alter or import that service.
2. Once Post-Apollo NAS/cross-computer Connections infrastructure is actually ready, applicable durable data and **protected authority** may migrate to separately administered hardware, with its own independent custody, fresh source/role/key enrollment, and explicit migration/activation approval.
3. Local C5 development SQLite (including the synthetic `ACTIVE`, `SPENT`, `REVOKED` and `UNKNOWN` labels), copied backups, self-described operator approval and diagnostic signed-looking history are **not** current/rollback-resistant production grants. Future enrollment **must not import these as authorization**. A filesystem NAS mount writable by the same host/user is not independent custody.

**This policy does not choose a particular NAS, custodian identity, key algorithm, deployment date or final retention policy.** Those are separate future operator/root/owner decisions. Do not reopen the already decided *local-first vs separate-hardware-later* storage strategy.

## IMPLEMENTATION // Four-way distinction, not a migration routine

The additive `tests/connections/timew/TimeWC5LocalHistoryQuarantineReference.py` models a **pure in-memory hostile fixture** to exercise an eventual cutover firewall:

- **Ordinary local TimeW data** is outside this C5-specific fixture and remains TimeW-owned. A saved layout is not consent or selected-surface identity.
- **Local C5 fixture history** is test-generated, revocable/rollbackable and may be retained as historical evidence only. Strict TimeW-specific audience/action, grant/operation/issuer and exact local origin are validated; duplicate IDs and forged positive fields fail closed.
- **Archive-only candidate** is *not an actual archive write*: local state might be kept for audit if a later separately approved implementation explicitly copies it. This source never copies, deletes, redacts, uploads or certifies an archive.
- **Fresh protected genesis candidate** must use independent new identities/roles and current history. The reference detects obvious syntactic reuse of local grant/operation/issuer/key/head and refuses all proposed historical authority imports, backup restores and local fallback. **A perfect disjoint candidate still ends `FRESH_GENESIS_CANDIDATE_UNENROLLED_HOLD`** because caller-provided UUIDs/heads/claims do not independently prove separate hardware, current history, genuine enrollment or human consent.

The test input names `LOCAL_DEVELOPMENT_ONLY`, `SEPARATE_HARDWARE_CANDIDATE`, and `FRESH_EMPTY_GENESIS` are **private fixture labels**, not approved network field names or a production migration scheme. Every returned result sets production/native/one-use consent/custodian/current-head/activation/retry/undo flags FALSE and `safe_actions=[]`. Even `archive_copy_performed` and `archive_verified` are always FALSE.

The module imports the existing DOC 5 `TimeWC5SpendFenceReference._claim` strictly for **test claim syntax**. It does not open the test SQLite ledger, read TimeW v3 capture data, authenticate another system, issue commands, sign packets, read an actual NAS or install software. No local filesystem/network I/O.

## HOW TO USE

This isolated suite runs only in disposable GitHub Actions or a deliberate developer test checkout:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_local_history_quarantine.py
```

The dedicated workflow also runs inherited DOC 5 spending, custodian-provider negative checks and TimeW exact-review tests. It does not configure the operator's Fedora workstation or create a database, network service or signing key.

## VERIFY / WATCH OUT FOR

Hostile tests include local `SPENT` promotion, backup replay, historical grant/operation/issuer/key import, distinct synthetic genesis that **still denies**, key/history-head reuse, local fallback, forged admin approval, malicious positive authority fields, wrong audience, malformed claims, duplicate identifiers and upper bounds.

**This does not prove a real hardware cutover is secure.** A malicious host can invent disjoint UUIDs/heads, forge a history, replace a local SQLite snapshot or present a dishonest separate-hardware claim. Real current-head authority, protection from local rollback, trusted operator intent and source-signed SwayPX native settlement are still missing. A retryable read-only recovery lookup is never permission to repeat a command.

The existing [DOC 5 proof-obligation RFC #2271](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2271) remains **contract REVISE/HOLD** following the retrospective Nurse 2 review. The TimeW owner controls local v3 data; SwayPX owns native original selection/transaction settlement; DOC 1/C3e and DOC 2/C4b own independently enrolled native producer infrastructure; DOC 5 owns the TimeW-only one-use human consent/SPENT and recovery history. No Hospital, Forest, TASKS, Brave or Identity key is reused.

## CHECKLIST / NEXT

- [x] Reuse operator-approved local-first staging decision without a repeated user question
- [x] Keep DOC 5 changes separate from TimeW #2284 and the SwayPX compositor implementation
- [ ] Exact source-head GitHub CI
- [ ] Independent Nurse 2 pre-merge scoped review
- [ ] Operator merge disposition
- [ ] Future independently enrolled protected custody, fresh approved genesis and historical archive plan
- [ ] Joint native receipt/selected-window and real terminal recovery integration, with operator production acceptance

**DECISION //** This test-only nonpromotion reference advances the C5 boundary without establishing any actual protected authority. Production TimeW Restore remains HOLD.
