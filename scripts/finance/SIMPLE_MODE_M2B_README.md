# FinanceW Simple M2b // Dormant protected two-envelope writer

## Scope and state

**Status: SOURCE-ONLY / DISABLED BY DEFAULT / NOT MOUNTED.**

M1 [#2305](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2305)
and M2a [#2310](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2310)
are merged. M1's operator visual check was reported PASS. M2a is still an
**unmounted preview**: there is no button in the running Budget menu.

M2b adds:
- `scripts/finance/envelope_move_guard.mjs`: pure strict
  `validateEnvelopeMoveCommand`, stale source/month/two-category
  `preflightEnvelopeMove`, and injectable execution policy.
- `scripts/finance/write_envelope_move.mjs`: standalone, dormant,
  **separately permitted** CLI using the shared FinanceW writer lock and
  operation journal. Nothing in FinanceW invokes or installs this CLI.
- Fictional policy/CLI tests including interrupted first-only and
  post-sync failures. No network, Actual credentials or live budget
  are accessed by these tests.

## Mechanism: budget assignment, not bank transfer

Moving, for example, $25.50 from Groceries to Fuel adjusts exactly two
expense-category **monthly assigned** amounts, which in turn change
the two category **available** balances. It does not move bank cash,
change account balances, create a spending transaction or change total
unassigned ("TO BUDGET") funds.

The request binds 12 exact fields:

`action`, `requestId`, `sourceKey`, `month`,
`fromCategoryId`, `toCategoryId`, `moveCents`,
`expectedFromBudgetedCents`, `expectedFromAvailableCents`,
`expectedToBudgetedCents`, `expectedToAvailableCents`,
`expectedToBudgetCents`.

All money is integer cents. The writer independently rereads Actual and
refuses stale, ambiguous, malformed, duplicate-ID, insufficient source
funds, source-assignment-underflow, self-moves or amount overflows
**before** recording an attempted mutation.

## Permission and critical non-atomic boundary

**Never create a permit as part of this PR or CI.** A future separately
approved operator action would be required to provision a **private file**
named `~/.config/financew/envelope-moves-enabled`, with content
`FINANCEW_ENVELOPE_MOVES_APPROVED`, only after independent security
review and operator production approval.

This permit is intentionally **distinct** from
`allocation-writes-enabled`, transaction write permission and other
finance capabilities. Merely merging this code **does not activate it**.

The existing Actual API exposes two sequential
`setBudgetAmount(month, id, target)` operations here. **This is NOT an
atomic DB transaction**. It is one *guarded* request with two API
mutations and a single sync. After the first attempted mutation, a
crash/error can leave only the source envelope changed. Do not retry,
roll back automatically or claim that both writes either happen or
neither happens.

To contain that failure:
1. Validate source URL (exact localhost 5006), private credentials and
   sourceKey under the **shared** `~/.local/state/financew/operations`
   lock `.write-lock`.
2. Refuse unresolved or malformed prior finance operation journals.
   The request ID is one-use, including prior other FinanceW operations.
3. Before the first `setBudgetAmount`, durably create an ATTEMPTED
   journal, fsync the file **and containing directory**.
4. Call the two assignments sequentially, sync once, reread both
   exact category identities and TO BUDGET, and compare both monthly
   budgeted and available amounts with the preflight expectation.
5. Only after verified matching readback may a COMMITTED receipt replace
   ATTEMPTED. An interruption or mismatch after the recorded attempt
   leaves an attempted/uncertain journal. Future finance writes must
   refuse until a human independently reconciles the real Actual
   budget and follows an approved recovery process.

The caller must not infer success from an API return or CLI exit code
alone; the receipt is evidence, not permission for a second operation.

**No automatic journal cleanup** is authorized here. Do not delete or
edit `.write-lock` or an ATTEMPTED record just to unblock the UI.

## Test and acceptance plan

The M2b CI suite uses an injected fictional Actual stub; it deliberately
injects a failure **after only the first allocation**, a sync error,
and a mismatched readback. It confirms that the prior single-category
writer refuses new writes when an envelope-move ATTEMPTED journal exists.

Locally on a disposable test checkout or in GitHub CI:

```bash
node --test tests/finance/test_envelope_move_guard_m2b.mjs
node --test tests/finance/test_envelope_move_cli_recovery_m2b.mjs
python3 -B tests/finance/test_envelope_move_m2b_contracts.py
```

**Next required gates:** independent Nurse 2/security review of new
money-mutating boundary; disposable *real Actual API* test only after
approval and in an isolated fictional budget; M2c controlled root
integration; operator permission/production activation approval;
real desktop acceptance. Headless/fictional CI is not a production
acceptance or evidence that two API calls are atomic.

## Ownership, handoff and rollback

This PR adds only isolated new policy, CLI, fictional tests and workflow,
plus this documentation. Existing `FinanceW.qml`, the M2a read-only
preview, old allocation/transaction writers, permits, journals,
credentials and local machine are untouched.

**Rollback before activation:** drop or revert the PR. Since no UI
invokes it and no permit is provisioned, removing the new files cannot
change live budget records.

**Unresolved:** Actual database transaction-level atomicity and whether
a sanctioned single transaction API can cover both allocations; never
assume or promise it. Keep an explicit UNKNOWN/UNCERTAIN partial-write
recovery state until verified.
