# FinanceW FP1b // Local goals and recurring-cost plans

This step adds **local operator-entered plans**, not verified bank accounts
or authorization to view another person's finances. It works without
Connections, Social, Actual Budget or a finance provider.

## How to use after approved merge/local update
Finance → STRATEGIES → PLANS → choose MINE / SHARED / MOM / GRANNY / FAMILY.
Choose SAVINGS GOALS or MONTHLY COSTS. Enter a title and manual amounts,
then explicitly SAVE. For removal click DELETE, then CONFIRM. Data is
loaded only while the Strategies PLANS view is active. REFRESH reloads
the selected context.

Goals capture manual target, amount already set aside (unverified), and
planned monthly contribution. A descriptive months-to-go estimate is
derived without growth, interest or market assumptions. Monthly costs
capture a labeled planned recurring amount, not a bank transaction.

## Storage and safeguards
- Files: ~/.local/share/post-apollo/finance/household-plans/<context>.json
  (or the matching XDG_DATA_HOME path). Folder 0700, files 0600.
- Each logical context is isolated by a strict allowed name, revision,
  separate file, whole-document validation and nonblocking advisory lock.
- Writes use temporary files, file/dir fsync and atomic replace.
- Mismatched revisions, malformed data, symlinks, untrusted modes and
  invalid amounts fail closed without silent reset or overwrite.
- The read path creates no directory, and no initial financial values
  are fabricated. There is no polling, bank sync, connection grant,
  automatic write, credential reading, or provider request.
- **Same Linux UID can access ALL five contexts**. These are operator
  labels and are NOT enforced multi-person privacy, shared-login access
  or authenticated membership. Do not put another person's sensitive
  information there without appropriate permission and trust in the
  local device/user.
- Files are local plaintext, not encrypted at rest. Backup and encrypted
  permission-bound sharing require separate reviewed milestones.

## Verification
python3 tests/finance/test_household_plan_store.py
python3 tests/finance/test_finance_household_plans_contracts.py
Existing FinanceW FP1a and stock/Actual contracts also run in CI.
Native compact/fullscreen keyboard, pointer, saved persistence and
cross-context switching need operator-host acceptance.

## Ownership
New FinanceW-only files and a bounded Strategies mount change.
No Connections/Identity/Social/Actual datastore migrations or direct
bank writer modifications. This is not Hospital-registered state.
