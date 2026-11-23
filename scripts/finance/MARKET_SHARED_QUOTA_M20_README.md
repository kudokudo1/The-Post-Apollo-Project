# FinanceW MARKET M20 // Crash-safe local free-provider request budget

## What changes

FinanceW's **global EODHD** and **Alpha Vantage** price-reader CLIs now reserve
their next free-plan request in a **shared SQLite ledger before the upstream
HTTPS request starts**, rather than trusting only the previous QML
instance-local counters. The registered account's actual balance is still
**not observable** through these public historical-price APIs. This is a
local, conservative Post-Apollo safeguard, **not provider billing data**.

The ledger is:

`~/.local/share/post-apollo/finance-market/global-free-provider-attempts-v1.sqlite3`

The only persisted fields are:
`provider`, `utc_day`, and `reserved` (an integer). No company/ticker,
API key, symbol, FIGI, currency, personal account, or request URL is stored.

| Provider | Reserved daily local ceiling | Included requests |
| --- | ---: | --- |
| EODHD | 20 | M18 global listing search and global daily EOD history |
| Alpha Vantage | 25 | M19 symbol search and compact daily history |

**Not included**: the original six-stock EODHD reader and Market Hub, any
other Post-Apollo widget or integration, browser, other computers, Python
scripts calling these APIs directly, or any calls made outside these two
instrument-discovery CLIs. These sources can exhaust the account despite
this ledger. A valid free key is still required for each provider, stored
under its existing owner-only token path. This PR does not create keys or
link accounts.

## How it works

- The existing manual user flow stays unchanged:
  Finance → MARKET → STOCKS → GLOBAL SEARCH → PRICE OPTIONS → provider →
  candidate listing → preset → **LOAD HISTORY**.
- The script validates the request and reads its existing private token,
  then calls the M20 wrapper **immediately before its outbound fetch**.
  The wrapper launches `python3 market_shared_quota.py reserve PROVIDER`
  with fixed arguments and **no shell or key in argv**.
- Python opens the owner-controlled finance-market directory without
  following symlinks. It creates the DB with 0600 permissions in a
  private 0700 directory when absent. Unsafe directory ownership/mode,
  symlinked or multi-hardlinked DB, corrupt DB, lock contention and
  interpreter failures **fail closed before the provider request**.
- SQLite `BEGIN IMMEDIATE` serializes independent processes. One
  transaction increments an existing provider+UTC date row or refuses when
  the documented free ceiling is reached. Database transactions survive
  normal process completion and crashes. A crash after reservation is
  **not refunded** because the external provider might have received
  the request.
- Success replies carry `localQuota` with an exact schema; the QML
  reader validates provider, UTC date, count, ceiling, and
  `notAccountBalance:true` before displaying the result.
- Each price pane displays its old `PANEL ATTEMPTS` plus the most recent
  successful `LOCAL SHARED RESERVED X / LIMIT` or
  `LOCAL SHARED RESERVATION NOT YET READ`. Neither display claims the
  provider account's remaining calls.
- If exhausted, the operator sees `SHARED LOCAL ... BUDGET EXHAUSTED`.
  If the ledger is missing/broken/insecure and cannot be safely created,
  requests are refused with `LOCAL QUOTA STORAGE UNSAFE OR UNAVAILABLE`.
  There is **no auto-retry, paid upgrade, bypass, alternate provider
  fallback, or local record reset**.

## Limits and important caveats

1. Daily caps are an upper bound on **our two local readers' attempts**, not
   a live provider allowance or proof of actual entitlement. Token changes
   share the same local provider bucket for conservatism.
2. The legacy six-company EODHD source remains outside this write path.
   Including it requires reviewing its shared Market Hub, cache and
   concurrency owner; **no cross-owner changes were made here**.
3. A hard restart can make the old UI panel count zero, while the SQLite
   ledger still refuses a request when its shared local daily limit has
   already been consumed. The UI will not show the persisted count
   before its first successful request, since no background read was added.
4. UTC date is used for the local bucket. Exact provider reset semantics,
   billing units, entitlement policy, and other-machine traffic must not
   be inferred from this count.
5. This is a real **local file write only after an operator has separately
   approved merging, deploying and activating this PR on the host**.
   Merely creating/reviewing the GitHub draft does not touch the live host.
   On native acceptance, verify the existing `finance-market` directory
   is user-owned, non-symlinked and private; do not silently chmod/delete
   anything to bypass a refusal.
6. If the canonical market source storage format changes, preserve this
   ledger or explicitly migrate it; deleting the ledger mid-day can lose
   local quota memory and allow overspending. No automated removal,
   reset, or cleanup functionality exists in this patch.

## Verification

- `tests/finance/test_market_shared_quota.py` uses a disposable temp DB.
  It tests exact 20/25 provider limits, UTC bucket isolation, transaction
  persistence, 32 concurrent independent connections racing for 20
  reservations, refusal of the 12 losers, zero refunds and corrupt DB.
- `tests/finance/test_market_shared_quota.mjs` uses only injected fake
  network/reserver functions. It checks strict Python process invocation
  and output validation, no network on budget refusal, exact source
  integration and QML validation/error disclosures.
- The Node test launches the disposable Python test. Both are wired into
  existing `test_market_price_range.mjs` in the FinanceW Market contract
  CI alongside M9–M19. The automated suite deliberately does not
  contact a live provider, read a real key, or touch the host quota file.

## Next checkpoints

Independent Nurse 2 review must cover local directory/SQLite attack
surfaces, transaction durability, output parsing, and the exclusions above.
A separately authorized native acceptance must test real Quickshell pane
behavior and the failure mode for an unsafe existing directory, without
spending a user's free provider calls unintentionally. Later, a distinct
ownership-reviewed project can add genuine cross-widget account-budget
coverage, read-only STATUS display, or a provider-capability matrix. Those
features are not silently granted by this patch.

**PRODUCTION HOLD / DRAFT ONLY.**
