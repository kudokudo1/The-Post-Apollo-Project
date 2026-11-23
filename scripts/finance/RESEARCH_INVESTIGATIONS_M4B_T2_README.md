# FinanceW Research M4b-T2 // Disposable dispatcher and acknowledgement preview

**Patient:** `The-Post-Apollo-Project`  
**Scope:** FinanceW Research only, external Hospital-compatible development  
**State:** Reviewable staging, **no live write authorization**, no shared FinanceW menu changes

## IMPLEMENTATION
- `scripts/finance/research_investigation_disposable_dispatcher.mjs`: a test-only adapter that sends M2 commands into an OS-created private temporary directory. It does not accept a target path. It does not resolve XDG or user home storage. Each refusal has empty stdout and a fixed non-sensitive error message.
- `widgets/FinanceResearchWriteOutcomePanel.qml`: display-only status panel. It starts in `simulationOnly: true`, displays **not saved to live storage**, and has no Process, save, or retry signal. In a future reviewed controller, only a verified acknowledgement with a nonnegative revision may display a saved result. Uncertain outcomes preserve drafts and offer only a read-only reload request.
- Targeted Node disposable integration and static QML contract tests are included in the existing Research workflow.

The M4b-T1 `ResearchWriteAttempt` one-shot lifecycle remains the actual state-machine dependency. Its `dispatchOnce` method prevents a second call after the first dispatch. T2 tests use real M2 local-store code **only inside a disposable test directory** to test an acknowledged create, manual attach, remove, stale revision, malformed command and lost reply after committed replacement.

## HOW TO USE
Development tests only:
```sh
node tests/finance/test_research_investigation_disposable_dispatcher.mjs
python3 -B tests/finance/test_research_write_outcome_panel_contract.py
```
The test fixture creates and destroys its own temporary records. There is no new live menu entry or persistence activation.

## VERIFY
Check the exact PR head's `Finance Research investigation contracts` GitHub Actions job and raw logs for both M4b-T2 PASS strings. Native QML layout and focus checks are not established by source-contract tests.

## WATCH OUT FOR
- A successful disposable save is **not** a real user save or protected authorization.
- The outcome panel's properties convey presentation state only and are not trusted security credentials.
- M2 independent review remains required for filesystem trust, path and symlink safety, crash/lock recovery and concurrent writers before a production write dispatcher.
- Sensitive household finances, bank credentials and confidential company research must not enter the current unencrypted local Research store.
- Keep `FinanceResearchInvestigationsReadHost.qml`'s `writeEnabled: false`. No operator activation or Quickshell restart is part of T2.

## CHECKLIST / NEXT / DECISIONS
- [x] Reconfirm M4b-T1 merged and Research-owned file boundaries.
- [x] Add disposable-only dispatcher with no target override.
- [x] Add visible but non-executable acknowledgement/recovery UI.
- [x] Test exact ACK, stale writes, uncertain post-commit outcome, no duplicate submission.
- [ ] Exact-head Research CI and independent code review for security-boundary promotion.
- [ ] Native QML usability test for the status panel.
- [ ] Future independently reviewed protected live writer and coordinated shared menu integration.

No shared `FinanceW.qml` changes, merge, local machine mutation, or production activation are authorized or made by this milestone. Nurse 2 review is limited to the M2 security and subsequent live-authorization boundary, not ordinary Research UI development.
