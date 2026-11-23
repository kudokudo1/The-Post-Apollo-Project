# FinanceW Market M24 // Disposable populated-ledger visual acceptance

## IMPLEMENTATION

M23's operator-reported live Quickshell acceptance passed **ABSENT / UNKNOWN**
with no real M20 SQLite ledger. M24 adds a **separate** populated-ledger
visual fixture, without spending an actual provider request or seeding
the production ledger.

The test uses M20's real `reserve()` writer with explicitly injected
SQLite files inside a disposable directory and M21's real
`quota_status(database=...)` reader. It then loads the **actual**
`FinanceMarketQuotaStatusPane.qml` and
`FinanceMarketQuotaStatusService.qml` in a detached native Qt window.

A fake test-only Quickshell Process module, created in the same temp
directory, validates the usual M21 status command but never executes
a child process, accesses the live quota file, or contacts providers.
Neither M20 nor M21 nor production QML is modified.

| Scenario | True disposable M20/M21 input | Real pane output |
|---|---|---|
| LOW | 3 EODHD and 9 Alpha reservations | 3/20, 9/25 |
| FULL | 20 EODHD and 25 Alpha reservations | 20/20, 25/25 |
| ZERO | Prior-day reservations only | 0/20, 0/25 **local only** |
| ABSENT | Missing **test** DB | Both UNKNOWN |
| UNAVAILABLE | Corrupt **test** DB | Both UNKNOWN |

## HOW TO USE

### CI (isolated)

    python3 -B tests/finance/test_market_m24_populated_visual.py --ci

The M24 GitHub Actions job installs PySide6 and Qt on the **disposable
runner only**. Its automation renders the real QML pane and checks all
five scenarios, the real refresh/back signals, and compact/wide layout.
The test checks that the sample DB hashes and mtime remain unchanged.

### Optional live desktop visual fixture

Only after the PR is merged into the checkout and **if PySide6 is
already installed**:

    python3 -B tests/finance/test_market_m24_populated_visual.py --visual

This opens a **separate Qt test window**, not a new Quickshell session.
The permanent orange banner warns: NOT YOUR REAL QUOTA OR API ACCOUNT.

Choose LOW / FULL / ZERO / ABSENT / UNAVAILABLE across the top to
reopen the real pane with each disposable scenario. The pane's real
REFRESH LOCAL STATUS button replays the selected in-memory reply.
BACK TO STOCKS closes the pane inside the test window, and selecting
another case reopens it. Resizing tests the compact layout. Closing
the window automatically deletes temporary DBs and QML test stubs.

If PySide6 is missing, stop. Do not install packages or change the
live desktop simply for this test.

## VERIFY

- M20 creates local test counts and caps in a disposable private DB.
- M21 reads those files via its test-only database override, with no
  observed file modifications.
- The **actual** pane and service render populated, capped, real-zero,
  missing, and unavailable results correctly.
- Actual QML ActionButton refresh/back signals work; resize does not
  issue extra requests. All Process.exec traffic is intercepted by a
  fake QML module that cannot run commands.
- Existing M21 no-write regression is repeated in the M24 CI workflow.

## WATCH OUT FOR

**This is native Qt visual testing, NOT a production Quickshell runtime
test.** M24 proves the real pane renders realistic SQLite-generated
counts, not that the operator's canonical M20 DB was populated or that
the free API provider's full account balance is known.

No canonical user SQLite path is opened, seeded or reset. All writes
happen only inside the auto-destroyed temp directory. The operator's
dirty local Quickshell tree must be preserved. A future legitimate
provider read may populate the normal ledger; never spend a request
solely to manufacture a passing test result.

M20 filesystem/concurrency safety remains a separate focused security
review boundary. No Connections workers own this test or block it.

## CHECKLIST

- [x] M20-M23 merged; M23 ABSENT native operator PASS recorded
- [x] Real M20-to-M21 SQLite fixture and detached actual QML pane
- [x] No production quota / Quickshell change
- [ ] M24 exact-head CI
- [ ] Operator merge approval
- [ ] Optional operator native Qt visual fixture check
- [ ] Production populated-ledger/independent security acceptance

## NEXT

Run exact-head CI, keep the feature in draft until approved, then use
the optional native visual window only where PySide6 is already
available. Do not modify the actual quota database for acceptance.

**PRODUCTION HOLD // NO LIVE PROVIDER REQUESTS // DRAFT.**
