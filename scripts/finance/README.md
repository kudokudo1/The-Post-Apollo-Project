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
