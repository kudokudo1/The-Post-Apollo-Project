# Reusable DIAG Dock Button + In-Widget Service Health Popup

**Patient:** `The-Post-Apollo-Project`  
**Room / Assignment:** FinanceW Research diagnostic experience, shared Weather/Finance component extraction  
**Role:** External Hospital-compatible DOC, no claim of live Hospital registration  
**Deployment:** Draft source only; local machine, Quickshell and production unchanged

## IMPLEMENTATION

This work extracts **Weather Station's existing M6c implementation**, not a painted replica.

1. **`components/DiagnosticsDockButton.qml`** is the original top-dock `ActionButton` behavior: **DIAG** when closed, **BACK** when open, 59×32 geometry, yellow accent and one explicit `toggleRequested()` signal. Host remains the owner of the open flag. It never launches an extra window.
2. **`components/DiagnosticsServicePopup.qml`** is the original Weather diagnostics popup structure: in-widget `Rectangle`, top-right overlay placement supplied by host, independent close button, `Flickable`, `NeonScrollBar`, service rows, per-state border/text coloring, origin, last reading, reason, and read-only footnote. Its inputs are generic; it owns **no service**, timers, processes, requests or writes.
3. **Weather:** `StationWeatherProviderDiagnostics.qml` becomes a thin binding adapter. It keeps Weather's current `StationProviderDiagnosticsPolicy.snapshot()`, uses the **same primary, fallback and AQI entries**, and the original `WeatherStationW.qml` owns popup visibility and close/Escape priority. This preserves Weather as the working implementation.
4. **Finance:** `widgets/FinanceW.qml` uses the same shared top-header button and same shared popup as a child of its existing content area. Its rows come directly from **already-present** Budget, Market, Research Crawl, SEC EDGAR, SEC Document and SEC Price reader instances. Banking is explicitly `MANUAL` or `IDLE`, not presented as a verified connected provider.

## HOW TO USE (after separately approved installation)

- **Weather Station → top header → DIAG**: opens the original provider-health inspector; **BACK**, **×**, or **Escape** closes it before the overall window.
- **FinanceW → top header → DIAG**: opens the same reusable in-widget inspector, now listing Finance's individual services; **BACK**, **×**, or **Escape** closes only the diagnostic popup.
- Navigation, keyboard ownership, resizing and visible source state remain with each owning widget. A popup is not a separate external window or service.
- Inactive service rows show `IDLE`; saved public data shows `SNAPSHOT`, **not** verified bank connectivity. `LAST PROVIDER SUCCESS // --` means no trustworthy per-service success timestamp was exposed in these existing Finance readers; no timestamp is inferred.

## VERIFY

CI source and parity checks:
```sh
python3 -B tests/components/test_shared_diagnostics_weather_finance.py
python3 -B tests/weather/test_weather_provider_diagnostics_integration_m6c.py
node tests/weather/test_weather_provider_diagnostics_m6c.cjs
python3 -B tests/finance/test_finance_adaptive_chassis_contracts.py
python3 -B tests/components/test_finance_dock_contracts.py
```

**Native Quickshell approval still pending:** render both widgets on the operator desktop, open/close the popup, examine rows, press Escape, resize through compact/wide tiers, and ensure no unexpected launches or focus loss. A green source contract cannot prove desktop layout.

## WATCH OUT FOR

- This is **shared UI code** touching a Weather-owned widget and shared Finance header, not purely an isolated Research file. It needs owner coordination and independent integration review before merge.
- Diagnostics never re-fetch or mutate data. A row labeled LIVE comes from the owning service's existing state, not a diagnostic network test.
- Research M5 source-health audit and M2 persistent writes are separate from service-status inspection. This popup does not activate M2 writes or pretend to run a source-health scan automatically.
- No account linking, transaction writes, bearer keys, storage permissions, outside windows or background tasks are introduced.

## CHECKLIST / NEXT / DECISIONS

- [x] Inspect actual Weather M6c provider policy, button, scrolling and popup lifecycle
- [x] Extract reusable ActionButton and popup, preserve Weather through an adapter
- [x] Reuse the component in Finance with current service owner statuses
- [x] Ensure DIAG/BACK, close ×, Escape-first, window-close reset and keyboard-nav guard
- [x] Add targeted cross-widget tests, existing Weather/Finance regressions and CI
- [ ] Verify exact PR head in GitHub Actions
- [ ] Coordinate ownership and native acceptance before authorized merge
- [ ] Optional later diagnostics extensions such as a manually triggered M5 read-only audit

**Decision:** One shared source implementation serves multiple widgets, with provider adapters and popup ownership remaining with each widget. Existing cosmetic bugs stay in the later UI-polish lane.
