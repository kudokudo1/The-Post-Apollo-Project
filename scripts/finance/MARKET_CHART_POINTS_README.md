# Finance Market STOCKS // M12 Chart Point Inspector

## IMPLEMENTATION

M12 makes the **existing RANGE-mode daily closing-price chart clickable**.
It does **not** request more price data, introduce another API, or alter the
M10/M11 DAY and RANGE modes.

The native `Canvas` keeps the existing cyan line. Its contained
`MouseArea` finds the **nearest actual provider-returned session** in
both x and y coordinates, within 18 canvas pixels. The independent
`FinanceStockChartPointPolicy.js` is shared by rendering and hit testing,
so the same geometry is used by both.

On a valid selection:
- Magenta vertical crosshair identifies the exact returned session.
- Orange dot marks the selected close.
- A read-only detail below the graph shows **date, price basis, closing
  price, and symbol** from the existing in-memory EODHD snapshot.
- Click the selected point again to deselect. Click elsewhere outside
  the point radius to clear the selection.

The chart shows small cyan dots for up to 32 returned sessions. For denser
histories (up to the existing 132-bar cap), it keeps the cyan line and
only marks the selected session, avoiding 132 overlapping highlights.

## HOW TO USE

After operator merge and Quickshell update:

1. Finance → Market → STOCKS → RANGE.
2. Choose dates and press **LOAD RANGE**, as in M10/M11.
3. Click near a cyan plotted data point. Read the selected date/closing
   price under the chart. The orange point and magenta guide indicate
   exactly which returned session was selected.
4. Click a different point to inspect it. Click the same point again or
   click empty graph space to clear.
5. Switch to DAY, change company, or LOAD another RANGE. The previous
   selection clears; no stale detail remains.

The chart remains **click-to-inspect**, not hover-to-trade, no automatic
per-day fetch, no interpolation between real sessions and no price
estimated for nontrading dates. The position of returned sessions along
the x-axis is **equally spaced by trading-session index**, matching the
existing M10 chart. It is not a continuous calendar-day scale.

## VERIFY

- `node tests/finance/test_finance_chart_points.mjs` tests first,
  middle and final points; compact and dense graphs; constant prices;
  invalid/off-chart hit detection; exact date/close retrieval and
  separation from source objects, with fictional prices.
- `python3 tests/finance/test_finance_chart_point_contracts.py` verifies
  one FinanceW window, preserved three calendar controls, chart
  integration, selection clearing on mode/data changes and no extra
  provider, write or command execution.
- Existing M9–M11, SEC, OSIRIS, Polymarket and Budget tests remain
  part of GitHub CI.

GitHub does not render Qt/Wayland or simulate your physical pointer.
Live acceptance in compact and expanded FinanceW remains required.

## WATCH OUT FOR

A dense six-month chart may have many tightly spaced actual sessions;
the nearest plotted point is selected using both coordinates. A click
far from any plotted session clears selection. The behavior is local
to the current graph and deliberately does **not** change the separate
DAY date selection when inspecting a RANGE point. Prices are historical
daily closes, not intraday or a claim of causation.

No Quickshell startup/restart, provider key, service activation, cache
modification, trading path, FinanceW geometry change or Budget mutation
is included in M12.
