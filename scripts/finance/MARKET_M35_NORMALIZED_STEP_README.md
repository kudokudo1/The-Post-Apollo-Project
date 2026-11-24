# Market M35 // Shared normalized step inspection

## IMPLEMENTATION
Click the M34 normalized comparison chart to select the nearest ordinal observed step using its existing common horizontal scale. A yellow vertical cursor and highlighted actual observations identify the two paths. Details give each observation's actual calendar date, normalized index, percentage movement from its own baseline and the difference (interval 2 minus 1) in percentage points. An ended shorter interval shows N/A, not an extrapolated observation. Clicking the same step clears the cursor. A changed normalized comparison resets selection; resizing preserves the selected ordinal step. No additional provider calls, persistence, financial writes or account access.

## HOW TO USE
After approved merge/deployment: Finance → MARKET → STOCKS → RANGE → pin A, select B, SAVE INTERVAL 1, choose another A/B. Click the normalized chart at the desired horizontal position. Click that step again to clear. Change a comparison endpoint to reset the cursor.

## VERIFY
Fictional Node fixtures check the shared-axis hit mapping, unequal lengths, actual dates, base values, gaps, reverse direction, invalid inputs, copied observations and no provider commands. M35 is included in the existing Market regression chain. Actual Qt interaction and drawing require operator-native verification.

## WATCH OUT FOR
Same ordinal step need not mean same date or same elapsed calendar time. The chart compares relative historical movement, not investment returns or forecasts. Shared FinanceW category-preview source-contract mismatch from M34 remains a separately owned issue unless reverified fixed.

## CHECKLIST
- Pure inspection and source integration.
- Exact-head Market and shared CI.
- Operator merge/deployment and native interaction.

## NEXT
Verify click/clear, changed intervals, resize and a step beyond the shorter interval using already-loaded history.

## DECISIONS
Market DOC; source-only changes. No local host mutation or production activation.
