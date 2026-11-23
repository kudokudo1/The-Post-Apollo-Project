# FinanceW Research M2 // Local Investigation Store

## Dependency
This branch depends on Research M1 draft PR #2199. It must be reviewed against the M1 schema before any integration, and must not be merged independently onto a branch missing M1.

## Purpose
A private, local-only file store for manually named Research investigations and small, cited factual evidence entries. No QML menu wiring yet, no OS file modifications during GitHub development.

Entry point: `scripts/finance/research_investigation_store.mjs` (Node ESM).
Data root: `$XDG_DATA_HOME/post-apollo/finance/research-investigations/` or `~/.local/share/post-apollo/finance/research-investigations/`.
The file `investigations.json` is readable only by the local user (0600); the final directory is 0700. The only normal output is a bounded versioned JSON document.

## Protocol
Single newline-terminated JSON request on standard input:
- `{"action":"list"}`: read without creating the directory.
- `{"action":"create","expectedRevision":0,"id":"example-1","title":"Example","question":"What is the evidence?","timestamp":"2026-11-22T20:00:00Z"}`
- `{"action":"attach","expectedRevision":1,"investigationId":"example-1","evidence":{"id":"edgar-1","source":"sec-edgar-submissions","title":"Example SEC filing","summary":"Factual description","url":"https://www.sec.gov/Archives/edgar/data/320193/example.htm","observedAt":"2026-11-22T20:00:00Z"},"timestamp":"2026-11-22T20:00:00Z"}`
- `{"action":"remove","expectedRevision":2,"investigationId":"example-1","evidenceId":"edgar-1","timestamp":"2026-11-22T20:00:00Z"}`

Writes require the exact current revision, return a new one and never retry. All mutation commands are explicit. Input is bounded to 8 KiB. The output is `FINANCE_RESEARCH_STORE_RESULT <json>` or a code-prefixed error on stderr.

## Safety and recovery
- Atomic temporary file, fsync and rename, plus fsync on directory.
- Existing data is never overwritten when corrupted, symlinked, world-readable, or larger than the bound.
- The private writer uses an exclusive create lock. A crash can leave `investigations.lock` behind; this **intentionally blocks** future writes rather than guessing whether a previous write succeeded. Inspect the stored document and investigate the holder/crash before any manual lock cleanup. Never automatically remove a stale lock or retry a financial/research write.
- Research findings are **not authenticated evidence** merely because a URL was saved. Facts should retain source attribution, and any future AI-generated analysis must be labeled separately.
- This is not encrypted storage. Never save credentials, financial account numbers or tokens, confidential household data, or raw bank statements.
- M2 has no direct network calls, brokerage calls, SEC requests, bank transfer, or Quickshell integration.

## Tests
```sh
node tests/finance/test_research_investigations.mjs
node tests/finance/test_research_investigation_store.mjs
```
Tests cover revision gating, persistence round-trip, corruption refusal, symlink and permissive-file refusal, writer lock and exact command shape. Automated tests were added but results must be verified at exact PR head before review completion.

## Follow-on M3
Build a Research-owned QML pane and a bounded QML-to-Node bridge with carefully separated load and explicit save states. Shared `widgets/FinanceW.qml` navigation wiring requires Nurse 2 coordination, and live operator acceptance requires separate approval.
