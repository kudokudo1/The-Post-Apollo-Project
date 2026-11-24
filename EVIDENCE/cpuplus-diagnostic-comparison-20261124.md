# CPU++ DOC 3 // M3b.7 Archived capture comparisons

## Checkpoint

PR #2520 persistent archive merged; its diagnostic workflow passed.
Operator reported the archive worked. Exact restart, eviction and failure
acceptance coverage is not specified by that statement.

## Use

CPU++ SYSTEM > MEMORY/SWAP > DIAG > LOAD HISTORY. Select a completed
capture and SET BEFORE. Select a newer completed capture of the same
type and SET AFTER. COMPARE CAPTURES displays both measurements and
AFTER minus BEFORE. Percentage deltas are percentage points. The
selection IDs survive pane reconstruction within a shell session.
Evicted/unavailable records do not substitute a newer capture.

## Evidence boundaries

- Memory: starting/peak/final PSS, trapezoid time-weighted PSS mean,
  net PSS change, peak SwapPss, time-weighted CPU and peak CPU.
- Threads: interval-weighted CPU, peak and main-thread mean where
  available, count peak. Short-lived threads may be missed.
- Census: final interval coverage, process count and returned unique
  exact-name Quickshell RSS, CPU and storage rates. This does not prove
  identity or absence of omitted matches. No totals from top-N rows.
- Inventory: declaration counts, not live activity.
- Complete records only, distinct chronological IDs, same tool.
  Truncated census, malformed records and unequal durations are
  rejected or visibly qualified as appropriate. N/A is not zero.

This is a descriptive comparison, not an automated benchmark, patch
provenance witness or causal verdict. Archive v1 does not store deployed
commit, dirty tree, workload actions or environment. Record these
separately for controlled comparisons. Eight-capture rolling limit
remains; no pinning or retention change in this milestone.

No new process, timer, file format or shared notification changes.
Independent review and native operator comparison pending. Next:
per-service storage activity attribution, then GPU diagnostics.
