# FinanceW Simple M3d4 // disposable process SIGKILL recovery matrix

**PATIENT:** The-Post-Apollo-Project
**ROOM:** FinanceW Simple/Budget
**STAFF:** Successor Simple DOC, external Hospital-compatible only
**PRODUCTION FINANCIAL WRITES:** HARD HOLD
**STATUS:** Source-only isolated draft CI test, not operator activation/acceptance

## IMPLEMENTATION

Two new test fixtures exercise the existing M3b categorized expense writer using pinned Actual API/sync-server 26.10.0. No production source, Quickshell, financial permit, lock logic, M3b policy, Budget reader, or shared UI file was changed.

A CI-only ESM loader pauses the in-memory policy module at exactly one of two checkpoints:

- **After ATTEMPTED:** After the production CLI's recordAttempt promise has returned, meaning journal and directory fsync are complete, and before the first Actual add.
- **After add:** After a real Actual addTransactions call with accepted acknowledgement, but before sync.

The parent starts the actual production CLI with this test-only loader and a temporary fictional HOME, waits for a private mode-0600 checkpoint barrier, checks the private ATTEMPTED journal and global .write-lock, delivers SIGKILL, and verifies the records survived process death.

A later invocation is refused by the stale lock. In a separate purely disposable verification, the test deliberately removes **only the temporary stale lock** (never the ATTEMPTED journal), then verifies that both the production M3b and D9 CLIs still refuse with recovery-needed. This lock deletion is **NOT a proposed live recovery procedure**. Production recovery requires independent investigation and operator authorization. No journal deletion, clearing, or automatic retry is part of the production writer.

Independent fresh Actual clients inspect fictional transactions. The after-attempt case must have zero matching remote transactions. The after-add case remains intentionally **uncertain** whether an unsynced transaction reached remote storage. Neither presence nor absence authorizes retry.

## VERIFY

A GitHub Actions workflow with read-only repository permission, pinned Node 22 and Actual 26.10.0, and the environment triple (GITHUB_ACTIONS/CI/FINANCEW_DISPOSABLE_TEST) runs source-isolation assertions, syntax checks, and the disposable server/real-process matrix. Require a successful exact-head CI job and raw FINANCEW_M3D4_SIGKILL_PASS marker before reporting PASS.

The test uses an **instrumented in-memory guard** for deterministic pauses, NOT byte-identical uninstrumented policy execution. This proves filesystem/journal/lock handling of the actual CLI against SIGKILL at those checkpoints, not that every uninstrumented crash window or power-loss/disk-failure mode is covered.

## WATCH OUT FOR

- **Nurse 2 financial-security review of M3b #2356 remains outstanding.** Source merge, green CI, and this crash test do not authorize production financial writes.
- Test-only credentials and permits are inside temporary CI HOME. No real user data, live Actual endpoint, desktop, or operator-owned permit is accessed.
- Port 5006 is checked for availability and used only by a private test server. No remote network services.
- The category selector's source 5007 default versus strict M3b write 5006 remains a separate source compatibility question.
- Banking storage, Categories stale assertion, Research, Strategies, Market and M2b Move Money are different lanes. No cross-worker code changed.

## CHECKLIST / NEXT

1. Verify exact-head CI and raw logs for both checkpoints.
2. Request independent Nurse 2 evaluation of M3b lock, source, durable journal, admission, receipt and ambiguous outcomes, including instrumentation limitations.
3. Operator explicitly accepts any future guarded Save wiring and separate production permit activation. No automatic merge or live financial mutation.

## DECISIONS

No user-local changes. Test-only rollback reverts these four new files. Preserve unresolved real attempts until an authorized investigation resolves them.
