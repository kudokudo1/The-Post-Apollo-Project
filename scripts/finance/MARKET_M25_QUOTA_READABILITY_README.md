# FinanceW Market M25 // Readable compact local quota status

## IMPLEMENTATION

M24 verified five disposable SQLite quota cases in the real Market QML pane. The user's Fedora screenshots show that the status screen works in a small window, but the 9px advisory and per-provider text can be hard to read. M25 makes a **UI-only** readability pass on the *existing* `FinanceMarketQuotaStatusPane.qml` rather than creating a new service, control, or test-mode bypass.

- Header uses a shorter `LOCAL FREE API // QUOTA STATUS` label and a larger BACK button.
- Refresh and local-state labels use 11–12px text, with provider titles at 13px, reservation counts at 12px and advisory/context text at 11px. Footer remains 10px.
- Provider cards are 142px high to fit wrapped context. The per-card line no longer truncates `OTHER APP USE UNKNOWN` or `NO USAGE CONCLUSION // NO ZERO ASSUMED`.
- Cards stack in narrow widths (below 560px available grid width), preserving two cards side-by-side for wide layouts.
- Repetitive disclaimer text is shortened while retaining three essential rules: local requests are not provider-account usage; absent or unsafe ledger means UNKNOWN; the page never creates, resets or repairs SQLite.
- Preserves `NeonScrollBar`, Back/Refresh action signals, source identities, all exact M20/M21 limits and non-network behavior.

The real QML M24 test now checks one-column compact and two-column wide layout, provider context font sizes, text height and containment within each card, all five ledger cases, refresh and back. The M24 workflow is triggered by changes to the production quota pane so regression coverage follows future UI edits.

## HOW TO USE

After an authorized merge and separate live-host deployment, existing Finance → MARKET → STOCKS → QUOTA STATUS displays the larger, more legible text. No new button or data action is introduced. The optional M24 isolated Qt fixture still works:

`python3 -B tests/finance/test_market_m24_populated_visual.py --visual`

This requires an existing PySide6 environment, uses only temp SQLite files, does not launch real Quickshell or call a provider.

## VERIFY

- The M24 test must pass all real M20→M21 disposable populated/zero/absent/unavailable states in the actual QML pane.
- Compact 365px window must stack cards; wide 750px must use two columns.
- Both per-card disclaimers must have at least 11px text, wrap to fit, and remain inside their cards.
- Switching widths, rendering and refreshing must not spend any actual quota or issue an external provider request.
- M21 source contracts still require `LOCAL RESERVED UNKNOWN`, `NO USAGE CONCLUSION // NO ZERO ASSUMED`, `NOT ACCOUNT BALANCE`, `NO API CALLS`, `NO QUOTA RESET`.

## WATCH OUT FOR

This is **presentation-only** and does not change M20 quota ownership, the M21 local-only reader or provider-account limits. It does not mark the production populated-ledger path as tested. Compact screenshots are user visual evidence, not a reason to change the protected DB. The production authorization and M20 focused security review remain distinct.

## CHECKLIST

- [x] M24 merged, CI PASS and operator native Qt visual screenshots PASS
- [x] M25 readable UI text and responsive cards in the existing pane
- [x] M25 real QML compact geometry and no-truncation assertions
- [ ] M25 exact-head CI and raw logs
- [ ] Operator merge and native acceptance decisions

## NEXT

Run M25 exact-head CI in a draft PR. If accepted, the change is a layout improvement only; Market's backend, stock readers, Banking, Research and Connections remain untouched.

**PRODUCTION HOLD // NO PROVIDER REQUESTS // NO LOCAL DESKTOP MODIFICATION.**
