# Market M33 // Observed-step interval comparison

## IMPLEMENTATION
M32 compares raw chronological endpoint changes for a saved and current A/B interval from the same loaded source. M33 adds the constant compounded change equivalent to each interval's endpoint ratio over its number of observed closing-price transitions.

For start price S, end price E, and n observed steps: 100 × (exp((log(E)-log(S))/n)-1).

100→121 in two observed steps and 100→110 in one both correspond to +10% per observed step, even though their raw changes are +21% and +10%. The difference is in percentage points. Four decimal places are display precision; subtraction uses unrounded values. Chronological endpoints are independent of pin direction. Existing overlap, drawdown, raw return and duration fields are retained.

## HOW TO USE
Finance → MARKET → STOCKS → RANGE → pin A and select B → SAVE INTERVAL 1 → choose a second A/B pair. Read GEOMETRIC CHANGE PER OBSERVED STEP. No new button or market request. Clear the saved interval using CLEAR INTERVAL.

## VERIFY
The fictional M33 Node regression checks equal equivalent growth for unequal-length segments, negative/flat returns, reverse selection, valid same-snapshot comparison, invalid data, and UI source contracts. It is part of the existing price-range CI chain.

## WATCH OUT FOR
An observed step is a transition between returned closes, not necessarily a calendar or exchange day. This is an endpoint-derived constant equivalent, not the arithmetic average of realized changes or a measure of volatility. Missing sessions are not invented. No annualization, forecast, portfolio performance, or trading recommendation. Comparisons remain within one snapshot and one price basis. No provider, file, account or quota access is added.

## CHECKLIST
- Source implementation and regression test.
- Exact-head GitHub CI verification.
- Operator-approved merge/deployment.
- Operator-native visual acceptance.

## NEXT
Verify CI, then inspect the panel on already-loaded historical data after approved deployment.

## DECISIONS
Market-owned read-only feature. Production activation and host writes remain outside this assignment.
