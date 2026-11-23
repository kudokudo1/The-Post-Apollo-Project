# FinanceW Research M7 // Explicit evidence candidate picker

**Patient:** `The-Post-Apollo-Project`  
**Room/assignment:** FinanceW Research, M7 in-memory candidate inspection  
**Provider / role:** External Hospital-compatible ChatGPT DOC; no live Hospital registration verified  
**State:** Development staging; no main-menu mount, no new provider or production write authority

## IMPLEMENTATION

M7 builds on M6's bounded, read-only SEC/Demo candidate model.

- `scripts/finance/research_candidate_preview_bridge.mjs` accepts exactly one bounded newline-framed preview request containing already-loaded SEC and/or Crawl snapshots. It calls M6's `previewEvidenceCandidates()` without reading files, fetching URLs, making API requests, or writing to storage. Invalid sources and oversized frames are refused without echoing raw input or stack traces.
- `services/finance/FinanceResearchCandidatePreviewService.qml` is an explicit on-demand controller. It takes the **existing** SEC and Crawl service objects as inputs, serializes only ready snapshots, launches the preview bridge, validates a bounded reply, and discards stale results when the host closes or source identity/state changes. It does **not** instantiate a new SEC, Scrapy, finance or model provider.
- `widgets/FinanceResearchEvidenceCandidatePicker.qml` is an isolated read-only list/detail component. ALL/SEC/DEMO filters operate entirely in memory. A candidate row selects its plain-text metadata, including the official index URL, observed time, and explicit review warning. No URL opens automatically; no attach, create or save signal exists.
- `widgets/FinanceResearchEvidenceCandidatePreviewHost.qml` composes the service and picker, consuming existing reader instances supplied by its future owning FinanceW integration. It does not alter shared `widgets/FinanceW.qml`.

The SEC candidates represent **submissions-index entries, not inspected filing contents**. They carry `reviewed:false` and `authenticatedProvenance:false` and cannot be represented as verified SEC evidence. Demo Crawl pages are labeled non-financial and blocked from downstream attachment.

## HOW TO USE

This code is not installed or mounted on the operator's live FinanceW menu. Once reviewed and separately integrated, the intended interaction is:

1. Enter Finance → Research and use an existing SEC or Crawl source view.
2. Open the evidence-candidate picker and press **BUILD PREVIEW**. This operation processes the snapshots already in memory, rather than making another provider call.
3. Filter **ALL**, **SEC** or **DEMO** and select a row to view its metadata.
4. Leave or change the source to discard the old preview. No data is imported or saved.

The future `ADD TO INVESTIGATION` behavior remains a separate review/authorization boundary. The existing M6 helper can prepare an unsaved manual-source draft, but M7 deliberately does not expose a save or even a draft-submission control.

## VERIFY

```sh
node tests/finance/test_research_evidence_candidates.mjs
node tests/finance/test_research_candidate_preview_bridge.mjs
python3 -B tests/finance/test_research_candidate_picker_contract.py
```

The Research GitHub Actions workflow runs these alongside the M1–M5 regressions. The transport tests exercise normal SEC/Crawl outputs, malformed/spoofed sources, wrong issuer selection, refusal before network/storage, invalid oversized input, and a child that responds even while its parent keeps stdin open.

A QML source contract is **not** native desktop acceptance. The next operator check, only after coordinated menu integration, should verify actual Quickshell component loading, compact/wide selection and scrolling, source/issuer change invalidation, Escape/back behavior and lack of new provider requests.

## WATCH OUT FOR

- No real login or SEC identity attestation is supplied by the preview. Its URLs and labels are informative, not authenticated contents.
- No credential handling, secure M2 mutation, trading, account linking, cross-company files or model-based financial conclusion occurs.
- M2's filesystem and crash/recovery security review stays required for any future persistent investigation writer.
- The diagnostics popup visual bugs remain deferred. This work touches no Weather components, shared FinanceW header, or diagnostic buttons.
- If a future `widgets/qmldir` or `services/finance/qmldir` is introduced, the M7 types must be exported explicitly, avoiding the earlier shared Diagnostics startup failure.

## NEXT / DECISIONS

M7 is a stacked change on the currently open M6 Research branch; do not merge it into main before its base dependency is available and appropriate integration review is complete. No operator desktop modifications, merges, automatic background scanning or native acceptance have been performed. Research ownership is preserved.
