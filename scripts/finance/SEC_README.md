# FinanceW // SEC EDGAR M2

The SEC source is **official public EDGAR company submissions**, not Scrapy
or a paid third-party provider. The endpoint is
`https://data.sec.gov/submissions/CIK##########.json`.
This source requires **no API key**, but SEC fair-access guidance requires
identification and moderate automated use.

## One-time identity setup (no reboot or packages)

The SEC expects your requests to identify the software and a real contact
address. Use a contact email that you control. No contact is provided by
this repository and FinanceW will show SETUP REQUIRED until you configure it.

From your normal **Kitty host terminal**, not inside a QML shell:

```bash
mkdir -p "$HOME/.local/share/post-apollo/finance-sec"
chmod 700 "$HOME/.local/share/post-apollo/finance-sec"
printf '%s\n' 'PostApollo Finance Research YOUR-REAL-CONTACT@YOUR-DOMAIN' \
  > "$HOME/.local/share/post-apollo/finance-sec/user-agent.txt"
chmod 600 "$HOME/.local/share/post-apollo/finance-sec/user-agent.txt"
```

**Replace the placeholder with your actual email before running.** The
script intentionally rejects `example.com`, `example.org`, and
`example.net`. The contact header is transmitted **only to SEC** by the
read-only Node process; never added to the QML snapshot, argv, repo or logs.

## In-window usage

Finance → Research → **SEC EDGAR**, then choose **APPLE**, **MICROSOFT** or
**NVIDIA** and press REFRESH. Source requests are bounded: exactly one
issuer `GET` per refresh, a 12-second timeout, maximum 30 returned
filing rows, no automatic continuous polling, no stored SEC snapshot.
The header says **SNAPSHOT** (not live streaming). Source documents are
shown as their official SEC URLs for inspection.

This is an **issuer watchlist pilot**, not a comprehensive all-SEC feed,
a recommendation engine, or a copy of scraped document content.

Included forms: **8-K**, **4**, **SC 13D**, **SC 13G**, **10-Q**, **10-K**,
and their listed amendments. These are filing metadata records only.
In particular, **Form 4 does not establish buy/sell direction by itself**.
An explicit Form 4 document parser and additional owner-/issuer-specific
filing reconciliation would be separate future work.

We use the fixed issuer CIKs:
- Apple 0000320193
- Microsoft 0000789019
- NVIDIA 0001045810

SEC guidance:
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/about/developer-resources

## Smoke test after merge

```bash
node "$HOME/.config/quickshell/scripts/finance/read_sec_filings.mjs" 0000320193
```

Expected: `FINANCE_SEC_SNAPSHOT` with official filing metadata, or a
`FINANCE_SEC_ERROR` cause. The contact address is not printed.
If SEC blocks the request, leave it in a failed state and inspect the
connectivity and identity rather than retrying rapidly.

To test without SEC connectivity (CI uses fictional records only):

```bash
node tests/finance/test_sec_edgar_reader.mjs
python3 tests/finance/test_finance_sec_contracts.py
```

No Toolbox, rpm-ostree modification, web browser embed, or restart is
needed to **fetch** data. Live FinanceW UI integration still requires
an operator test after review/merge and safe local pull.

## Boundaries

FinanceW Budget mutation gates are unchanged. Polymarket, OSIRIS and
the existing Source Crawl remain separately owned. All SEC contacts
stay outside GitHub. No automatic trades or account access.
