# FinanceW Research M6 // Existing source snapshots → evidence candidates

**Patient:** `The-Post-Apollo-Project`  
**Assignment:** Research-owned, read-only candidate preparation connecting existing SEC and demo Crawl data shapes to the M1 investigation model  
**Status:** Source staging under review. No live Research storage writer, FinanceW navigation, provider activation, or operator desktop changes.

## IMPLEMENTATION

This milestone adds `scripts/finance/research_evidence_candidates.mjs`. It reuses the *actual outputs* of:

- `scripts/finance/read_sec_filings.mjs`: official EDGAR submissions index for Apple, Microsoft and NVIDIA, restricted to 30 current filings and a selected CIK
- `scripts/finance/read_scrapy_crawl.mjs`: bounded, saved demonstration scrape from `quotes.toscrape.com`, not live financial evidence
- `scripts/finance/research_investigations.mjs`: current investigation and evidence validation
- `scripts/finance/research_investigation_write_contract.mjs`: existing future write-intent format, **not invoked by the new module**

`previewEvidenceCandidates({secSnapshot, crawlSnapshot, selectedCik})` returns a maximum of 36 read-only candidates. Missing sources and verified empty snapshots are explicitly distinct. Inputs are checked for source label, schema, read-only marker, limits, date shape, issuer/CIK match, duplicate accession/URLs and canonical SEC archive URL construction. No network, disk, external provider, clock, or background request is performed.

SEC entries are labeled `sec-index` and explicitly state **the underlying document has not been inspected**. They receive `authenticatedProvenance:false` and `reviewed:false` even though their path is consistent with the existing SEC reader contract.

Demonstration Crawl entries are labeled `demo-crawl`, `eligibleForDraft:false` and explicitly state **NOT FINANCIAL EVIDENCE**. They can be displayed for inspection but cannot become a draft via this bridge.

`prepareCandidateAttachDraft(candidate, investigation)` can produce an *unsaved form intent* from one SEC index candidate after validating an existing M1 investigation. It refuses duplicate saved source links, full cases, invalid/synthetic URLs, and demo candidates. The resulting proposed attachment has only `action`, `investigationId`, `title`, `summary` and `url`, matching the existing M4b preparation contract. M4b later creates a fresh ID and stamps `source:"manual"`, `reviewed:false` if a separate, protected write path is eventually approved.

**This is not a SAVE or an import action.** A user reviewing a candidate is still responsible for opening and evaluating the underlying filing. Source data is not automatically treated as a conclusion, proof of intent, financial advice or authenticated evidence.

## VERIFY

```sh
node tests/finance/test_research_evidence_candidates.mjs
```

The fixture derives actual SEC and Crawl snapshot structures using their existing normalization functions, then checks M1/M4b interoperability without calling the store. Tests cover source tampering, wrong CIK, domain spoofing, document traversal, duplicate accessions/links, stale source dates, demo prohibition and exact draft fields. The dedicated Research CI also runs M1–M5 regressions.

## HOW TO USE

Development-only library until an independently coordinated UI integration. No new button or popup in FinanceW is authorized. Later, Research could show a selected SEC filing as an **ADD TO INVESTIGATION (REVIEW FIRST)** candidate, and the existing editor could prepopulate the manual citation fields after explicit selection. The user would still need a separately authorized save, and the current M2 storage security HOLD is unchanged.

## WATCH OUT FOR / DECISIONS

- Snapshot validation detects obvious malformed or misleading data; **it does not establish remote SEC identity, signatures or provenance**.
- This milestone does not fetch filings, execute a crawler, save records, unlock the store, change household finances, or call a language model.
- Crawl remains demonstration content and does not silently enter financial investigations.
- No shared `FinanceW.qml` changes or Weather/Diagnostics changes. Existing visual polish stays deferred.
- Changes to SEC/Crawl readers or eventual navigation require their owners' coordination. Live persistent writes require the separate M2 filesystem/crash security review.

## NEXT

After exact-head CI, stage a read-only candidate picker against the existing source snapshots in an isolated component, then coordinate the narrow FinanceW integration. Do not interpret CI or draft creation as native/operator acceptance.
