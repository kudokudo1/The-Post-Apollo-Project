# FinanceW Research M8 // Existing-menu integration

**Patient:** `The-Post-Apollo-Project`  
**Role:** FinanceW Research DOC, external Hospital-compatible contributor  
**Scope:** Shared `widgets/FinanceW.qml` Research tab only; requires FinanceW integration review before merge  
**State:** Draft source integration; no local desktop install or writer activation

## IMPLEMENTATION

M6 and M7 established an offline-validated SEC/Crawl evidence candidate model, on-demand read-only subprocess bridge, isolated picker, and a real disposable Fedora Quickshell native smoke test. M7 originally landed in an M6 feature branch rather than `main`. [M7 reconciliation PR #2315](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2315) adds those source files to `main` without changing its navigation.

M8 adds a **single third control** to the existing Finance → Research top strip:

- **SOURCE CRAWL:** existing saved demonstration crawl view
- **SEC EDGAR:** existing official SEC submissions reader
- **CANDIDATES:** existing M7 read-only preview picker

The candidate tab's host receives the already-created `crawlService` and `secService` objects. Neither is instantiated again, and switching to Candidates does **not** start a provider request. Previously loaded snapshots remain available for explicit **BUILD PREVIEW**, or the picker displays no candidates until the sources have been loaded through their original tabs.

The Finance header reflects the picker status with **READING / SNAPSHOT / ERROR / NO FEED**. The top-header resync button deliberately stays **disabled** on Candidates because the picker does not own a provider and must not refresh SEC or Crawl behind the user's back.

The M7 controller clears candidate data if the issuer, source snapshot, or monitoring state changes; M8 activates it only while Finance → Research → Candidates is visible and the Finance window is open.

## HOW TO USE (after reviewed merge and local installation)

1. Open Finance → Research → **SEC EDGAR** to read the public filing index, or **SOURCE CRAWL** to read the saved demonstration export.
2. Select **CANDIDATES** on the same strip. The new view has **BUILD PREVIEW** and **ALL / SEC / DEMO** filters.
3. Press **BUILD PREVIEW** to validate and display the snapshots already in memory. Select a candidate to read its metadata and warnings.
4. Switching issuers or refreshing a source invalidates earlier results. Build the preview again explicitly.

There is **no ADD, ATTACH, SAVE, UPDATE, external URL launch, or background crawling** in the new route. SEC index entries are not inspected or verified documents; demonstration Crawl pages cannot be attached as financial evidence.

## VERIFY

```sh
python3 -B tests/finance/test_research_m8_navigation_contract.py
node tests/finance/test_research_candidate_preview_bridge.mjs
```

M8's CI also runs M1–M7 regressions and the existing FinanceW layout/keyboard/navigation suites triggered by `widgets/FinanceW.qml`. M7's disposable native test loads the actual candidate QML and verifies read-only IPC and issuer-change invalidation. **That does not prove native startup of the full FinanceW PanelWindow or operator desktop acceptance.** The latter remains a separate integration check because the full shell depends on its real Wayland compositor and other live widget services.

## WATCH OUT FOR

- **Shared ownership:** this PR edits `widgets/FinanceW.qml`, so Finance coordination is needed to avoid overwriting parallel Banking, Budget or Market changes.
- **Reconciliation dependency:** do not merge this PR until M7 reconciliation #2315 has been reviewed and landed, or the dependency is otherwise represented in `main`.
- **No production writes:** Research M2 filesystem/crash security acceptance and protected storage authorization remain separate and still HOLD.
- **Visual polish deferred:** this is an added functional tab, not a redesign of the existing Research or diagnostics windows.
- **No local changes:** the operator's Git tree, Quickshell instance and financial records have not been touched.

## NEXT / DECISIONS

After exact-head CI and integration-owner review, merge M7 reconciliation first, then rebase/retarget M8 to current `main` and verify again. Once the operator installs the reviewed branch, perform an actual compact/large desktop click-path test. No merge or production activation is implied by CI.
