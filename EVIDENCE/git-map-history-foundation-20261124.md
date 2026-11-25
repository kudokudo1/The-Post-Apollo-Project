# DOC 3 // G1 Git Map immutable history and viewport foundation

## Scope and current evidence

Operator approved the full-history map direction with strict scrolling
continuity. This is the first isolated implementation checkpoint; not a
replacement of the live GitW. Source audit at main e2b21138892e98a63157a35b6bce6b6995a2e589:
services/git/GitService.qml requests 48 topology commits, and
components/BranchMap.qml uses a full-height Canvas plus a Repeater over
the loaded model. Neither should simply be expanded to the entire history.
Existing Git evidence, journal, Undo, recovery, Hospital and CPU++ actuator
owners are untouched. External Hospital-compatible DOC 3; no live registration
claimed. Syntagma AGENTS and scope/authority/lifecycle protocols rechecked.

## Implemented

* Standalone Python builder captures local reachable ref tips and HEAD, uses
  Git topology order, writes a fresh SQLite candidate, assigns immutable
  ordinal/SHA/lane records, exact parent endpoints and page boundary lane
  frontier. Refuse unresolved ancestry, duplicate SHA, oversized histories,
  or detected tip/shallow-state changes. No overwrite of an existing index.
* Read-only manifest, aligned 128-row pages and full-SHA lookup. No diffs,
  file contents, journal records, remote fetch or live service queries.
  Candidate directory is explicit, fresh and private. Not encrypted.
* Pure JS viewport controller separates total extent and position from page
  availability. Current viewport before directional adjacent prefetch,
  at most five retained pages; stale request tokens, wrong repository or
  snapshot, malformed rows and cross-page endpoint mismatches refused.
  Data arrival never updates scroll position. Explicit retry and bottom
  states distinguish missing/loading/failed ranges, shallow boundary and
  indexed local end. Replacing a generation needs a matching currently
  loaded anchor SHA/offset and new locate response, or explicit top choice.
* Disposable real Git merge fixture, cross-page merge graph, 100,000-row
  synthetic index and viewport stress tests with out-of-order arrivals,
  failures, rapid jumps, reverse scrolling, repository switch and anchors.

## Limits / decisions

SQLite is a candidate local index, not a migration of the operation journal.
First build is a full traversal; incremental indexing not implemented.
History is reachable from captured local tips and HEAD, not unfetched remote
or unreachable/reflog history. Shallow state is explicit. Tip comparison is
a drift check, not a lock against concurrent ABA/ref changes. Git replacement
objects disabled; local repository metadata can still vary. Initial limits:
1,000,000 rows, 512 lanes, 64 parents per commit, 10,000 tips, 128 rows/page,
5 cached pages. Oversize cases refuse rather than truncate the graph. Author
and subject are bounded display summaries. The candidate helper is a separate
process; real build duration and memory/IO need profiling before live use.
Current tests are backend and pure-policy tests; they do not prove smooth
native Qt rendering, scrollbar/gesture behavior or end-to-end asynchronous
process custody. No live UI, persistent active-index owner or incremental
refresh is installed. Full graph painting across page boundaries still needs
native verification. No automatic builds or polling.

## Next gates

G2: asynchronous bounded page bridge, disposable native viewport with
fixed-height/reused rows and viewport-sized graph canvas. Preserve existing
NeonScrollBar interaction and window lifecycle. Test artificial delays,
direction reversal, bottom clamp, stale responses, cross-page graph and
new-generation anchor. G3: explicit index build/reuse and integration into
GitW with old map fallback and native acceptance. G4: incremental maintenance,
search/jump and PR association. Separately coordinate journal architecture
and remote PR retrieval changes with Git owner. No migration or deployment
authority inferred.
