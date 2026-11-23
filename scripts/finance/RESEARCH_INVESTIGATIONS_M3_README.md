# FinanceW Research // Investigations M3 Interface

## Scope
The isolated `widgets/FinanceResearchInvestigationsPane.qml` presents a responsive investigation workspace. It is **not wired into `FinanceW.qml`**, so existing SEC and Source Crawl paths remain unchanged.

The pane accepts the M1 investigation array from a future controller and offers:
- browse and reopen an investigation in memory
- a new-investigation title and research-question form
- evidence source/title/summary/HTTPS URL drafting
- two-click removal of a selected cited source
- stacked compact / two-column wide layout
- status reporting and explicit read-only preview when unconnected

The only outward actions are QML signals (`loadRequested`, `createRequested`, `attachRequested`, `removeRequested`). A future reviewed controller is responsible for generating unique IDs and UTC timestamps, checking expected revisions and input validation, and applying the M2 local store contract.

## Security and ownership
- The pane owns no filesystem, credentials, HTTP, broker, SEC, market data, or budget code.
- `controllerConnected` and `writeEnabled` default to `false`. An unconnected preview does not offer working save/load buttons.
- Textual citations are displayed as plain text. No arbitrary URL execution or automatic source fetch.
- The M2 writer has not been reconciled into `main` and remains unreviewed for crash/recovery. Do not enable live persistence before independent review and a corrected integration path.
- All shared navigation edits remain with the FinanceW integration owner, coordinated via Nurse 2.

## Verify
```sh
python3 tests/finance/test_research_investigations_pane_contract.py
```
The test checks isolated signals, read-only defaults, source labels, layout responsiveness and absence of direct filesystem/network/financial operations.

Native Quickshell QML compile and compact/wide/fullscreen mouse tests are still pending. Static checks alone cannot certify responsive layout, input focus, or human readability.

## M4 candidate
After Nurse 2 review of M2:
1. Open a separate M2 reconciliation PR targeting current `main` with exact changed-file review.
2. Implement a Research-only controller with explicit M2 list/create/attach/remove calls, bounded stdout, revision tracking, stale-response refusal and recovery states.
3. Integrate M3 via an approved narrow change to `widgets/FinanceW.qml`.
4. Operator tests save/reopen across widget restart and handling of corrupted/locked data in a disposable local profile before activating for ordinary use.
