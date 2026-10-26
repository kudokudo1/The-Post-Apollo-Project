# Finance Market STOCKS // M14 BACK TO RANGE

## IMPLEMENTATION

M14 adds an explicit **BACK TO RANGE** button to the DAY view **only**
when DAY was opened from a selected, previously loaded RANGE session
using M13's OPEN IN DAY action.

The original RANGE snapshot is temporarily preserved as an isolated
in-memory copy. It is *not* persisted to disk or added to the Market Hub
cache. No market-data provider, API, subprocess, polling timer, trading
permission, FinanceW geometry change or background work is introduced.

### Safe lifecycle

- RANGE → LOAD RANGE → select a real price point → **OPEN IN DAY**:
  retain one bounded original RANGE snapshot and display the derived DAY.
- DAY → **BACK TO RANGE**: validate source identity, issuer, saved
  START/END dates, selected DAY and original EODHD provenance. Restore
  the already loaded RANGE chart immediately with the full original
  sessions, first/last prices, percentage comparison and timestamps.
  **No new request**. The chart point highlight itself resets, matching
  existing M12 selection-clearing behavior.
- The restored RANGE view labels itself
  **RANGE SOURCE // RESTORED FROM MEMORY // NO NEW REQUEST**. Its existing
  DIRECT/HUB and cache timestamps still describe the original retrieval.
  They do **not** imply a fresh provider response.
- After restoration the return ticket is consumed. Only one temporary
  snapshot is retained; it cannot become an unbounded history stack.
- DAY changed manually, issuer changed, RANGE START/END changed, ordinary
  DAY/RANGE mode toggle, explicit DAY/RANGE refresh, or closing the
  Market pane **discards** the saved return ticket.

The separate normal RANGE button retains its M11 behavior. A normal
mode toggle does not silently restore older prices. BACK TO RANGE is
visible only while the original returned-data contract remains valid.

### Why not always use a cache?

M7's optional Market Hub already handles provider-cache TTL, request
coalescing and concurrency. M14's temporary ticket serves a different
purpose: a reversible **UI navigation action** between two views of the
same already-accepted historical dataset. It does not issue another
request or change M7's cache ownership or retention policy.

## HOW TO USE

After PR review/merge and a safe local Quickshell update:

1. Open Finance → Market → STOCKS → RANGE, select date bounds,
   press LOAD RANGE and click an actual plotted closing session.
2. Press **OPEN IN DAY**. You should see that day's original EODHD
   closing price and a derived-from-RANGE explanation.
3. Press **BACK TO RANGE**. Your previous line graph should reappear
   immediately, with the original bounds, sourced prices and timestamps.
4. Change the company or DAY date, or perform a fresh explicit request:
   the saved return should be unavailable. This is deliberate.

No restart or second provider request is needed to use either handoff
button once the existing RANGE snapshot has been loaded.

## VERIFY

Fake-only GitHub CI:

    node tests/finance/test_stock_back_to_range.mjs
    python3 tests/finance/test_stock_back_to_range_contracts.py

Tests cover original ranged trading-session preservation, source
provenance, independent copies, issuer/date/index integrity, stale or
tampered ticket refusal and no-network UI contracts. Existing Finance
M9–M13, SEC EDGAR, optional Market Hub, Polymarket, OSIRIS and Budget
regressions remain in the same CI workflow.

GitHub's source/tests do not simulate the live Qt/Wayland pointer.
Operator acceptance should verify compact and wide FinanceW views,
the immediate no-spinner return, and ticket invalidation.

## WATCH OUT FOR

This restores **previously fetched end-of-day historical data**, not
live quotes or a currently refreshed price. A user can still press the
normal explicit REFRESH RANGE to request new data when desired.

No broader stock entitlements, provider reconfiguration, auto-start,
local installation, Budget writer change or trading order capability.
