# FinanceW Research M9 // Selected SEC candidate → existing case editor

**Patient:** `The-Post-Apollo-Project`  
**Hospital role:** Research DOC, external Hospital-compatible only (not live registered)  
**Scope:** Existing Research candidate picker/host, existing M3 investigation editor and read-only M4 case loader  
**Status:** Source-only draft. No production persistent writes, merges, or desktop installation.

## IMPLEMENTATION

M9 adds an explicit, **unsaved** citation-preparation step between the selected SEC filing index and the original Investigations editor. It **reuses** rather than clones the existing `FinanceResearchInvestigationsPane.qml` title, URL, factual note and case list.

- The CANDIDATES picker offers **REVIEW IN CASE EDITOR** only for a validated `sec-index` selection, never the synthetic demo Crawl entries.
- The existing M4 local Research read controller is activated only in review mode. **LOAD CASES** triggers one explicit read-only `list` request from the existing M2 file store; it does not initialize or write that store.
- **PREPARE UNSAVED** requires a selected local case and a current SEC candidate. The `research_candidate_draft_preview.mjs` one-shot IPC bridge invokes M6's `prepareCandidateAttachDraft` and refuses duplicates, full/invalid cases, forged SEC URLs, demo candidates and stale key/ID mismatches.
- The response contains **only fields to prefill the existing editor**. It has `readOnly:true`, `preparedOnly:true`, `source:"manual"`, `reviewed:false`, case revision and source identity. It contains no executable attach action, permission or write route.
- Leaving the source, changing issuer, reloading cases, changing selected case or closing the review invalidates draft state. The editor's `writeEnabled:false` remains literal. No `attachRequested`, `createRequested` or `removeRequested` handler is connected.

**SEC INDEX IS NOT AN INSPECTED FILING.** The source URL identifies an index entry only. The operator must separately review the filing's contents before making a substantive conclusion.

## HOW TO USE (after authorized merge and installation)

1. Finance → Research → **SEC EDGAR**; load the issuer's filings.
2. Select **CANDIDATES**, press **BUILD PREVIEW**, then select a SEC filing.
3. Click **REVIEW IN CASE EDITOR**.
4. Click **LOAD CASES** and select an existing local investigation. If no cases are saved, the button stays disabled because Research's persistent-writer security review is not yet approved.
5. Click **PREPARE UNSAVED**. Existing editor fields are populated for review. You may edit the local draft, but **ATTACH SOURCE remains disabled**.

**BACK** leaves the editor and clears its draft. The existing Research tab strip remains unchanged.

## VERIFY

Scoped source tests:
```sh
node tests/finance/test_research_candidate_draft_preview.mjs
python3 -B tests/finance/test_research_m9_editor_contract.py
```

Disposable native Fedora/Quickshell workflow now loads a valid synthetic case in a private `XDG_DATA_HOME` and exercises 30 synthetic SEC rows, candidate selection, case read, unsaved draft prefill and source-change invalidation. It asserts writer-disabled state, no created write lock and byte-for-byte unchanged synthetic store. The fixture never reads personal accounts, real Research records, or a live financial provider.

## WATCH OUT FOR

- Native CI can test QML runtime/IPC behavior; **operator desktop acceptance remains separate**.
- The existing M2 store still requires independent filesystem/custody/crash audit before any live write authorization. No approval implied by reading a synthetic file.
- If the operator has no saved Research cases yet, M9 cannot prepare an attachment for a nonexistent case. That is an honest limitation, not a reason to bypass case validation or enable writes.
- No new account connector, SEC fetch, stored citation, budget mutation, model-generated financial conclusion, or external browser launch.
- The current diagnostics window's cosmetic issues remain deferred.

## CHECKLIST / NEXT / DECISIONS

- [x] Inspect current main, actual M6/M8b and existing Investigation pane
- [x] Reuse old editor and read-only case loader
- [x] Add strict unsaved candidate-to-case bridge and checked in-memory prefill
- [x] Add source, invalid-input, duplicate and spoofing regression tests
- [ ] Exact-head CI and synthetic native acceptance
- [ ] FinanceW integration compatibility review
- [ ] Operator compact/large editor review after authorized merge/install
- [ ] M2 separate write-security authorization before saving

No merge, local device operation or live Hospital registration by this worker.
