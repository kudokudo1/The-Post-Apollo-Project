# 🏥💜 DOC 1 // A read-only IPC response is not protected settlement evidence

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity  
**WORKER:** DOC 1, externally Hospital-compatible; live Hospital registration unverified  
**ASSIGNMENT:** Distinguish read-only C3e local diagnostic reply, local fixed refusal and missing/invalid response from a durable independently protected terminal receipt  
**PHASE:** Development-only negative evidence; no trusted custodian, native command or production Sign-In  
**STATE:** DRAFT / **PRODUCTION HOLD**

## IMPLEMENTATION

Linux can deliver bytes from one process to another using the existing disposable test-only `AF_UNIX` IPC. The merged [#2258](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2258) validates those bytes and returns only a diagnostic or fixed denial. **That is not the same as a durable record that some earlier operation committed or definitely did not commit.** A response might be lost after a different process changed state. A diagnostic may describe a rollbackable local SQLite row. A fixed refusal has no protected receipt proving anything about another request.

This milestone adds **four DOC 1 test/documentation/CI files only**:

- `tests/connections/c3e_release_trust/C3eIpcReceiptNonEvidenceCI.py`: a pure, deny-only classifier for the exact preexisting diagnostic envelope;
- `tests/connections/test_connections_c3e_ipc_receipt_non_evidence.py`: 30 hostile cases;
- `.github/workflows/connections-c3e-ipc-receipt-non-evidence-ci.yml`;
- this document.

The classifier accepts a *synthetic* IPC delivery observation and a single exact response frame. It may distinguish the following observations, all of which still mean **no independently protected command settlement**:

| Observation | Diagnostic status | Forbidden inference |
| --- | --- | --- |
| Complete, valid local `SNAPSHOT` / `OUTCOME` / protected `CUSTODIAN_STATUS` | `OBSERVED_LOCAL_DIAGNOSTIC_NOT_SETTLEMENT` | A protected C3e commit, noncommit, signed terminal receipt, real host/seat or consent |
| Existing fixed `IPC_CI_REQUEST_REFUSED_NO_AUTHORITY` frame | `OBSERVED_IPC_REFUSAL_NOT_SETTLEMENT` | No earlier/different command executed, or safe automatic replay |
| Missing, truncated, malformed, mismatched or unverified frame; timeout, EOF, child exit or send error | `NO_VERIFIED_IPC_FRAME_OUTCOME_UNKNOWN_HOLD` | Any terminal outcome at all |

All return `PROTECTED_OUTCOME_UNPROVEN` and a mandatory `HOLD_NO_AUTOMATIC_RETRY_REQUIRE_INDEPENDENT_CUSTODIAN` next state. All positive authority, protected commit/noncommit, signed terminal receipt, consent, Sign-In and safe-retry fields are **literally false**.

A parsed `OUTCOME` marked `consumed` remains *local fixture observation only*. It is not independently current after SQLite rollback. A parsed `issued` state is not proof that a protected action did not execute. Valid response bytes remain untrusted for authorization because the CI-only transport has no independently enrolled root or protected history.

The classifier recognizes the **existing test-only response schema** to detect malformed/extra fields and forged grant claims. It does not introduce a new executable IPC command, listener, key, service, SQLite write, credential operation, or remote transport. It does not define a future production NAS wire protocol.

## HOW TO USE

There are **no workstation or NAS steps**. This is a source-only negative behavior test running in disposable GitHub CI. It uses in-memory synthetic frames and then reruns the merged forked-process test suite from #2258, local cutover, SQLite and C3e signer/history suites without modifying their source.

DOC 6 already owns **Identity Center signed command delivery ambiguity** ([#2246](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2246)). This DOC 1 milestone **does not change or duplicate** the native command client. It covers only the lower-level protected C3e read-only diagnostic evidence boundary. DOC 2 owns installed Silverblue gateway/process evidence; C5 and Identity own human intent and action permission.

## VERIFY

The 30-case matrix tests valid `SNAPSHOT`, `issued` and `consumed` outcomes, protected custodian HOLD, fixed refusal without a nonce, timeout, EOF, missing/short/oversized or trailing frames, duplicate keys, invalid JSON constants, forged nested or top-level success fields, wrong mode/nonce/schema, and attempts to treat any such data as a protected terminal receipt or replay permission.

The workflow also reruns **46 merged IPC + 32 migration + 28 storage + 28 SQLite + 24 signed-history + 22 enrollment + 22 AF + 20 Z = 222 inherited cases**, including real forked Linux IPC and malicious frame tests. The standard Grammar, offline root-pinned admission, and inherited Fedora fake signed-RPM workflow checks must pass at the **same PR head** before Nurse 2 review.

## WATCH OUT FOR

- This is a **negative-evidence** layer only. No real protected terminal receipt is available. All observed statuses deny promotion; there is no hidden authorization switch.
- Even a well-formed fixed refusal does **not** settle an earlier ambiguous send. Do not retry a protected command without an independently authenticated terminal record and a new operator/C5 authorization path.
- A local SQLite `consumed` status remains rollbackable and not a production current head.
- A future independent NAS/other-machine custodian requires separate administrator and key ownership, externally enrolled root, authenticated transport, atomic challenge/history writes, durable signed terminal receipts, antirollback backups and crash/recovery acceptance.
- No other worker's command or C5 code should import this test-only classifier as production authorization.

## CHECKLIST / NEXT

- [x] Verify merged #2258 and Nurse 2's exact-head retrospective scoped PASS; inspect Syntagma and C3e code.
- [x] Check DOC 6's separately owned native Identity transport ambiguity #2246 and avoid its files.
- [x] Add pure synthetic negative classifier, 30 adversarial tests, dedicated workflow and this documentation.
- [ ] Verify exact-head GitHub CI and inherited regressions.
- [ ] Nurse 2 independent **pre-merge** source/CI review and operator merge disposition.
- [ ] Separate retrospective reviews remain on prior DOC 1 #2232, #2240, #2248 if not yet recorded.
- [ ] Select and implement a real independently protected custodian only with specific operator authority; **PRODUCTION HOLD**.

## DECISIONS

The operator accepted **Local Development Ledger first → Independent Trust Custodian later**, not local production trust. This change preserves the deny-only diagnostic stage without crossing into native commands, protected enrollment, actual host/NAS changes, merge, C5 consent or Sign-In activation.
