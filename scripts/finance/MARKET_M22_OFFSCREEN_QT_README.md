# FinanceW Market M22 // Actual QML quota-pane offscreen acceptance gate

## IMPLEMENTATION

Adds a headless Qt smoke gate that mounts the **real**
`FinanceMarketQuotaStatusPane.qml` and its **real**
`FinanceMarketQuotaStatusService.qml`, using the project's existing
offscreen PySide6 acceptance approach. This is a test/instrumentation
milestone, **not a new quota or provider operation**.

Production changes are limited to stable `objectName` values on the existing
pane, service, refresh/back ActionButtons and reservation labels so the
test can address real Qt objects. No FinanceW active menu logic, provider
client, quota storage reader/writer, policy, account state or window
activation is modified.

Test-only `Quickshell` and `Quickshell.Io` QML module stubs are built in
a disposable `TemporaryDirectory` during CI. The mock `Process.exec`
rejects any command except the existing **local-only M21 status** script
shape. It records the requested arguments in memory and returns synthetic
read-only JSON fixtures; it **never spawns a process**. The test never opens
the real quota SQLite DB, sends market/provider requests, reads credentials
or touches the operator's host.

## HOW TO USE

Developer/offscreen CI verification:

`python tests/finance/test_finance_market_m22_qt_runtime.py`

Requires `PySide6>=6.10,<6.12` and a headless Qt runtime. The new
`financew-market-m22-offscreen-qt.yml` GitHub Action installs these only in
its disposable runner. **Do not install test requirements, restart
Quickshell, or deploy this branch on the operator's live host without
separate approval.**

After approved native host deployment, ordinary UI remains:
Finance → MARKET → STOCKS → **QUOTA STATUS** → REFRESH LOCAL STATUS /
BACK TO STOCKS.

## VERIFY

The actual QML pane/service headless test checks:

- service does not run before opening; opening triggers exactly one
  local-only status request, and repeated rendering/resizing does not poll
- valid 3/20 EODHD and 9/25 Alpha local reservations render; refresh to
  capped 20/20 and 25/25 renders, invoking the **real** ActionButton signal
- both providers display UNKNOWN for missing, busy, malformed, invalid
  counts and tool-error fixtures, never a synthetic 0
- compact and wide pane widths work while preserving both provider rows
- closing discards the old snapshot; re-opening runs one fresh local read
- **BACK TO STOCKS** emits the real pane's exitRequested signal
- only the exact M21 Python status command is requested by the service;
  the fake Process cannot make a network call or use the host filesystem.

The M21 Python SQLite permission/race/no-write tests and M20 writer
regression remain in the existing FinanceW Market gate. This PR does not
replace those tests.

## WATCH OUT FOR

Offscreen Qt with fake process transport verifies real QML binding/layout
and command dispatch, **not native Quickshell** or Linux production
permissions. No test can infer actual provider-account quota from the
local reader. The offscreen test uses synthetic fixtures only; checking
native user quotas without spending a provider call requires separate,
operator-approved host acceptance.

M20's protected-file trust and concurrent-writer safety are a security
boundary: independent Nurse 2 review remains appropriate there. Ordinary
M22 UI/test instrumentation does not require a separate reviewer unless
that review identifies new security/coordination scope.

## NEXT

Once source CI succeeds, keep PR draft until operator approves merge.
Perform real-host GUI/SQLite/no-network verification **only after explicit
host mutation/testing authorization**. Retain production HOLD until live
acceptance.

**NO LOCAL HOST MUTATION // NO REAL PROVIDER NETWORK // DRAFT ONLY.**
