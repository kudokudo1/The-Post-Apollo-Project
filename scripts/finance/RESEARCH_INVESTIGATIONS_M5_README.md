# FinanceW Research M5 // Read-only source-health diagnostics

**Patient:** `The-Post-Apollo-Project`  
**Assignment:** Research investigation evidence-health analysis, isolated from shared FinanceW navigation  
**State:** Source implementation under review; production writes and native UI acceptance remain HOLD

## IMPLEMENTATION

Research M5 introduces a local evidence-quality check without altering the existing visual layout or investigation records.

- `research_investigation_source_health.mjs` takes an already validated M2-style snapshot and an explicit UTC `asOf` time. It returns stable counts and bounded diagnostic codes. No storage, browser, network, clock polling, or mutation.
- `research_investigation_health_probe.mjs` accepts a single bounded newline-framed **audit** command, executes M2's existing `list` read action only, validates the snapshot and emits a bounded diagnostic report.
- The report counts investigations and evidence; manual links needing review; source-label categories; empty cases; repeated normalized HTTPS URLs **within the same investigation**; records observed in the future; observations older than a configurable day window; and demo-only citations.

### Important provenance distinction

M1's `source:` label is **not evidence of successful SEC/crawler retrieval**, and a local `reviewed: true` flag is **not authenticated provenance**. M5 deliberately reports `provenanceVerifiedByAudit: 0` regardless of the stored labels, and issues this notice:

`METADATA CHECK ONLY // NO WEB FETCH // NO SOURCE AUTHENTICATION`

M5 never calls SEC, EODHD, Alpha Vantage, a scraper, an LLM, or a bank account. It is not financial advice and does not prove a source is correct.

### Privacy and bounds

The diagnostic response contains only revision, timestamps, aggregate counts and up to 100 findings with fixed codes and record identifiers. It does **not** echo original titles, questions, summaries, source URLs, filenames or account data. Additional findings contribute to a complete count and an omitted-findings count. Invalid, corrupt, stale-revision or unsafe documents are refused rather than silently repaired.

The health probe is an explicit read-only process. It never creates `XDG_DATA_HOME` directories or files, and accepts neither arbitrary file paths nor writer arguments.

## HOW TO USE

Run this only in a trusted, private developer environment after your normal Research source checkout:

```sh
printf '%s\n' '{"action":"audit","asOf":"2026-11-23T12:00:00Z","staleDays":180}' |
  node scripts/finance/research_investigation_health_probe.mjs
```

The timestamp is a **fixed example**, not a continuously current value. A future Research UI or diagnostics integration must supply a current trusted UTC timestamp explicitly. No automatic background scan or live Research menu control is being added in M5.

The probe reads only local Research investigations. It cannot inspect private bank accounts or independent live provider feeds. An empty result could mean no Research store has been created; it is not proof that a scan of every financial document occurred.

## VERIFY

```sh
node tests/finance/test_research_investigation_source_health.mjs
node tests/finance/test_research_investigation_health_probe.mjs
```

The dedicated Research workflow runs the M1–M4 regression tests as well. Tests use invented records and isolated disposable directories, including invalid inputs, corruption refusal and a newline-framed process with stdin left open.

## WATCH OUT FOR

- **No actual provenance verification:** SEC-like domain and manual `reviewed` fields are only stored metadata.
- **No new storage authorization:** M2's path, permission, symlink and uncertain-crash concerns remain a separate security acceptance boundary.
- **No repair operations:** Health diagnostics cannot unlock stale write locks, overwrite a corrupt file, or automatically resubmit a mutation.
- **No UI claim:** This is backend functionality for later integration with the user's existing diagnostics surfaces. Current desktop visuals and navigation are unchanged.
- **No automatic activation:** No local installation, merge, Quickshell restart, live bank link or production write was performed by this milestone.

## NEXT / DECISIONS

After exact-head CI, decide whether to expose the new numeric health report through an existing FinanceW diagnostics area. That shared UI integration is a separate coordination step; leave the original visual bugs for the user's planned polish phase. Nurse 2 is required only if crossing storage-security or cross-worker ownership boundaries, not for the pure source-analysis utility.

**Definition of done for M5:** deterministic, read-only diagnostics, strict local-only protocol, no private source text disclosure, and passing automated tests; native display integration remains separate.
