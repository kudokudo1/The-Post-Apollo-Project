# FinanceW Research M8a // Populated-candidate handoff recovery

**Patient:** The-Post-Apollo-Project  
**Role:** FinanceW Research DOC, GitHub-only source changes, no live Hospital registration claim  
**Scope:** M7 read-only candidate preview service, host diagnostic state and disposable Quickshell regression  
**User report:** SEC EDGAR displays 30 Apple filings on the operator desktop, but switching to CANDIDATES and pressing BUILD PREVIEW results in 0 items and PREVIEW REFUSED.

## IMPLEMENTATION

- Reproduce the **populated** (30 SEC + one demo) case with an isolated, synthetic, real Quickshell smoke fixture. The original M7 smoke tested just one SEC record, and the first expanded fixture needed its demo index corrected to position 31.
- Preserve the existing M6 SEC/archive validation, no provider requests, no external URL openings, and M2 persistent-write security HOLD.
- The M7 bridge already emits a **fixed** error code to stderr, but its QML controller discarded stderr and replaced every failure with an unhelpful generic message. Add a bounded, allowlisted `FINANCE_RESEARCH_PREVIEW_REFUSED` code in the status text and console. Do not echo source URLs, filing titles, SEC User-Agent, raw stderr or snapshot JSON.
- Handle process exit and relevant `StdioCollector` stream completion as **independent asynchronous events**. For success, wait for stdout; for refusal, wait for stderr. A short fail-closed deadline prevents indefinite LOADING if the expected stream never completes. Never retry a write or fetch a provider in response.
- Extend the native smoke to (a) validate all 30 SEC entries plus one demo, (b) verify issuer-change invalidation, and (c) deliberately submit a wrong-issuer snapshot to assert a bounded `INVALID_SOURCE_SNAPSHOT` refusal.
- Extend Node tests with 30 filings normalized through the existing SEC reader, Form 4 XML paths and 8-K filing rows. Verify the output stays inside the existing IPC size limits.

## HOW TO USE

**After independent source review, authorized merge and operator-controlled local update**:

Finance → Research → SEC EDGAR → wait for populated filings → CANDIDATES → BUILD PREVIEW. Expected: **SEC INDEX 30 / DEMO 0** if only SEC source was loaded. Select an entry and read its metadata. If the preview still fails, the status and Quickshell logs now provide a safe refusal code, e.g. `INVALID_SOURCE_SNAPSHOT` or `STREAM_INCOMPLETE`.

The new error codes allow a focused next diagnosis without requesting the user's actual SEC snapshots, credentials or raw data.

## VERIFY

```sh
node tests/finance/test_research_candidate_preview_bridge.mjs
python3 -B tests/finance/test_research_candidate_picker_contract.py
bash scripts/finance/verify_research_candidate_native_m7.sh
```

The last command must run only in a disposable Fedora/Quickshell/Xvfb CI environment, not against the operator's running desktop; GitHub Actions provides this environment.

**Important limitation:** Synthetic 30-row acceptance does not prove that the user's particular live SEC response has passed M6's strict source checks. The new safe refusal code determines that at the next native operator test.

## WATCH OUT FOR

- `INVALID_SOURCE_SNAPSHOT` means the bridge refused the source based on its existing validation. Do not bypass or weaken the SEC source/URL validation just to fill the picker.
- `INVALID_RESULT_STREAM`, `EMPTY_RESULT_STREAM`, or `STREAM_INCOMPLETE` implicates the local IPC/collector handoff, not the SEC connection.
- No new provider service, automatic crawler run, account link, financial write or research evidence attachment.
- Local workspace edits, installs, merges and shell restarts require separate operator authorization.
- Research's existing visual-polish and diagnostic-window changes stay deferred.

## DECISIONS / NEXT

Keep this as a small read-only Research recovery PR. Verify exact-head CI and compare the resulting safe failure code on the operator's desktop after review/merge. Preserve M2 security HOLD until its separate review; do not count synthetic CI as final native acceptance.
