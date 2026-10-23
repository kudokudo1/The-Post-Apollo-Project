# FinanceW // Actual read-only connection pilot

Stage D3: an isolated probe with a **manual REFRESH** action in FinanceW's Budget UI.
It does not have Actual mutation methods and does not modify a budget.
It downloads an isolated disposable API copy, reads the requested month,
and deletes its private working directory. No automatic polling or startup.

## Local preflight

1. Keep the Actual desktop app's local sync server running (the setup
   shown in the operator screenshot used `localhost:5007`).
2. Get the **Sync ID** from Actual: budget Settings → Advanced → Sync ID.
   Never copy this ID into tracked Git files.
3. Create a local private password file. Do not paste passwords into chat,
   Git, commands with echoed arguments, or shell history:

   ```bash
   mkdir -p -m 700 ~/.config/financew
   install -m 600 /dev/null ~/.config/financew/actual-password
   read -rs "FINANCE_SECRET?Actual server password: "
   printf '%s' "$FINANCE_SECRET" > ~/.config/financew/actual-password
   unset FINANCE_SECRET
   ```

   The `read` command above uses **zsh** (the user's shell).
   On bash use `read -rsp "Actual server password: " FINANCE_SECRET`.

4. On the host with Node.js 22+ installed, install the package into
   this isolated script directory. `node_modules` is ignored by Git.

   ```bash
   npm install --prefix ~/.config/quickshell/scripts/finance --no-save --package-lock=false
   ```

5. Run manually, using your own Sync ID (no need to share it here):

   ```bash
   export ACTUAL_PASSWORD_FILE="$HOME/.config/financew/actual-password"
   export ACTUAL_SERVER_URL="http://127.0.0.1:5007"
   export ACTUAL_SYNC_ID="REPLACE_WITH_SYNC_ID_FROM_ACTUAL"
   FINANCEW_MONTH=2026-10 node ~/.config/quickshell/scripts/finance/read_budget.mjs
   unset ACTUAL_SYNC_ID ACTUAL_PASSWORD_FILE ACTUAL_SERVER_URL
   ```

   Output is **private financial data**. Do not paste raw JSON into chat
   or save it in this repository. For the fictional test data, verify
   `toBudgetCents: 20000`, checking `balanceCents: 25000`, and
   Spotify `availableCents: 5000`.

## Security and limitations

- Read-only API getters for Budget Month and account balances; no writes,
  sync upload call, bank sync, schedules, or actual account credentials.
- The Actual API still downloads the budget into a temporary local working
  copy as part of its normal operation. That directory is mode 0700 and
  removed on exit; avoid running a real-data budget until local testing passes.
- The connection is loopback HTTP only, not exposed to your network.
- The credential file must be a regular file with mode 0600/0400.
- If data shape differs from the current Actual API, the probe fails
  instead of inventing balances; report the error code, not the raw JSON.
- The package is pinned to `@actual-app/api@26.10.0`. A native
  `better-sqlite3` dependency requires Node.js compatibility.
- FinanceW invokes the script on menu open, month change, or manual REFRESH.
  No startup-time shell read and no persistent network polling.

## Budget screen connection (D3)

FinanceW reads the local budget on menu opening, changing months, or
pressing REFRESH. No persistent polling, automatic account mutations,
or tracked financial data.
The user must first save their known Sync ID privately (zsh):

```zsh
mkdir -p -m 700 "$HOME/.config/financew"
install -m 600 /dev/null "$HOME/.config/financew/actual-sync-id"
read -rs "FINANCE_SYNC_ID?Paste Actual Sync ID: "
printf '%s' "$FINANCE_SYNC_ID" > "$HOME/.config/financew/actual-sync-id"
unset FINANCE_SYNC_ID
printf '\nSync ID saved privately.\n'
```

The existing `actual-password` file remains in the same directory.
Do not paste either value into a chat or repository. The server at
127.0.0.1:5007 must be running to refresh. The snapshot is kept only in
the Quickshell process memory, cleared on failed reads, and not written
to disk by the UI. It shows the current month from Actual, not a sample
or a guarantee of live continuous updates.

## FinanceW D4: month navigation and category spending

Budget → Budget now has previous/next month controls. Selecting a month
invalidates the previous in-memory snapshot and automatically starts or
queues a read for that month. There is no continuous background polling or
financial mutation, and a missing or failed response never shows the last
month's numbers as the selected month's numbers.

Category rows show assigned, net spent (the signed value returned by Actual),
available, an overspent label when the available balance is negative, and a
bounded spending progress indicator for categories with positive assignments.
The bar is only a visual indicator, not a spending-limit enforcement rule.

## FinanceW D5: automatic read on opening and changing months

Opening FinanceW now triggers a read-only refresh of the selected
month without requiring REFRESH. Clicking either month arrow updates the
month label, hides stale figures, and starts a refresh automatically.
REFRESH remains available for retrying or checking recent changes.

If an Actual read is already active, additional month selections do not
launch concurrent API downloads: the latest selected month is queued and
read once the current subprocess exits. Navigation stays responsive even
when Actual is slow. No automatic polling occurs while the window stays
open, and nothing reads at shell startup when FinanceW remains closed.
Failed reads show an error and do not display old budget data.

## FinanceW D6: source-aware header LIVE status + account summary

In the Budget/Budget view, LIVE is shown only when the current month's
authenticated read-only snapshot succeeded **and** the local Actual server
responded to the latest loopback HTTP check. The source check uses a
credential-free `curl --fail --max-time 3` every 15 seconds **only while
FinanceW is open**. A failed read shows ERROR; a failed health check shows
OFFLINE. READING appears while fetching; CHECK before verification. Reserved
or unwired pages show NO FEED, not a fictional LIVE status.

When the source drops after a successful read, the in-memory numbers remain
visible but are clearly labeled CACHED, with the last successful read time.
The indicator is sampled availability, not a continuous authenticated
stream or proof of bank synchronization. Open/refresh/selected-month changes
still authenticate through the actual-app API. Nothing runs while FinanceW
remains closed and no budget records are written.

The Budget page also totals all displayed active, on-budget account balances
and shows their count. It intentionally excludes off-budget/closed accounts,
so this is not a net-worth figure.

## FinanceW D7: transaction preview + header glow

The same isolated read-only Actual snapshot now queries `getPayees()`
and `getTransactions(accountId, start, end)` for the selected month
across all open, on-budget accounts. The Budget scroll area shows the
latest 24 transactions, their date, available payee label or fallback,
account, and signed amount. It also shows the monthly count. There is no
financial mutation, transaction-import operation, or local file persistence.

The upper-right state indicator now uses green LIVE lettering and a
matching text glow. Border and border glow remain Omnitrix green for
normal states (including LIVE, CHECK, READING), switching to the actual
text state color for OFFLINE, ERROR, or NO FEED. The close × uses the
shared ActionButton's own stronger red glow. No independent glyph
shadow sources are added to the close button.

## Standalone local server (not tied to the desktop window)

Actual's desktop app can run its own embedded server on 5007. Closing the
desktop window stops that embedded server, so the FinanceW client loses its
source. A separate, user-managed Actual sync server is required for a
persistent budget source. We stage it on **127.0.0.1:5006** and run it
through a user systemd service. It starts with your login, not the
FinanceW menu and not the desktop Actual app. Server version is pinned to
`@actual-app/sync-server@26.10.0`, matching the FinanceW API family.

**Never substitute an empty new server for the existing budget.** The new
server has its own data directory and password and initially contains no
budget. Do not point FinanceW at it until you export and restore the actual
budget and verify your account and category balances. The installer never
copies, moves, deletes, or migrates desktop app financial records.

1. In your **existing desktop Actual Budget**, choose Settings → Data →
   **Export data** and save the downloaded budget ZIP. Keep it as a backup.
2. With the current budget safely exported, run
   `bash ~/.config/quickshell/scripts/finance/install_standalone_server.sh`
   on the Silverblue HOST, not in a toolbox. It installs under
   `~/.local/share/financew/`, writes a user systemd unit and enables it.
3. Open `http://127.0.0.1:5006` in your browser; set a NEW server password
   if prompted and import the ZIP using the Actual **Import file** workflow.
   Verify the budget's accounts, categories and balances. Ensure the
   imported budget has a Sync ID in Settings → Advanced. Don't reset sync
   on the original desktop installation.
4. Back up the old local FinanceW files `actual-password` and
   `actual-sync-id` to a private directory first. Then update those two
   **private (0600)** files to the NEW server's password and imported
   budget's Sync ID. The old 5007 credentials do not automatically apply
   to 5006.
5. Only after verification, switch the connection using
   `printf 'http://127.0.0.1:5006\\n' > ~/.config/financew/actual-server-url`
   and `chmod 600 ~/.config/financew/actual-server-url`.
   Restart or reopen FinanceW, then verify an authenticated read and a
   LIVE status **with the desktop app closed**.
6. For the rollback, restore the original password and Sync ID private
   files, remove `~/.config/financew/actual-server-url` to fall back to
   5007, and launch your original desktop Actual app. To stop the new
   service: `systemctl --user disable --now financew-actual-server.service`.
   Never delete either server's data just to fix a connection failure.

FinanceW reads `~/.config/financew/actual-server-url` on every read
and health check. **When it is absent**, the existing `127.0.0.1:5007`
behavior stays unchanged. Only valid loopback HTTP URLs are accepted,
and no URL or credential file is committed to Git.

Useful diagnostics: `systemctl --user status financew-actual-server.service`
and `curl -I http://127.0.0.1:5006`. The status alone is not sufficient
to claim authenticated LIVE; the actual budget must be downloaded.

## FinanceW D8 // draft-only transaction staging

Budget → Budget → Transactions now contains a NEW DRAFT action.
It opens an isolated in-memory editor (date, description, positive USD
amount, selected displayed account, expense/income) with fail-closed
date/amount validation and a PREVIEW button. CANCEL, source refresh,
month changes and menu close discard the draft.

The preview is **not a save**. No Actual API mutation methods, financial
writes, file persistence or banking permissions are connected to this
screen. Existing transaction history remains read-only. Before enabling
actual writes we must include stable transaction IDs and account IDs,
explicit mutation authority, review confirmation, durable failure/retry
boundaries, and a tested rollback path. A displayed account name alone
must never be used as a write target.

## FinanceW D9 // guarded transaction create and edit (opt-in, NOT activated)

A reviewed D8 draft can now be explicitly confirmed. The UI offers NEW DRAFT,
PREVIEW then CONFIRM SAVE; eligible history rows offer EDIT. Editing is
limited to the date and amount of a simple, unlinked transaction. The
existing payee is deliberately preserved and the description field is read-only
during edit. Creating a new transaction uses a payee name, a selected stable
account ID, and an uncategorized amount. There is no bank syncing, deleting,
bulk import, or automatic retry.

**IMPORTANT:** GitHub merge does not authorize financial writes. The writer
refuses every request by default. To permit live operations, the operator
must explicitly create the local 0600 file
`~/.config/financew/transaction-writes-enabled` containing exactly
`FINANCEW_TRANSACTION_WRITES_APPROVED`. Do not create it until after a new
Actual data export and a successful local runtime review. The UI itself
cannot create or change this permission. A missing, unsafe, or mismatched
file leaves saving locked.

### Mechanism

- QML sends a reviewed JSON frame over private Node process stdin,
  never over command-line arguments, tracked files, or logs.
- The Node worker downloads the selected budget with the existing
  `actual-password`, `actual-sync-id` and loopback URL credentials.
- Before mutation it checks the active on-budget account, the transaction
  date/amount, duplicate-date-and-amount candidates, and stale IDs. Imported
  bank transactions, transfers, split/parent transactions, and closed or
  off-budget accounts cannot be edited.
- The code records a one-attempt journal in
  `~/.local/state/financew/operations/` (0700 directory, 0600 files).
  The journal has a SHA-256 command hash and outcome but no raw financial
  fields. Each request ID is unique, any repeated ID is blocked, and an
  unresolved attempt blocks every subsequent write. A crash can leave the
  global `.write-lock` behind to block all future writes as well.
- The Actual client uses a disposable data directory and performs exactly
  one `addTransactions` or `updateTransaction` call, then `api.sync()`,
  then a read-back check. Only this path can return committed.
- Post-attempt errors and interrupted operations must be treated as
  **UNCERTAIN**; do not retry. Inspect Actual on the standalone server,
  reconcile the transaction and journal with the operator, and export a
  safe backup before considering a new attempt.
- No LIVE state or saved balance is inferred from an HTTP success alone.

### Verification and recovery gates

The D9 tests exercise only fake API objects and temp HOME directories;
they do not execute real Actual mutations or use personal financial data.
Live QML and end-to-end sync validation remain separate operator acceptance
gates. Leaving the activation file absent is the safe rollback: FinanceW
continues reading the budget and can preview edits, but cannot mutate data.
Never blindly delete a recovery journal or `.write-lock`: their existence
can mean a write happened even if the widget did not receive confirmation.


## FinanceW D10 // Private local saved drafts (not Actual transactions)

Budget → Budget → Transactions has a SAVE DRAFT action separate from the
existing PREVIEW → CONFIRM SAVE operation. SAVE DRAFT persists incomplete
new-transaction text locally; it does not call Actual, authorize budget writes,
create transactions, or reconcile bank data. SAVE DRAFT works while the real
transaction writer remains WRITES LOCKED. Existing Actual transaction EDIT
is not a local draft edit.

Saved drafts appear under SAVED DRAFTS for the selected budget source and
month. OPEN restores one to the editor, UPDATE DRAFT saves revisions,
and DELETE → CONFIRM removes the chosen local draft. Dates, amounts, or
descriptions may be unfinished when saved. PREVIEW / CONFIRM SAVE still require
complete validated data and the separate operator write gate.

Local storage: ~/.local/state/financew/drafts/index.json, directory 0700,
file 0600, atomic replacement on changes. The content is plain JSON, not
encrypted; it may contain payees, amounts, descriptions, and account IDs.
Do not commit or share this file. The backend checks permissions, rejects
symlinks, version mismatch, malformed data, stale revisions, and cross-budget
operations. Maximum 50 total saved drafts. The frontend only presents drafts
matching the currently authenticated budget source and selected month. Reload
the Budget page after changing the Actual source to see the appropriate drafts.
If an account is no longer available, the record cannot be reopened; the data
is preserved for manual review rather than silently redirected.

A saved draft is never proof that Actual was changed. After an explicitly
authorized successful Actual transaction, check the ledger before manually
deleting the corresponding draft. In particular, an Actual UNCERTAIN response
still requires manual recovery and never automatic retry.

Back up the private JSON file before troubleshooting corrupt data. Avoid
changing permissions or deleting the file to hide an error. The D10 tests use
isolated disposable HOME directories; they never read or write actual budgets.


## FinanceW D11 // Category allocation preview (read-only)

Budget → Budget → Categories now offers **ALLOCATE** for each category.
It opens a non-persistent **PROPOSED ALLOCATION** editor that performs
pure calculations from the most recent authenticated Actual snapshot.
PREVIEW shows the existing versus proposed monthly category amount,
projected available balance, and remaining To Budget. It warns if the
proposal would over-allocate the month's unallocated funds, or if the
category would remain overspent.

The preview is an **absolute proposed category allocation**, not a payment
or a transfer. Example: increasing SET from $200 to $250 uses $50 of
To Budget and adds $50 to category available. Reducing SET frees funds
but can leave a category overspent. Negative target allocations are not
supported in this first UI slice.

**D11 has no save or apply action.** It does not call Actual Budget's
mutating API, does not use the transaction writer, does not touch financial
authorization files, and does not persist the proposal. The preview is
discarded when its source snapshot refreshes, the selected category
changes, or the user presses CANCEL. ACTUAL remains authoritative.

Verify D11 using source contracts and pure fictional-data arithmetic tests.
Runtime rendering and later guarded allocation writes are separate milestones.


## FinanceW D12a // Allocation policy foundation (NOT connected to Actual)

A separate guarded budget-allocation **policy** now exists at
scripts/finance/allocation_guard.mjs. It is intentionally **not invoked** by
FinanceW, not imported by a local process or QML, and cannot activate itself.
This development batch is a fake-data-only foundation for later guarded
category allocation saving.

The command is an **absolute** category monthly amount in integer cents,
bound to a specific budget source fingerprint, selected month, stable category
ID, unique request ID, and the original category/To Budget values observed
by the operator. Reject malformed data, extra fields, missing/duplicate
categories, stale amounts, unchanged proposals, changes that spend more
unallocated funds than are available, and category balances that would remain
negative. A live allocation's permission and durable journal remain a
**separate later implementation**, not inherited from D9 transaction writes.

In a future separately authorized execution adapter, the policy will first
read Actual's current month, verify these invariants, call the adapter's
durable recordAttempt, perform at most one
setBudgetAmount(month,categoryId,amountCents), sync, and verify a fresh
readback. Once recordAttempt occurs, all errors are **UNCERTAIN** until
manually reconciled; no automatic retries. This batch does not provision a
write permission file, does not enable UI APPLY, and does not access the
operator's budget. Its tests inject fictional API methods and never import
Actual itself.

Next: establish a disposable real Actual test for the specific
setBudgetAmount semantics, then design a separate local authorization and
recovery gate. Keep D11 PREVIEW-only until that stage is accepted.


## FinanceW D12b // Real Actual disposable-server allocation test

A GitHub Actions **CI-only** script exercises pinned Actual API/server version
26.10.0 with a fictional budget, account, category group, expense category,
and income entry. It tests D12's pure allocation guard against the real
`getBudgetMonth`, `setBudgetAmount`, and `sync` methods. A second
authenticated API session downloads the fictional uploaded budget and
verifies the changed category amount/balance and To Budget. Stale budget
state is refused without invoking the mutation API.

This test uses a temporary isolated server on `127.0.0.1:5006`, hardcoded
fictional credentials, temp client directories, and an injected
`recordAttempt` counting spy **only**. It never reads local operator
credentials or the local finance operations journal. It does **not**
establish production write safety or an operator-authorized live writer.

No category allocation APPLY button, local write authorization, persistent
journal integration, or real-budget mutations are introduced in D12b.
Those remain D12c/D12d and separately authorized stages.


## FinanceW D12c // Separate guarded category-allocation writer

The Node writer at `scripts/finance/write_allocation.mjs` is committed
as a **disconnected backend**. No Quickshell caller or APPLY button was
added. It is not an extension of the D9 transaction permission: it checks
for a *different* private mode-0600 operator authorization file named
`~/.config/financew/allocation-writes-enabled` with the exact intended
marker `FINANCEW_ALLOCATION_WRITES_APPROVED`. This file is **not**
provisioned by installation, Git pulls or FinanceW.

The writer takes a single framed JSON command from **stdin**, never argv,
and requires a matching source fingerprint, an exact month/category ID,
original budget figures, and a new 32-character hexadecimal request ID.
It rereads Actual's current month before considering a mutation.

Before any call to Actual's `setBudgetAmount`, the writer:
1. Acquires the **same** exclusive `~/.local/state/financew/operations/.write-lock`
   used by D9. This prevents concurrent transaction and allocation writes.
2. Refuses if any previous finance operation journal is unfinished, corrupt
   or unsafe. It never automatically reconciles or retries it.
3. Writes, flushes, and syncs a private
   `allocation-<requestId>.json` attempt journal. The receipt stores
   an operation hash and state, never a category name or money amount.
4. Calls the guarded policy once, Actual sync once, and verifies fresh
   readback before committing the receipt. After attempt recording, any
   failure is **UNCERTAIN**, leaving an attempted receipt behind and
   blocking both allocation and transaction writers until manual review.

This is **not live activation**. The D12c GitHub tests inject only
fictional Actual APIs in isolated temporary HOME directories, including
mutations that fail after being applied. Test coverage verifies the
independent permission gate, stale source refusal, shared lock, journal
privacy, stale preflight, sync uncertainty, and mutual recovery barriers.
Never create the authorization file merely to test the interface.

The next step is to validate the complete guarded writer against a
disposable **real** Actual server, including controlled failure recovery,
before adding any D12d UI controls or considering a real-budget activation.


## FinanceW D12d // Guarded category allocation confirmation UI

**This UI does not activate money writes.** Finance → Budget → Budget →
CATEGORIES → ALLOCATE keeps the existing safe PREVIEW. A valid nonzero
proposal that does not over-allocate or leave a category overspent may
advance to **ARM SAVE → CONFIRM SAVE**. This explicit action submits one
command to the separate D12c writer via process stdin. With the separate
\`allocation-writes-enabled\` operator permit absent, the writer refuses
with **ALLOCATION WRITES LOCKED // OPERATOR ACTIVATION REQUIRED**.
No authorization files or credentials are created or displayed by the widget.

The proposal is bound to the authenticated budget fingerprint, month,
category ID, original allocation, category balance and To Budget value.
Any source refresh/change or change to the input clears the approval
state. An eligible command carries one request ID, with no automatic
retry after submission. The D12c writer independently downloads fresh
Actual data, checks the original values, journal and shared global lock,
then blocks stale or unsafe writes before any Actual mutation.

Writer outcomes surface as COMMITTED, REFUSED, or UNCERTAIN. Any process
failure or missing status is conservatively labeled UNCERTAIN.
UNCERTAIN suppresses further allocation submissions until manual
reconciliation and a future recovery procedure; restarting Quickshell
does not clear an attempted journal. On successful save, the pane
closes and the read-only budget snapshot refreshes.

Acceptance scope: source contracts and GitHub CI, then operator
Quickshell UI verification with the writer permit still absent.
Do **not** create that permit as part of the UI test. Actual live-budget
activation, explicit backup review and crash-recovery acceptance remain
separate operator decisions.


## FinanceW D13 // Read-only CHECK WRITE LOCK + funding readiness

Finance → Budget → Budget → CATEGORIES now includes **CHECK WRITE LOCK**.
This is a **read-only status probe** of the allocation permission file,
not an attempt to write a transaction or category allocation. It does not
read Actual credentials, connect to Actual, create or change a file, or
change the D9/D12c authorization rules. The probe only runs after the
button is clicked, so its message must be treated as a point-in-time
status, not a promise about a future operation.

Statuses:
- **WRITES LOCKED // NO ALLOCATION PERMIT**: no local allocation
  authorization marker was found.
- **PERMIT DETECTED // DO NOT TEST LIVE WRITES**: the exact marker
  appears in a private regular file. This is **not proof the system
  is safe or that the budget is eligible**; D12c independently checks.
- **UNSAFE PERMISSION FILE // REVIEW REQUIRED**: malformed marker,
  loose file permissions or symlink; no activation is recommended.
- **LOCK CHECK UNAVAILABLE // NO SAFETY CLAIM**: the probe failed.

A separate **FUNDING** line below To Budget distinguishes available-to-
allocate money from account balances. With zero or negative To Budget,
it points the operator to review properly entered and categorized income,
opening balances, or earlier allocations in Actual. **An account balance
does not automatically equal money available to budget.** The status
never creates money, does not auto-allocate, and does not authorize
budget writes.

Funding follow-up (NOT implemented here): read-only reconciliation of
starting balances and income categorization, then preview and separately
authorized operations that are supported by Actual. Preserve the user's
actual accounts and never fabricate a balance to unlock a button.


## FinanceW D14 // Monthly Funding Review (READ ONLY)

Under Finance → Budget → Budget, use **REVIEW FUNDING** in the scrollable
Budget area. It shows selected-month income-category activity as reported by
Actual's budget month, a count and total of positive uncategorized transactions
in active on-budget accounts, and warnings about what these numbers cannot
prove. It reuses the authenticated snapshot already loaded by FinanceW:
no extra server queries, no permission changes and no writer or APPLY action.

- **Income category activity** is the signed sum of Actual's income-group
  category \`spent\` fields, not a claim of new funds available to allocate.
- **Positive uncategorized items** may be income, refunds, adjustments or
  transfers. Ordinary transfers and split parents/children are excluded
  when Actual identifies them; the operator must review ambiguous cases.
- **Opening balances** are deliberately marked **NOT VERIFIED**. A single
  monthly snapshot cannot prove historical opening balances.
- **To Budget** remains exactly the value reported by Actual. It is never
  recomputed from account balances or uncategorized positive transactions.

The same existing read-only Actual API getters supply all data. The normalized
summary contains **aggregate cents and counts only**, never new transaction
descriptions, raw sync IDs, account secrets or category writes.
If the month/source changes, the review closes and cannot display stale data.
Actual remains the authoritative place to inspect and correct income
categorization or starting balances, subject to the separate authorization
rules for any future FinanceW editing tools.

Next potential work: opening-balance historical inspection and a guarded
income categorization preview. Neither is implemented or activated by D14.


### D14 compatibility: optional Actual income fields

Actual 26.10.0 may omit `spent` on income category entries. Missing data
is represented as **NOT REPORTED BY ACTUAL** (null), never converted into
zero, and must never invalidate the rest of the Budget snapshot. When Actual
supplies integer `totalIncome` in its monthly budget, the separate **MONTHLY
INCOME (ACTUAL)** line displays that number; it does not imply the amount
is available to allocate. Opening balances and unallocated funds retain their
independent source and verification status. This is exercised in both
fictional unit tests and the real disposable Actual-server read-only probes.


## FinanceW D15 // On-demand historical opening-balance inspection

Under **Budget → REVIEW FUNDING → INSPECT OPENING BALANCES**, an explicit
click downloads a temporary private read-only Actual copy and calls only
`getAccounts`, `getCategories`, and `getTransactions` for historical
transactions between **1900-01-01** and the selected month's end.

It reports each active on-budget account's first recorded date and amount,
transaction count, and any entries linked to a category named **Starting
Balance** or **Starting Balances** (when available). Those entries are
**candidates**, not verified opening balances: imported data, history gaps,
transfers, category naming, and external bank records may differ. Missing
candidates never imply zero starting balance. The view never computes funds
available to budget from those transactions.

The scan is deliberately **manual**: no scheduled lookback, polling, or new
budget modification capability. It rejects more than 30 accounts or 10,000
history rows in any account rather than silently truncating findings. Large
budgets should be inspected through Actual itself if the bounded scan refuses.
Sensitive transaction payees and notes are omitted from results. The scan's
local API cache is a disposable mode-0700 directory and is cleaned afterward.
The report clears if the current budget fingerprint or month changes.

For a true opening-balance reconciliation, compare original bank statements
and historical Actual transactions. This feature **cannot validate external
balances** and does not authorize real transactions or allocation writes.


## FinanceW D16 // Read-only income categorization preview

Inside **Budget → REVIEW FUNDING**, open **REVIEW INCOMING** to inspect the
selected month's positive, currently uncategorized transactions. Identifiable
transfers, split parent/child records, categorized deposits and expenses are
excluded. A positive amount is *only a candidate to investigate*, not proof
of income. Entries show their date, account and amount without raw payee
descriptions.

Select **REVIEW** for a candidate, then select a visible Actual income
category to preview **UNCATEGORIZED → category**. This selection is
**not saved, persisted, or transmitted**. The UI has no write action and
does not calculate a hypothetical new To Budget. Actual may allocate the
effect to different months or require additional reconciliation.

At most 12 of the newest candidates are displayed. When more exist,
the UI explicitly states the displayed/total count and directs the user
to Actual for the remainder. If over 24 income categories exist, the UI
fails closed for target selection rather than presenting an incomplete
category set. Category details missing from Actual do not crash the
Budget snapshot. Both selection and preview clear on snapshot changes.

D16 includes fake-data tests, source contracts and real disposable Actual
integration in CI. No new API calls are added to the regular Budget read,
no credentials or raw sync IDs are exposed in the review and financial
writes remain separately authorization-locked.

Next milestones: D16 local Quickshell UI acceptance and guided legitimate
starting-balance/income setup. Editing a real transaction's category must
be designed, audited and authorized separately.


## FinanceW D17a // Guided Funding Setup Preview (NO WRITES)

Budget → REVIEW FUNDING → **GUIDED FUNDING SETUP** adds two guarded,
read-only planning paths, **OPENING BALANCE** and **INCOME**. This
first-stage UI deliberately does not expose SAVE, WRITE, APPLY, a
payment operation, an Actual mutation API or local persistence.

For OPENING BALANCE, choose an existing on-budget account, enter a
reference date and positive USD amount, then PREVIEW SETUP. The plan
reminds the user that this is an **existing account** and its opening
balance must be compared with historical transactions and original bank
statements before making any adjustment. Entered numbers are *not*
treated as a new transaction, verified starting balance, or added funds.

For INCOME, choose an existing on-budget account, a date in the selected
month, a positive amount and an existing income category from the
authenticated read-only snapshot. PREVIEW SETUP shows the proposed
account/date/amount/category, without changing or creating any Actual
transaction. The relevant income category must exist, and a truncated
category list refuses a proposal.

Both previews are bound to the budget's source fingerprint and selected
month. Harmless snapshot refreshes invalidate the preview but preserve
the unsaved inputs; source/month changes close the editor. Input dates
must be actual calendar dates, monetary amounts must be positive integer
cents, and the selected account must exist uniquely in the snapshot.
A read-only account balance is shown for context but **To Budget after
is always UNKNOWN**, never invented from a positive amount. No local
financial state, settings file, or authorization is written.

D17b onward: plan guarded data entry on a **disposable Actual budget**,
including reconciliation of pre-existing opening transactions, duplicate
detection, and explicit operator approval. Do not enable real-budget
funding writes based on a preview or a passed CI test.


## FinanceW D17 input controls // Calendar & USD normalization

FinanceW's three user-editable amount fields (transaction drafts/edits,
category allocation and guided funding) now display a fixed dollar glyph
outside the editable number. On leaving a money input, whole dollars
normalize to two decimal digits: \`25\` → \`25.00\`; \`25.5\` → \`25.50\`.
Backend amount semantics, cents limits, draft permissions and save locks
are unchanged. Invalid money strings are not converted or submitted.

FinanceW's two editable date fields (transaction drafts/edits and guided
funding) are MONTH / DAY / YEAR numeric segments. Each has a text editor
and up/down pointer controls; focused segments also accept keyboard
Up/Down. A valid date is internally emitted in Actual's existing ISO
YYYY-MM-DD format. Impossible dates are refused, while month/year changes
clamp the day to the shorter month (including February leap years).
Day stepping traverses calendar boundaries. Empty draft dates can be
restored via a pointer step or valid typed segment using the selected
month's first day as a starting reference.

These editors reuse the established TaskDateSegment interaction, and
are *not* connected to Actual API, local storage, or write activation.
This is an input ergonomics change only. Continue to use preview and the
separately controlled write gates; no real financial authorization changed.


## FinanceW D17b // Disposable funding entry & recovery rehearsal

**Scope: CI-only. No new FinanceW SAVE action, writer or authorization file.**
D17b extends the pinned Actual 26.10.0 disposable-server integration tests
with separate realistic funding pathways:

1. **Existing-account opening balance**: refuse automatic creation, because
   the account may already contain imported or historical transactions.
   Original bank statements and existing Actual ledger must be reconciled
   before any adjustment. This UI is still a plan, not a real account edit.
2. **New account initial balance**: test the documented
   \`createAccount(account, initialBalance)\` API using a *fictional new account*;
   require an absent account name before creation and verify its initial
   balance in an independently downloaded disposable budget.
   This operation does not accept a historical reference date. Therefore
   the D17a date field is NOT a supported write parameter for opening a
   new account, and D17a MUST remain preview-only.
3. **Categorized income entry**: test \`addTransactions\` using a stable
   request identity, a known active on-budget account, an Actual income
   category and positive integer cents. Preflight checks selected-month
   date, live category membership and duplicate-looking ledger records.

The test-only mutation harness is
\`tests/finance/fixtures/funding_disposable_rehearsal.mjs\`.
It refuses execution without **CI=true, GITHUB_ACTIONS=true,
FINANCEW_DISPOSABLE_TEST=yes**. It has no launch path from FinanceW.
It verifies **record-attempt before mutation** and duplicate refusal.
If sync fails, the attempt is **uncertain**; inspection reports
\`observed\`, \`not-seen\`, or \`ambiguous\`. *Even not-seen never authorizes
an automatic retry*: manual investigation and durable journaling are
requirements for the future D17c writer. Independent Actual readback
confirms only fictional test changes.

All existing write-lock files remain unchanged and no additional
credentials or private financial data are added to GitHub. D17b acceptance
is CI source and disposable-budget integration only; it is not operator
approval for new-account creation or live income transactions.
