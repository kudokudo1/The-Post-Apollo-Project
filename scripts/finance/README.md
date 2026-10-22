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
