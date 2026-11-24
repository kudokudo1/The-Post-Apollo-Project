# FinanceW Simple M3d3 // Dedicated real Actual categorized writer rehearsal

**PATIENT:** The-Post-Apollo-Project
**ROLE:** FinanceW Simple/Budget successor DOC, external Hospital-compatible; live registration unverified
**STATUS:** Source-only CI rehearsal in draft PR, not production accepted
**PRODUCTION FINANCIAL WRITES:** HARD HOLD

## IMPLEMENTATION

This milestone adds a **new CI-only disposable test** for the already merged M3b categorized expense writer. No existing writer, Actual read service, FinanceW root, editor, category preview pane, permission policy, local host or journal code is changed.

The isolated runner creates a temporary HOME, a private fictional Actual budget and its own ephemeral loopback server at `127.0.0.1:5006` using pinned `@actual-app/api@26.10.0` and `@actual-app/sync-server@26.10.0`. The script refuses execution unless `GITHUB_ACTIONS=true`, `CI=true`, and `FINANCEW_DISPOSABLE_TEST=yes`. It checks the endpoint port is free before starting, never connects to the operator's Actual server, and disposes its temporary data and child server.

It tests the **real production M3b CLI** with a permission file created **only in temporary CI HOME**. The first invocation without a permit must refuse; the next must reject a mismatched source and stale category balance without writing. An authorized fictional transaction must create once with the category in the same add operation and commit a durable private receipt. A completely independent second Actual client downloads the budget and verifies exact category ID, amount, account, date, imported ID and uniqueness. Request-ID replay and duplicate-date/amount are denied.

For a realistic uncertain-write seam, the test additionally wraps the real Actual engine with an **injected sync failure after exactly one real addTransactions call** and writes a disposable ATTEMPTED receipt before that add. It verifies one add, one sync attempt, no retry and retention of the attempted record. Then the production M3b and existing D9 CLIs both refuse further writes while that unresolved record exists. This fault injection does **not** by itself simulate a real crash of the unmodified CLI process; that separate SIGKILL failure matrix remains a future security-review consideration.

The same read-only Actual snapshot projects group/category `hidden` flags. The test reports `visibility=known` or `visibility=unknown` rather than turning omitted flags into false. Missing values are still a blocker for a future write-ready preview and do not weaken the M3b writer's own fresh Actual preflight.

## VERIFY

CI checks source-isolation contracts, installs pinned Actual 26.10.0, then runs the real server and CLI. The success marker is `FINANCEW_M3D3_DISPOSABLE_PASS`. This marker is supported only after inspecting exact-head raw logs; a source PR or automatic check alone is not acceptance.

## WATCH OUT FOR

This is a test of a **fictional disposable budget only**. It is not a production bank/account operation, user-host credential, real financial permission or live Save enablement. The operator has not accepted activation. The M3b writer #2356 has no recorded independent Nurse 2 financial-write review. M2b envelope-move writer remains separately held. No automatic retry or journal deletion is part of any live path.

## CHECKLIST / NEXT

- [ ] Exact-head M3d3 CI and raw logs
- [ ] Independent Nurse 2 M3b financial-security review, including journal/lock and uncertain outcome
- [ ] Budget source-owner review of merged M3d1 visibility flags and Actual version behavior
- [ ] Explicit operator decision before a **separate** later categorized Save bridge
- [ ] Keep production writes on HOLD

## DECISIONS

The new test and workflow are isolated to this Simple lane; Research, Banking, Categories and shared widget files remain untouched. Revert the test-only PR to roll back. It must not be merged or used as production activation without operator approval.
