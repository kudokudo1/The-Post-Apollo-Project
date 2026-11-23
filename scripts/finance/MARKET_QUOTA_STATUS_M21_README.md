# FinanceW Market M21 // Read-only local free-provider quota status

## IMPLEMENTATION

Adds **Finance → MARKET → STOCKS → QUOTA STATUS** without requiring a
stock search, a vendor API key, or a price-provider request.

The status screen shows two **Post-Apollo local reservation** totals for
the existing M20 provider budget:

| Source | M20 local attempt ceiling | Account usage visibility |
| --- | ---: | --- |
| EODHD global price reader | 20 / UTC day | NOT OBSERVED |
| Alpha Vantage global price reader | 25 / UTC day | NOT OBSERVED |

**It is not a provider-account balance,** and the status screen cannot
reset or delete any counters. Legacy six-company EODHD/Market Hub, other
applications, remote hosts and browser/API calls are outside M20 coverage.

## Exact read-only mechanism

- New `scripts/finance/market_quota_status.py status` accepts **no caller
  file path**, account, ticker, API key, token or provider operation.
- It walks the exact M20
  `~/.local/share/post-apollo/finance-market/` hierarchy using existing
  read-only directory file descriptors, `O_NOFOLLOW`, ownership and mode
  guards. **No mkdir, chmod, deletion or SQLite file-creation path** is
  present.
- It opens the **existing** M20 SQLite file with `O_RDONLY|O_NOFOLLOW`,
  checks user ownership, one hard link, private mode and a 2 MiB maximum.
  A nonblocking POSIX shared lock avoids reading during an active writer.
- A sibling rollback journal, WAL or shared-memory file is treated as
  unavailable rather than repaired, truncated or discarded. SQLite format
  and rollback-journal mode are checked before reading bytes.
- The bounded, stable byte snapshot is opened via SQLite's **in-memory**
  `deserialize` method, followed by read-only SELECT on the expected
  M20 schema. No file-backed SQLite connection is used, therefore no
  `-journal`, `-wal` or `-shm` file is created or modified by the
  reader.
- The only output is source/UTC-day/read-only status for EODHD and Alpha
  Vantage. An existing, valid DB with no reservation row for a provider on
  that UTC day accurately shows **0 Post-Apollo local reservations**.
  If the DB/directory is missing, corrupt, busy, unsafe or unreadable,
  the status is **UNKNOWN / NOT INITIALIZED / UNAVAILABLE**, **never a
  falsely inferred zero**.
- New `FinanceMarketQuotaStatusService.qml` runs only this local Python
  script, once on opening and manually on **REFRESH LOCAL STATUS**. It
  checks exact schema, source, UTC date, provider order, caps, read-only
  claims and explicit UNKNOWN-null semantics before rendering.
- New `FinanceMarketQuotaStatusPane.qml` shows the latest snapshot for
  both providers, labels local reserved/unreserved amounts and excludes
  account-wide remaining balances. It has no reset, cleanup, paid upgrade
  or external network control.
- The new QUOTA STATUS button and overlay are mounted solely within the
  existing Market STOCKS pane; no Banking, Budget, Strategies, Research,
  SEC, Connections, protected writers or M20 reservation code changes.

## HOW TO USE

After independent review and **separately approved native deployment**:

Finance → MARKET → STOCKS → **QUOTA STATUS**

The pane reads the M20 ledger **without consuming provider calls**.
Press **REFRESH LOCAL STATUS** to re-read the existing bytes. Return using
**BACK TO STOCKS**. If a provider call completes while status is open,
manually refresh; there is no background polling or filesystem watcher.

A missing M20 quota database should remain missing until an existing
approved provider request actually creates it. Do not create an
artificial zero database to make status look healthy.

## VERIFY

- `test_market_quota_status.py` creates **only disposable test fixtures**:
  missing directories/database, valid M20 writer-created SQLite rows,
  separate UTC-day totals, unchanged DB bytes/mtime, unsafe file/directory
  permissions, a hot-journal sidecar, a symlink, a concurrently held
  exclusive POSIX lock, corrupt/empty DB, and no generated paths.
- `test_market_quota_status.mjs` launches the disposable Python test,
  checks exact QML subprocess invocation, no provider URLs,
  no M20 `reserve` path, strict UNKNOWN-null response and Market
  control/source isolation. Hooked into the existing
  `test_market_price_range.mjs` workflow alongside M9–M20.
- GitHub CI proves the isolated source behavior, **not** native
  Quickshell focus/scrolling, live M20 filesystem permissions or a
  provider's real remaining calls.

## WATCH OUT FOR

The original six-company EODHD reader and outside tools can use the
same provider account while the local ledger remains unchanged. Never
present this STATUS count as the actual provider balance.

A concurrent writer or hot SQLite journal may make a single inspection
show UNKNOWN; this is a safe refusal, not proof of data corruption.
Try manual REFRESH after the writer finishes. Never erase, chmod, reset,
or unlink the M20 database to clear that state.

Native host mutation, production activation and any new quota writers
require separate operator authorization. An independently reviewed
M20 security baseline remains a prerequisite before calling the overall
quota subsystem production-ready.

## NEXT

Independent Nurse 2 review of M20+M21 read/write boundary, then
operator-approved native Quickshell, private-storage and no-network
acceptance. Later, add authorized shared provider coverage/status for
the legacy Market Hub if its owner approves; do not silently expand
M21's read-only scope.

**GITHUB DRAFT ONLY // NO LOCAL HOST WRITE // PRODUCTION HOLD.**
