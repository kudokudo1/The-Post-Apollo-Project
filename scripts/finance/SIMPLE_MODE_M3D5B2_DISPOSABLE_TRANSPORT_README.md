# FinanceW Simple/Budget // M3d5b2 disposable transport & durable custody

**PATIENT:** The-Post-Apollo-Project
**ROLE:** Simple/Budget DOC implementer, not independent Nurse 2
**ROOM:** FinanceW Simple/Budget
**BASELINE:** M3d5b1 PR #2614 merged, independently reviewed SCOPED PASS #6052669097
**STATUS:** New NON-ACTIVATED disposable transport fixture, not a desktop Save bridge
**PRODUCTION FINANCIAL WRITES:** HARD HOLD

## IMPLEMENTATION

M3d5b2 introduces a strictly *disposable* protocol experiment rather than connecting the live M3b Actual writer.

- **Wire-grammar inspection only:** inspectM3d5b2StdinFrame checks one bounded JSON newline frame against the exact 13-field M3b categorized command schema and returns only a hash and no-activation status. No frame is sent.
- **Outcome interpretation only:** inspectM3d5b2WriterOutcome parses the writer's fixed FINANCEW_CATEGORIZED_EXPENSE_RESULT status line. A purported commit with nonzero exit, missing output, extra lines, malformed output, or unknown status is uncertain and non-retryable. These are synthetic results, not actual writer outputs.
- **Durable TEST-ONLY identity custody:** reserveM3d5b2DisposableIntent requires FINANCEW_DISPOSABLE_TEST=yes, the exact temporary HOME, and a private top-level financew-m3d5b2-fixture-* directory in the OS temporary directory. The Linux descriptor-anchored trust helper refuses symlinks and untrusted modes. The code creates a new private reservations directory only inside that sandbox; uses an exclusive, fsynced lock; examines previous private records; and writes a single fsynced exclusive sealed-dry-run intent. No full financial command is persisted: only a request ID, command-fields fingerprint excluding requestId, schema version and status.
- **Cross-process replay:** identical request IDs and identical command fields with a fresh request ID refuse on a second Node process. A reservation survives normal process exit. A stale lock or malformed record refuses for manual investigation. Unknown failures deliberately preserve the lock rather than silently trying again.
- **No actuation:** no Actual import or network, no writer Process, no production permit, no UI binding, no transaction mutation, no changes to shared FinanceW operation journals. Every exported status retains canSave:false, writeAllowed:false and dispatched:false where relevant.

## HOW TO USE

No new feature is mounted in FinanceW. The existing Budget > SIMPLE > TRANSACTIONS > CATEGORY // PREVIEW ONLY > CHECK CATEGORY SAVE READINESS remains read-only. M3d5b2 is solely a disposable CI fixture and MUST NOT be interpreted as a live Save or financial permission.

## VERIFY

The dedicated GitHub Action checks:
1. Real separate Node-process restarts: durable intent and duplicate refusal by requestId AND canonical command content.
2. Explicit temporary HOME + prefix gate; unknown paths, symlinked or writable directories and lock recovery refusal.
3. No raw transaction description/account in the durable record and private file modes.
4. Bounded one-line stdin JSON contract, fixed stdout status grammar, all uncertain outcomes non-retryable.
5. The prior independently reviewed M3d5b1 confirmation/cancel/recovery tests unchanged.
6. Source-only production HOLD, no writer call path or production journal reference.

Test data uses fictional accounts and a private temporary directory only.

## WATCH OUT FOR

- **No live durable identity or financial dispatch.** The reservation directory is an intentionally different, isolated test namespace, not the M3b finance journal. Real durable identity/consent custody would require integrating the M3b exclusive journal and its permit/security model in a later, separately reviewed transport.
- The M3d5b1 controller still discards the request ID after confirmation; M3d5b2 does NOT connect to M3d5b1. There is no false claim of an end-to-end controller. Confirmation UX is not authentication.
- No source-port migration. M3d5b1's refusal of a 5007 read-only source for the 5006 protected writer remains intact and needs explicit source-owner agreement before future protected writes.
- This fixture is Linux-specific (through the M3b /proc/self/fd trust helper), and is not a proof against same-UID compromise, arbitrary machine power loss, or malicious disks.
- Future design must inspect failure between journal ATTEMPTED, actual commit and stdout ACK; M3b writer still owns authoritative fresh Actual preflight.
- Other FinanceW workstreams, Categories-owned tests and the installed QML UI are not modified.

## CHECKLIST / NEXT

- [ ] Exact-head CI PASS and raw log review.
- [ ] Nurse 2 independent source/security review of this M3d5b2 fixture.
- [ ] Coordinate source compatibility with Budget owner and protected M3b writer.
- [ ] Develop protected transport adapter with durable one-use identity under M3b shared lock and operator security approval, NOT by copying this fixture directly.
- [ ] Disposable Actual end-to-end + crash/recovery, native UI and final operator acceptance.
- [ ] Explicit separate authorization before any real financial permit or production mutation.

## DECISIONS / ROLLBACK

Scoped fixture-only implementation. No local desktop or financial-account changes, no production activation and no merge authority. Reverting this PR deletes only the new source, test files, workflow and README; no real FinanceW data or configuration is changed.
