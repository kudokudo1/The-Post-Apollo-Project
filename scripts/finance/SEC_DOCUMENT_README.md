# FinanceW // SEC Document Inspector M3

Adds manual document inspection to the existing Finance → Research →
SEC EDGAR issuer filing index.

## How to use

After review/merge and safe local update:

1. Select an issuer. Keep the existing SEC contact user-agent file; do not
   reconfigure it.
2. Choose Form 4 / 4-A or 8-K / 8-K-A in the filing list.
3. Press INSPECT in the right-hand pane. This reads only that selected filing.
4. Read the SEC-sourced details or an explicit unsupported/error message.

No continuous polling, automatic crawling, trading, wallets, added Python
packages or new QtWebEngine instance. Selecting a row does not fetch it.

## What is extracted

Form 4: Reads original *raw XML* (not the styled XSL browser view) and
extracts up to 20 non-derivative transactions, reporting owners, transaction
date, security, transaction code, acquired/disposed code, shares, and price.
P is labeled a purchase CODE; S a sale CODE; A a grant/award CODE; M an
exercise/conversion CODE. For P/S rows with numeric shares/price, estimated
notional is shares times price, not a verified cash settlement or gain.

Derivative transactions, footnotes, corrections, full options and 10b5-1
details are not interpreted. No non-derivative rows yields an explicit
unsupported result rather than manufactured values.

8-K: Reads the SEC submissions metadata items field and scans selected
8-K primary HTML/TXT for Item X.XX headings. Shows bounded nearby text,
not AI-written summaries or investment signals. Text near an item heading
may include a table of contents. Exhibits are not fetched.

The inspector supports fixed issuer CIKs Apple, Microsoft, NVIDIA via the
existing allowlist. Other SEC forms stay INDEX ONLY.

## Safety

- Reuses the existing private SEC user-agent file.
- Validates CIK, accession, form and document path before a request.
- One SEC HTTPS request, redirects denied, 12s timeout and 2MB byte cap.
- No automatic retry or Quickshell startup request.
- Selection change invalidates detail so a response is not misattributed.
- Original SEC document URL remains visible.
- No credentials or raw document content committed to GitHub.

## Offline verification

Run in the repo after pull:

    python3 tests/finance/test_sec_document_inspector.py
    python3 tests/finance/test_finance_sec_document_contracts.py
    node tests/finance/test_sec_edgar_reader.mjs

Tests use fictional XML/HTML and injected fetchers. GitHub CI passing
does not prove SEC document access on the operator's actual desktop.

Official source references:
- https://www.sec.gov/about/developer-resources
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
