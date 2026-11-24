# Market M34 // Base-100 historical interval chart

## IMPLEMENTATION
M34 visualizes the two M32/M33 intervals from one validated, already-loaded EODHD closing-price snapshot. Each interval is ordered chronologically, starts at index 100, and has a value of 100 times actual close divided by its own first close. Cyan represents saved interval 1; magenta represents current interval 2. Both share one y-scale and one x-scale from zero to the larger observed transition count. The gray horizontal reference is 100. Shorter lines end at their own final observation; no resampling, padding, extrapolation, or new provider operation. A flat combined range is centered vertically. The original absolute-price chart and all prior comparison figures remain unchanged.

## HOW TO USE
After approved merge/deployment: Finance → MARKET → STOCKS → RANGE → pin A and select B → SAVE INTERVAL 1 → choose another A/B. The normalized chart appears below the existing interval comparison; its legend identifies colors, high/low, final values and actual ending steps. Clearing either interval or changing the loaded source hides the chart through the existing comparison validity binding.

## VERIFY
Fictional Node tests cover base-100 calculation, common geometry, unequal lengths, reversal, flat paths, overlapping intervals, invalid inputs and copied outputs. Source checks verify local-only painting and repaint triggers. Existing full Market regression workflow includes M34. Native QML rendering and lifecycle are separate acceptance steps.

## WATCH OUT FOR
Index 100 is dimensionless, not $100 or an investment amount. A chart step is one returned closing-price transition, not calendar time. The two periods may overlap and may have different lengths. Lines connect observations visually; they do not supply unobserved prices or forecasts. No provider calls, account access, storage writes, annualization or trade recommendations are added.

## CHECKLIST
- Implementation and numerical regression.
- Exact-head CI.
- Operator-authorized merge and deployment.
- Native chart rendering and clearing behavior.

## NEXT
Verify chart with existing loaded ranges, including a short and long interval, flat data and clearing. Do not spend provider quota solely for a test.

## DECISIONS
Market DOC source-only work. No local host mutation or production activation.
