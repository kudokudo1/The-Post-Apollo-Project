# FinanceW Simple/Budget // M3d5b3 Protected Writer Bridge Contract (NON-ACTIVATED)

**PATIENT:** The-Post-Apollo-Project
**ROOM/ROLE:** FinanceW Simple/Budget · Simple DOC (developer, not independent reviewer)
**CONNECTION:** External Hospital-compatible; no verified live Hospital registration
**BASELINE:** M3d5b2b #2639 merged, independent SCOPED PASS #6055503517
**FINANCIAL WRITES:** HARD HOLD · No local financial writes, no permit, no protected bridge activation

## IMPLEMENTATION

M3d5b3 establishes the *read-only policy seam* for a future protected transport, without installing a second financial writer. The new pure Node module is not imported by the existing QML UI or any live writer, does not read or write files, does not construct a command, and cannot dispatch to Actual.

**Review + confirmation source**:
- Rechecks the merged M3d2 offline category witness against current nested budget/amount/selection values, rather than trusting an earlier visual review.
- Requires explicit, separate reader and protected writer endpoint witnesses, exactly matching the writer's pinned loopback URL http://127.0.0.1:5006 and equal source keys. In particular a read-only default on 5007 fails closed. These are plain caller values and do NOT constitute independent file/network attestation.
- Recognizes the M3d5b1 non-activated controller's confirmed-but-dispatch-disabled receipt, but explicitly refuses it as a durable operation identity. M3d5b1 discards the random requestId, so its fingerprint cannot reproduce the same 13-field M3b command across restarts. It is never used as a replacement request ID or transaction authority.
- Rejects an attempted caller-supplied executable command/requestId on the purported confirmation receipt. Never creates an independent authorization shortcut around M3b.

**Synthetic recovery matrix**:
- Models before-reservation, sealed-dry-run, writer-attempted and writer-exited phases with absent/sealed/attempted/committed/corrupt synthetic journals and crashes/timeouts.
- Reuses M3d5b2b's strict one-line LF result parser. Missing, malformed and inconsistent results are uncertain and never retryable.
- Even a matching synthetic acknowledgment + a hypothetical committed journal and readback is labeled synthetic-evidence-consistent and never a real Actual commit. No output can authorize replay or actual dispatch.

**Duplicate semantics:** A same-date, same-amount future legitimate expense is not globally banned. M3d5b2's disposable content fingerprint is intentionally NOT adopted as production replay policy. A protected one-use identity must be bound to a particular confirmed intent, with M3b's writer-specific duplicate detection and durable journal under lock.

## HOW TO USE

No new button or local command is connected. The UI route remains:

Finance -> Budget -> SIMPLE -> TRANSACTIONS -> NEW DRAFT -> CATEGORY // PREVIEW ONLY -> CHECK CATEGORY SAVE READINESS.

Readiness remains review-only, no transaction created.

## VERIFY

GitHub Actions run a real M3d5b1 stage + confirm in a private fictional temporary directory and feed its non-activated receipt into the new bridge, confirming that the missing durable request ID remains blocked. Additional tests cover source/port mismatch, stale/in-place changed category and budget, forged receipts, crash/timeout/unknown outcomes and the safe strict parser. Existing M3d5b1/M3d5b2b/M3d2 regression suites must remain green.

## WATCH OUT FOR

- **Not an executable writer bridge.** There is no command or requestId released from the current M3d5b1 controller. Building a future durable handoff requires a separate change to its custody/confirmation boundary with independent security review.
- **Endpoint ownership unresolved:** Reader defaults to 5007 and M3b pins 5006. This contract rejects disagreement but does not change the live source or configuration. Seek the Budget/source owner's agreement before any integration.
- **No fresh Actual preflight** or authenticated journal evidence. Those belong to M3b under its private permit, shared exclusive lock, ATTEMPTED fsync and separate Actual readback.
- Current cross-writer journal ambiguity, operation abandonment, duplicate content and process restart scenarios all require native disposable safety testing before activation.
- No local host edits, real funds, credential modification or production journal operations. Categories/Banking/Market/Research sources unchanged.

## CHECKLIST / NEXT

- [ ] Exact-head CI PASS and raw log review.
- [ ] Independent Nurse 2 M3d5b3 source/contract review.
- [ ] Explicit Budget source/port contract with owner.
- [ ] Design durable one-use confirmation custody without exposing request IDs to an untrusted UI.
- [ ] Build *separately reviewed* non-activated protected writer adapter preserving M3b's private permit, lock/journal, fresh Actual source/readback and uncertain outcome.
- [ ] Real disposable Actual crash tests, native UI operator acceptance and final production-write authorization.

## DECISIONS

No endpoint migration, second writer, silent permission creation or activation. This is an isolated source-only contract; revert the new source, tests, CI and README to roll back. Any production path remains blocked until explicitly accepted.
