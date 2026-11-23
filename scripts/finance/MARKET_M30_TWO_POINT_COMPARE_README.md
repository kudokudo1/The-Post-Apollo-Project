# FinanceW Market M30 // Pin A and compare any two loaded historical closes

## IMPLEMENTATION

M27 compared the selected stock chart close against only the **last loaded close**. M30 adds an independently controlled **A/B historical point comparison** inside the existing MARKET → STOCKS → RANGE view. Both dates must already be in the same validated price snapshot. There is no new provider request, backend, price-reader subscription, quota reservation, storage, credential or transaction workflow.

The existing pure `FinanceStockRangeAnalysisPolicy.js` now provides `comparePinnedRangeSessions(snapshot, firstIndex, secondIndex)`. It reuses M26 strict source validation for a bounded read-only EODHD range with one price basis, positive finite prices and chronological actual session bars. It accepts two exact integer indices and returns copies of:
- pinned A and current selected B actual closing date and value;
- signed dollar change and signed percentage change of **B relative to A**;
- the **absolute number of observed session transitions** between them;
- whether B lies **FORWARD**, **BACKWARD**, or at the **SAME** position in the loaded range.

No calendar days, weekend sessions, intraday prices, future quotes or investment performance are inferred. Choosing B from an earlier date is allowed: `B MINUS A` still uses pinned A as its baseline and explicitly labels BACKWARD.

In the existing `FinanceStockHistoryPane.qml`, after selecting a chart close, **PIN AS A** saves only a temporary point index and a reference to the exact already-loaded snapshot; a yellow chart marker identifies A. Clicking a different chart session selects B in the existing orange selected-point marker. A new read-only `PINNED A VS SELECTED B` panel appears, while the existing M27 selected-to-last and OPEN IN DAY controls remain intact.

**CLEAR PIN A** removes the reference. Changing the loaded snapshot, switching DAY/RANGE, replacing the bars, or invalidating the issuer/date-range analysis clears the pin automatically. Without a current validated source and exact snapshot identity, no comparison is displayed. Deselecting B hides the comparison but can leave A pinned for another B choice.

## HOW TO USE

After an operator-authorized merge and host deployment:

1. Finance → MARKET → STOCKS → RANGE → LOAD RANGE.
2. Click any actual chart point to select historical close **A**. Click **PIN AS A**.
3. Click a different point on the same chart for **B**. Read the dollar/percentage movement, ordered dates, and observed session steps under **PINNED A VS SELECTED B**.
4. Click other points to compare each against the same A, or **CLEAR PIN A** to end that comparison. Selecting another stock or history window starts without an old pin.

An A/B comparison is historical closing-price research, not a trading order or a current quote. It consumes **no additional provider requests** beyond the original deliberate LOAD RANGE.

## VERIFY

The new `tests/finance/test_market_m30_two_point_compare.mjs` uses a fixed six-session fictional EODHD range to test:
- A=110 and B=90, **-$20 / -18.18%**, three observed transitions FORWARD;
- pinned A=90 and B=100 from an earlier close, **+$10 / +11.11%**, four transitions BACKWARD;
- same point, unchanged adjacent closes, single-session, no fabricated percentage or missing-index value;
- frozen source records remain unchanged and calculated output is copied;
- invalid index, wrong source, malformed dates/prices, inconsistent first/last and oversized series fail closed;
- QML contains exact snapshot identity and clearing guards, explicit A/B controls, two chart markers and no provider/process/storage call in its comparison controls.

The test is chained to `tests/finance/test_market_price_range.mjs` and the existing M26–M30 CI workflow, which also runs the older M10–M29 mocked-provider and pure analysis tests.

## WATCH OUT FOR

M30's visual chart marker and buttons have source-level and unit test coverage, but **actual native Quickshell interaction requires a separate operator check** after source merge/deployment. Do not infer a native PASS from GitHub tests. Operator's M29 draft was merged at preflight; M29 native functional acceptance has not been claimed here.

The pin is **not saved** across sessions or reloads, and its data stays in the widget process only. Adjusted closing prices may later be revised for corporate actions. No real accounts, banking, investing trades, or user portfolio holdings are accessed. M20 quota filesystem security review is separately owned by Nurse 2 only at that narrow boundary; Connections is not required for this read-only Market change.

## CHECKLIST

- [x] Current main and Syntagma/Hospital role/source preflight
- [x] M29 merged, no competing M30 PR
- [x] Pure A/B calculations using validated existing-range source
- [x] Existing chart pin/clear controls and stale-source invalidation
- [x] Fictional test and full Market regression integration
- [ ] Exact-head GitHub CI and raw logs
- [ ] Operator merge decision
- [ ] Native chart/controls visual acceptance

## NEXT

Run all exact-head workflows. Keep the PR draft until authorized. For native acceptance, use already-loaded historical series and **do not spend provider quota solely for M30 testing**. Protect the operator's dirty Fedora Quickshell working tree.

**DRAFT / NO PROVIDER CALLS / NO HOST WRITES / PRODUCTION HOLD.**
