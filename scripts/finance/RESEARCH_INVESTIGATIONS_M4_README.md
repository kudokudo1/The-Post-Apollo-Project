# FinanceW Research M4a // Explicit Read Controller

**Patient:** `The-Post-Apollo-Project`  
**Room/assignment:** FinanceW Research, isolated Investigations read path  
**Provider:** OpenAI / ChatGPT, external Hospital-compatible DOC  
**State:** Code under review; not installed or mounted in the active FinanceW menu.

## What this stage adds
The M1 investigation model, M2 local file store and M3 investigation pane already exist on `main`. M4a establishes **only the read path** between them, in three Research-owned files:

- `scripts/finance/research_investigation_read_bridge.mjs` is a Node process that accepts exactly one newline-terminated `{"action":"list"}` request and calls the M2 store's read action. It validates the versioned response against the M1 model, emits exactly one bounded result line and exposes no mutation flag.
- `services/finance/FinanceResearchInvestigationReadService.qml` starts the Node process only after an explicit `load()` call while monitoring, reads one bounded result, checks its structure and blocks stale results when the host is deactivated.
- `widgets/FinanceResearchInvestigationsReadHost.qml` composes the existing M3 pane and read service without altering the shared `FinanceW.qml`. **`writeEnabled: false`** is hardcoded, and none of M3's create/attach/remove signals connect to storage.

This is a **preview host**. It is not launched from the main Research menu, has no network path, and cannot create or alter investigations.

## UI behavior after a separately approved integration
Research → Investigations → **LOAD CASES** displays the local case list and a selected case's saved evidence. The first integration should remain read-only until the M2 security reviewer explicitly clears the write path.

No automatic loading: opening, hiding, resizing, or re-opening the pane never starts a storage request. Leaving the host discards the displayed data; an in-flight read that completes afterward is ignored.

## Safety
- CLI accepts only an exact, bounded list request; no create/attach/remove action or future undocumented toggle can convert it to a writer.
- Node keeps all data local and does not print private record contents on error.
- Store corruption, symlinks and unsafe permissions fail visibly. A missing store returns an empty, read-only result without creating directories.
- The controller distinguishes `idle`, `loading`, `ready` and `failed` and refuses overlapping requests.
- M2's previously documented stranded-lock and filesystem race concerns still exist for *writers*. This milestone is **not** their security acceptance and does not alter that code.
- Records are not encrypted and do not imply identity or household authorization.
- No account, market, SEC network, cash movement, or automatic trading functionality is reachable through this bridge.

## Verify
```sh
node tests/finance/test_research_investigation_read_bridge.mjs
python3 -B tests/finance/test_research_investigation_read_controller_contract.py
```
The existing Research CI workflow includes these tests and the M1/M2/M3 regressions. A green test run is only exact-head automated verification, not local native Quickshell acceptance.

## Blockers before M4b (writes)
1. Independent Nurse 2 security review of the M2 store and its crash-recovery procedure, including disposable crash/lock test evidence.
2. Review of filesystem path traversal, race safety and local identity rules. No private company/household secrets.
3. A separate reviewed write controller: nonce/ID generation, expected-revision handling, no automatic retry after unknown outcomes, and verified result acknowledgement.
4. Coordination with the FinanceW shared navigation owner before adding an Investigations tab.
5. Operator-authorized merge, local installation, and compact/wide live acceptance. No uncontrolled update or production activation.
