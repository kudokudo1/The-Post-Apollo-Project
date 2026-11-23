# FinanceW Research M8b // SEC/Crawl candidate source-contract parity

**Patient:** `The-Post-Apollo-Project`  
**Assignment:** Research candidate preview validator / read-only bridge  
**Role:** Hospital-compatible external Research DOC, no live registration asserted  
**Release state:** Draft PR, operator local acceptance and merge pending

## IMPLEMENTATION

Operator's Quickshell screenshots show SEC EDGAR with **30 Apple filings** followed by CANDIDATES → BUILD PREVIEW → `INVALID_SOURCE_SNAPSHOT`.

The source audit found a **deterministic upstream/downstream schema mismatch**:

- `scripts/finance/crawler/finance_demo_source_spider.py` emits `observedAt: datetime.now(timezone.utc).isoformat()`, e.g. `2026-11-23T14:42:00.123456+00:00`.
- `scripts/finance/read_scrapy_crawl.mjs` accepts and retains that UTC-offset, microsecond timestamp.
- `scripts/finance/research_evidence_candidates.mjs` previously accepted only UTC `Z` timestamps with at most three fractional digits for **both** SEC and Crawl, rejecting legitimate Spider output.
- If the saved Crawl reader is READY when a populated SEC snapshot is previewed, a demo-source rejection aborts the **combined** preview and suppresses otherwise valid SEC rows.

M8b preserves the SEC `Date.toISOString()` validation and adds a separate strict RFC3339 timestamp check for **Crawl only**. It accepts up to six fractional digits and ISO timezone offsets, while refusing arbitrary date prose, excessive precision and invalid offsets. All SEC URL, issuer/CIK, filing, hostname, source-type, bound and no-write checks remain.

The read-only bridge now forwards **only a predefined fixed set of M6 failure codes** rather than collapsing all validation errors to `INVALID_SOURCE_SNAPSHOT`. Examples: `INVALID_SEC_FILING`, `INVALID_SEC_URL`, `INVALID_DEMO_PAGE`, `INVALID_DEMO_COUNT`. The Quickshell controller allowlists the same codes. Source filenames, URLs, SEC User-Agent, contents and raw exception messages are not printed.

## HOW TO USE

After authorized review/merge and operator-controlled local update:

Finance → Research → SEC EDGAR (load filings) → CANDIDATES → BUILD PREVIEW → SEC.

If saved Crawl data is READY, a valid Spider timestamp should no longer blank the SEC candidate list. The zero-data/Crawl-missing path remains valid. If another malformed record exists, the status now names the **validation stage** without revealing source data.

## VERIFY

Node and Quickshell regressions use synthetic 30-SEC-plus-one-Crawl snapshots, with the **exact timestamp format emitted by Python's spider**. They assert read-only preview success, full SEC candidate count, demo-source attachment prohibition, hostile timestamp refusal, and safe source error codes.

The native Fedora/Quickshell fixture uses microsecond UTC-offset demo data. It checks subprocess startup, loaded candidates, issuer-change invalidation, refusal stage and no Research write.

## WATCH OUT FOR

- The source mismatch is confirmed in repository code; whether it was the **sole** cause of the operator's exact live failure requires a new desktop retest.
- Do not downgrade SEC URL or source validations to make invalid data appear.
- The demo Crawl stays non-financial and ineligible for investigation attachment.
- No new source fetch, credential permission, persistent Research storage write, bank link, or external window.
- M2 persistent writer security **HOLD** remains unchanged.
- Do not modify the operator's local Git working tree, activate production, or merge without authorization.

## NEXT / DECISIONS

Obtain exact-head CI on M8b. Keep this as a Research-owned source/bridge correction; defer the diagnostics visual polish. After source review and authorized merge, verify the populated Apple source preview in actual FinanceW. Only then resume M9 selected-candidate investigation drafting.
