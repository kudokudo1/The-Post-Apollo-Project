# FinanceW Research // Investigations M1

## Purpose
First isolated foundation for reusable Research investigations. This is an opt-in *data contract*, not yet a menu button or durable local file store. It does not touch `FinanceW.qml`, budget data, third-party accounts, live funds, or shared navigation.

## Audit of existing sources (2026-11-22)
- `FinanceResearchCrawlPane.qml` displays a bounded previously exported Scrapy snapshot. The reader deliberately accepts only `https://quotes.toscrape.com/` and at most six pages; it is a demo, **not** a generalized web-finance crawler.
- `FinanceSecFilingsPane.qml` reads public SEC submissions for three fixed issuers (Apple, Microsoft, NVIDIA), up to 30 selected filings. The operator supplies the SEC user-agent contact outside the repository.
- `FinanceSecDocumentInspector.qml`, `FinanceSecEvidenceCompare.qml`, and `FinanceSecPriceContext.qml` support opt-in inspection, two-source SEC comparison, and date-based optional historical price context. No direct trade signals or causality claims.
- Existing evidence pins live only in QML memory and disappear on issuer refresh/switch. M1 does not change that behavior.

## M1 contract
`scripts/finance/research_investigations.mjs` exports:
- `createInvestigation`: immutable addition of an investigation (question, title, timestamps).
- `attachEvidence`: immutable addition of a cited source entry with URL and observed time.
- `removeEvidence`: immutable removal of one explicitly selected evidence entry.
- `validateCollection` and `parseCollection`: validation for any future file-backed store.

Boundaries: at most 50 investigations, 40 cited sources each, bounded text, unique IDs, precise source provenance. SEC URLs must be official SEC archive HTTPS links; the existing demo crawl is restricted to its known host. Unsupported source types are refused; `manual` records still need an HTTPS source URL. No AI conclusions are implicitly promoted to evidence.

This module performs **no filesystem writes** and makes **no requests**. A future persistence service should add atomic writes, private local permissions, explicit user save/load and corrupt-record recovery. It must not save credentials, account statements, bank tokens, personal identifiers, or unreviewed raw scraped content.

## Verify
```bash
node tests/finance/test_research_investigations.mjs
```

The test covers immutable updates, source validation, URL spoofing, duplicate IDs, size bounds and round-trip JSON. GitHub Actions evidence and live Quickshell acceptance must be verified separately.

## Follow-on work / collision boundary
1. Nurse 2 independently reviews policy and source-to-record mapping.
2. Add a guarded, local-only store and its crash/corruption tests in separate Research-owned files.
3. Build a new Research investigations pane component and test small/medium/wide layouts.
4. Ask the shared FinanceW navigation owner to wire the pane through a tiny integration PR; no unilateral changes to `widgets/FinanceW.qml`.
5. Operator acceptance of local UI and future research workflow. No provider/API activation or financial actuation in this milestone.
