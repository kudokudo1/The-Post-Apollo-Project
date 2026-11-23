# FinanceW Market M23 // Operator-guided native quota acceptance probe

## IMPLEMENTATION

M22's real QML pane/service already passed **offscreen** Qt CI. This M23
tool provides a **read-only operator-run acceptance probe** for the actual
Fedora host, without modifying M20's SQLite budget, reloading Quickshell,
opening a provider session, or installing dependencies.

New `scripts/finance/market_quota_native_acceptance.py`:

- Starts the existing **M21** `market_quota_status.py status` CLI as a
  bounded subprocess, using fixed arguments, Python `-B` and
  `PYTHONDONTWRITEBYTECODE=1`. It does not run M20's `reserve`, create a DB,
  call an API, or create `__pycache__` under the checkout.
- Uses M21's existing **trusted read-only descriptor traversal** to capture
  an in-memory SHA-256 fingerprint and immutable file metadata before and
  after the CLI, and on both sides of the user-led desktop checks. No raw
  database bytes are printed; no token, account identifier or symbol is
  read from the ledger.
- Validates both providers, UTC date, exact M21 provenance/readOnly/
  noProviderCalls/notAccountBalance flags and UNKNOWN-null semantics. A
  genuinely missing ledger is **ABSENT / UNKNOWN**, never a fabricated
  zero.
- Provides a terminal-guided checklist for the running **Finance → MARKET
  → STOCKS → QUOTA STATUS** UI: open, confirm provider counts or UNKNOWN,
  press local REFRESH twice, then use BACK TO STOCKS. Only the operator can
  observe the real desktop.
- If bytes, inode, size, mode, mtime, ctime, UTC day or local counters differ
  across the UI test, reports **INCONCLUSIVE**, not PASS or an accusation
  of a bad writer. Another valid worker could have spent a provider slot.
  Unsafe or locked ledger also stays INCONCLUSIVE; no automatic retry,
  chmod, deletion, reset or bypass.
- Labels UI PASS as **OPERATOR-REPORTED**, not independently instrumented
  GUI proof. Produces stdout only, no uploaded or persisted evidence.

No changes to production QML, M20's writer, M21's reader, protected files,
Market Hub, other worker menus, profiles, credentials or sign-in scope.

## HOW TO USE

**After the change is merged and the updated scripts exist in your actual
Post-Apollo checkout** (do not pull/reset an active working tree just to run
this): open a terminal **inside that checkout** and run:

```bash
python3 -B scripts/finance/market_quota_native_acceptance.py --preflight
python3 -B scripts/finance/market_quota_native_acceptance.py --interactive
```

The first command checks that the local status CLI reads the ledger without
an observed modification, or reports absent/unavailable. The second keeps
the terminal waiting while you use the live UI, then asks for one of:

- `PASS`: Actual UI opened, local values/UNKNOWN matched the reference,
  refresh worked twice and BACK returned to STOCKS.
- `FAIL`: Any of those real UI checks failed.
- `SKIP`: Could not observe the UI.

The probe compares the **before/after** local ledger bytes and metadata
after the response. `PASS` plus unchanged ledger means only **scoped
operator-reported UI PASS + unchanged ledger**. Final production acceptance
remains the operator's separate decision.

A missing ledger or a visible `UNKNOWN` is not permission to create or
reset the DB. If a legitimate provider request happens during the test, the
count may change; do not erase the record to force a passing result.

## VERIFY

- `tests/finance/test_market_m23_native_probe.py`: strict response
  validation, no false zero, untrusted source/provider/range rejection,
  fixed interpreter/arguments/timeouts, no silent backend errors, changed
  file/UTC-day/local count refusal, and correct PASS/FAIL/SKIP evidence
  classification with mock inputs. No real operator prompts or filesystem.
- `financew-market-m23-native-probe.yml`: runs the new fake-only probe
  tests, plus previously passing **M20** disposable SQLite concurrency
  and **M21** disposable read-only status tests on an isolated CI runner.
- M22's offscreen actual-QML job remains independent and unchanged.

## WATCH OUT FOR

**Not a remotely executed native test.** A GitHub CI PASS here does not
mean the operator's desktop was inspected. The conversation cannot read
local Sway/Quickshell windows directly, and this script does not launch
Quickshell, capture screenshots, intercept network traffic or install
software. It can demonstrate the exact M21 local CLI returned the expected
read-only contract and that the validated ledger fingerprint did not change
between the observed checkpoints; it cannot prove another process did
not make a separate API call or modify-and-restore bytes in between.

The ledger tracks only two Post-Apollo global price readers, not the
provider account's total usage. M20 file trust and SQLite concurrency
are still a separate *security* review boundary. Do not describe M23 as
Nurse 2 acceptance, account-wide quota assurance or production approval.

Do not run on a checkout without the M21 reader files. Do not run as root
or under a different user; the status reader uses the effective user's
password-database home and ownership. If Python is unavailable, stop.
A failure is diagnostic, not authorization to alter file permissions.

## CHECKLIST

- [x] Source-only M22 merged and 5/5 CI PASS verified
- [x] M23 no-write CLI, fixed one-reader invocation, operator-led UI flow
- [x] CI tests run only fake data/temporary SQLite
- [ ] M23 draft exact-head CI
- [ ] Actual operator host test and UI observations
- [ ] M20 security-boundary review if needed for production trust
- [ ] Separate final operator acceptance

## NEXT

Run the new CI gate on the M23 draft. After operator-approved merge and
native checkout availability, use `--preflight` and `--interactive` on the
actual Fedora host. Return the result to the Market worker for
reconciliation against source/CI, without logging or exposing credentials.

**PRODUCTION HOLD // NO LIVE HOST MUTATION // NO MERGE WITHOUT AUTHORIZATION.**
