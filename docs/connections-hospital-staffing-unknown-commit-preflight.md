# 🏥💜 Connections ↔ Hospital // Unknown COMMIT outcome safety preflight

**PATIENT:** The-Post-Apollo-Project · Connections Hospital Staffing Issuer  
**STAFF ROLE:** DOC source-only continuation, no verified live Hospital registration  
**BASE:** [staffing source recovery draft #2082](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2082), exact source `d2fa67639b248d0732a870db42700f004e5a1e4c`; [Hospital protected writer #133](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/133) pinned `ee1dc74056fbd2c849d3391e3148b003514b2932`  
**AUTHORITY:** Bounded Connections-only source/test implementation. No new writer schema, signer custody, production key, installation, native consent or merge permission. Previous protected C3e/Identity worker remains paused.

## IMPLEMENTATION

A network send is different from a completed database transaction. Once an issuer has *attempted* a COMMIT packet, a timeout or socket disconnect does not show whether the Hospital writer committed the source mutation. Blindly resending the same signed grant could duplicate or mislabel an operation. Likewise a JSON message claiming `"status":"COMMITTED"` is not a trusted writer receipt.

This new, **read-only CI-only** classifier consumes the preexisting source-only PREPARE / PREPARED / COMMIT context through `StaffingReceiptIdentityPreflight._source_context` (which inherits canonical frame, original nonce/Room/action/Session, grant-body graph/revision, writerInstance and exact COMMIT checks). It then compares a restricted *synthetic caller trace*, with exactly three diagnostic stages:

| Stage | Diagnostic | What it permits |
| --- | --- | --- |
| `LOCAL_BEFORE_SEND` | `NO_SEND_OBSERVED_IN_CALLER_CI_TRACE` | No production conclusion. Claim remains caller-controlled. |
| `SEND_ATTEMPTED` | `POST_SEND_UNKNOWN_MAY_HAVE_COMMITTED` | No automatic retry, no assumed refusal or commit. Reconcile through protected writer. |
| `UNVERIFIED_RESPONSE_OBSERVED` | `POST_SEND_UNKNOWN_MAY_HAVE_COMMITTED` | Received bytes are hashed for audit only, **never** parsed as authentic commit/refusal. |

The fixed source-only observation vocabulary covers local composition/scope refusal or pre-send cancellation; attempted send with no ack, timeout, exception, disconnect, truncation, unknown version, malformed reply or writer restart; and bytes received from a purported writer. A reply outside the proposed 16,384-byte CI diagnostic bound refuses. Stage/observation mismatches and unexpected reply bytes refuse.

All `writerIdentityAuthenticated`, `installedWriterReleaseVerified`, `writerReceiptAuthenticated`, `writerTransactionCommittedVerified`, `writerTransactionRefusedVerified`, `writerAlreadyAppliedVerified`, `hospitalReplayLedgerVerified`, `nativeOperatorAuthorized`, C5 human, credential, staffing permission and production fields are **hard-false**. `neverAutoRetryThisGrant` is always true. The exported native recovery entrypoint always refuses `NATIVE_HOSPITAL_WRITER_RECOVERY_NOT_INSTALLED`.

**This is not a reliable native journal.** The stage and packet traces originate from disposable CI arguments, not an authenticated running issuer. They may not be used to assert that a real network operation was never sent or safely replayed.

## HOW TO USE

The dedicated workflow checks out actual Hospital #133 parser and coordinator source at the pinned commit, runs 24 source-only adversarial cases, and re-runs the parent's 32 receipt and native socket credential/packet tests. No runner-generated key is enrolled and no durable Hospital database is accessed or modified.

## VERIFY

- [ ] Exact-head 24 unknown-outcome tests pass
- [ ] Exact-head parent 32 receipt tests and inherited transport negative tests pass
- [ ] Exact-head Grammar and other relevant checks pass
- [ ] Source scope only four additive Connections-owned files
- [ ] Independent Nurse 2 exact-head review
- [ ] Hospital protected writer-owner decision on actual receipt states/recovery
- [ ] Operator final acceptance and separately authorized merge / installation

## WATCH OUT FOR

A synthetic `LOCAL_BEFORE_SEND` diagnostic is not independently authenticated evidence that nothing reached Hospital. It must never become an automatic retry permission. In particular `SEND_ATTEMPTED`, `DISCONNECT`, `TIMEOUT`, `WRITER_RESTART`, `MALFORMED_REPLY`, `RECEIPT_TRUNCATED`, or fabricated `COMMITTED`/`REFUSED`/`ALREADY_APPLIED` response bytes are all **UNKNOWN** until the protected Hospital writer supplies an independently verified, durable outcome.

The proposed parent receipt is still a **15-field CI-only design**, not Hospital's accepted production result. Hospital's actual #133 source contains only a disposable fixture receipt; it does not currently expose signed native writer outcomes. Do not infer `revisionAfter = expectedRevision + 1`, do not introduce an optimistic second signer, do not modify Hospital #133 and do not transfer writer database ownership.

## NEXT

After Hospital's owner and the operator approve **actual** protected writer-origin identity, transaction/result schema and recovery behavior, replace the unverified diagnostic consumer with a separately reviewed native issuer-facing result verifier. The writer must own the durable COMMITTED / REFUSED / UNKNOWN / ALREADY_APPLIED reconciliation record and grant/nonce consumption inside its protected transaction. Connections must authenticate the writer response before advancing any externally visible result.

## DECISIONS

Source/CI-only independent stacked draft. No keys, native staffing issuer, Polkit action, credentials, Human consent, database migration or user workstation action. Parent #2082 remains under independent review; production authority stays off.
