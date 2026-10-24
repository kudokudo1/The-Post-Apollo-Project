# FinanceW // SEC Evidence Desk M4

## Goal

Make the existing live-tested SEC Form 4 and 8-K inspector more useful
without inventing investment signals or adding a new data backend.

## Use in Finance → Research → SEC EDGAR

**Filing filters**: ALL, INSIDER, 8-K, OWNERS, REPORTS. This filters only
the current bounded SEC issuer snapshot (up to 30 recent matched filings).
It is not a comprehensive SEC-wide search or an all-time history.

**Transaction filters**: Once you select Form 4 and press INSPECT, filter
non-derivative transactions by ALL, P (purchase code), S (sale code),
A (award code), M (exercise/conversion code) or OTHER. The filter only
controls the displayed rows: it never changes or refreshes source records.

**Pin and Compare**: Inspect a supported filing, press PIN, inspect another
filing from the same issuer, press PIN again and then COMPARE.
The comparison shows two documented sources side-by-side in wide views
or stacked in compact views. Each card includes the original SEC link,
filed date, reporting owner/code counts or 8-K item classifications.
Press DETAIL to return to the current filing; CLEAR removes both pins.

A third pin replaces the oldest. Re-pinning the same filing updates
its slot instead of creating a duplicate. Refreshing or switching
the issuer invalidates both pins. The cards exist only in local
Quickshell memory; nothing is saved or synchronized.

## Provenance and limits

This is a factual **source comparison**, not an economic correlation,
prediction, insider-trading signal, or proof of intent.

- SEC Form 4 counts are based on only up to 20 parsed non-derivative
  rows per inspected filing. P and S are reported codes, not necessarily
  voluntary open-market economic exposure after footnotes.
- 8-K card item classifications can come from source metadata or from
  detected headings; nearby text is not an authoritative complete summary.
- No stock-price or Polymarket history is read in M4, and no relationships
  to other organizations are inferred.
- No SEC network request is made by PIN, COMPARE, CLEAR or filters.
  INSPECT remains the single request gate and reuses existing SEC identity.
- None of the Budget mutation gates or FinanceW geometry are changed.

## Verify

    node tests/finance/test_sec_evidence_policy.mjs
    python3 tests/finance/test_finance_sec_evidence_contracts.py

Other SEC / FinanceW tests remain in CI. Live three-size mouse/scroll
testing is operator acceptance, not covered by GitHub source contracts.
