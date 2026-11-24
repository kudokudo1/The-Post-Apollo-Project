# FinanceW Research M9b // Multiple SEC citations in one volatile scratch case

**PATIENT:** The-Post-Apollo-Project  
**ROLE:** External Hospital-compatible FinanceW Research DOC (no live registration claimed)  
**SCOPE:** Research-owned candidate review host, existing M3 Investigations pane, pure M1/M6 bridge, isolated QML/CI tests  
**PRODUCTION / PERSISTENT RESEARCH WRITES:** HOLD

## IMPLEMENTATION

M9a already lets the operator create an ephemeral investigation when **LOAD CASES** finds zero saved cases. M9b lets that same temporary case collect up to the existing **40-source M1 model limit** without activating the separately security-held M2 writer.

- The existing case editor now offers **ADD TO SCRATCH** only when a scratch case is selected, an M9 SEC citation draft is currently prepared, the URL still matches the chosen SEC candidate, title/summary are bounded, and the URL has not already been added. It does **not** enable the old **ATTACH SOURCE** action.
- The new pure Node \`research_scratch_citation_preview.mjs\` takes the current in-memory scratch case, the current M6 SEC candidate, the exact M9 prepared draft and the operator's edited title/summary/URL. It reuses M6 \`prepareCandidateAttachDraft\` and M1 \`validInvestigation\`, \`validEvidence\` and \`attachEvidence\`. It returns a **new** bounded JSON scratch case with one citation in \`evidence\`. It never opens a file or creates a store command. It refuses duplicate URLs, malformed records, forged SEC URLs, excess citations and invalid inputs.
- Quickshell's \`FinanceResearchScratchEvidenceService.qml\` validates the returned case against the previous case, reference count, candidate, expected fields and pre-existing evidence, and ignores stale subprocess results. The host updates only its QML \`scratchCase\` variable.
- **PICK NEXT** switches to the existing candidate list while preserving that scratch case under the same loaded source. Selecting another SEC candidate opens the original case editor again. **BACK** still discards scratch; closing FinanceW or changing SEC/Crawl snapshots/issuers also discards it.
- Individual citations appear in the existing Sources list as **UNSAVED SCRATCH // manual**, with \`reviewed:false\`. They are not authenticated filing-content findings.
- All real M2 \`CREATE CASE\`, \`ATTACH SOURCE\`, \`REMOVE SOURCE\` and persistent writer hooks remain disabled/unconnected. No layout redesign, new provider, external window, account read, or production activation.

## HOW TO USE (after reviewed merge and operator-controlled local update)

1. Finance → Research → SEC EDGAR (load issuer) → CANDIDATES → BUILD PREVIEW.
2. Pick a filing → **REVIEW IN CASE EDITOR** → **NEW SCRATCH** → enter title and question → **CREATE SCRATCH**.
3. **PREPARE UNSAVED** → optionally edit citation title and factual note → **ADD TO SCRATCH**. The URL must remain the chosen official SEC filing index URL.
4. Use **PICK NEXT** → select a *different* SEC filing → **REVIEW IN CASE EDITOR** → **PREPARE UNSAVED** → **ADD TO SCRATCH**. Both citations appear under one volatile case.
5. **BACK** or **DISCARD SCRATCH** deletes all scratch records in this view. Leaving Research/closing FinanceW or issuer/source changes also discards them.

No part of this creates a saved investigation, exports source data, grants SEC authentication or writes a financial account.

## VERIFY

- \`tests/finance/test_research_scratch_citation_preview.mjs\`: canonical M1/M6 validation; two citations, field edits, preservation of the first citation, duplicate URL refusal, 40-source limit, invalid cases, URL spoofing, no executable result command, subprocess completion without stdin EOF.
- \`tests/finance/test_research_m9b_multi_scratch_contract.py\`: QML selection, no M2 writer handler or authorization, case limits, safe subprocess receipt and source-change invalidation.
- \`tests/finance/fixtures/M9bResearchMultiCitationNativeShell.qml\` with its Fedora Quickshell workflow: begins with empty isolated XDG data, creates a case, processes two synthetic SEC index entries, verifies the second entry doesn't erase the first, refuses a duplicate, clears both on source change, and verifies **zero files created**. Existing M7 and M9a native acceptance scripts import the new service dependency and re-run.

Native CI is not the same as operator desktop acceptance. Inspect actual logs and exact commit-head workflow statuses before merging or calling this verified.

## WATCH OUT FOR

Scratch is volatile and lost on BACK, DISCARD, provider refresh, issuer change, view closure or crash. It is not a backup. M2's persistent writer is still a separate security HOLD. A SEC filing-index URL is not inspected evidence; the resulting citation is explicitly unreviewed.

## CHECKLIST / NEXT / DECISIONS

- [x] Reconstruct M9a native acceptance and GitHub current main
- [x] Add memory-only multi-citation append using existing M1/M6 validators
- [x] Support PICK NEXT without discarding the active scratch
- [x] Keep permanent writes disabled, protect against duplicate sources
- [x] Add Node/source/real native smoke regression workflows
- [ ] Exact-head CI and source review
- [ ] Operator-authorized merge, local install and desktop click-path acceptance

The current Research UI's visual appearance remains unchanged except for the two functional actions. Diagnostics polish remains deferred.
