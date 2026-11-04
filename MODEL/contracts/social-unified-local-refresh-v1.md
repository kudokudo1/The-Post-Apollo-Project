# Social / Unified Local Refresh v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT, external Hospital-compatible; no verified Room, Assignment or Staff Role.
ASSIGNMENT: Control 5 of seven approved usability controls, one-page Organizations manager.
STATE: Draft PR, unmerged, not deployed or operator accepted.

## IMPLEMENTATION

Use one REFRESH ALL button near existing Search and Save Status on Social → USER → SETTINGS → ORGANIZATIONS. Do not add a workspace, menu or change button sizes. It calls the seven ORIGINAL QML stores' refresh methods: local Organizations/Branches, Portfolios, Structure, Function/Location, Branch/Location, Functional Reporting, Social Associations.

Prior refresh controls in the three record editors and the in-place Modifier editor are hidden while the editors are embedded in the shared page. They still exist, unchanged, for standalone use (useSharedRefreshControl defaults false). All save/archive/link/unlink, store concurrency, revisions, private JSON permissions and actual writer methods remain untouched.

The top-level REFRESH ALL is conservatively admitted ONLY when all seven stores are available and in ready or error, and none is already loading/saving or has an in-progress refresh. Seven calls to the existing read-only refresh functions are then requested. Each store's original refresh method can still refuse independently; report accepted count and partial failures instead of falsely claiming seven reloads. Display busy/unavailable, started, completed, partial and exact backend read errors. Do not queue duplicate reads from repeated clicks and do not automatically retry conflicts or writes. Save Feedback remains the authoritative observer of write outcomes.

## HOW TO USE

After operator-authorized merge and separately approved local code update: Social → USER → SETTINGS → ORGANIZATIONS → REFRESH ALL. Press once; the status line shows activity and completed/error result. While loading or saving, the button is disabled rather than interrupting a write. On any error review the store's error status before retry; no automatic retry. Each original editor remains on the same page.

## VERIFY

New source contracts check the seven direct existing refresh calls, no writes or auth, all-or-none preflight, original editor standalone compatibility and single-page composition. An actual Qt6 offscreen Settings test uses seven synthetic writable JS store objects with refresh counters to verify disabled while saving/loading, one call to every store, duplicate-call blocking, completion, error reporting and no accidental write. Existing local storage and genuine Quickshell persisted-reload workflows remain separate checks.

## WATCH OUT FOR

A read-only refresh is NOT an import or restore, does NOT write to disk, does NOT resolve an optimistic revision conflict, and does NOT establish verified company access. Refresh may reveal changes made by an outside process; preserve unsaved draft text in original input fields. All original store methods still guard concurrent operations, so any refusal remains visible as partial. No live workstation or Quickshell restart authorized.

## CHECKLIST

- [x] Reconstruct current main and merged Save Feedback #1154
- [x] Check Syntagma/Hospital authority and overlapping PRs
- [x] One shared guarded read-only refresh with truthful per-store status
- [x] Hide duplicate controls only while embedded
- [x] Source + real Qt test coverage
- [ ] Exact-head workflows pass
- [ ] Operator review and authorized merge
- [ ] Live desktop acceptance

## NEXT

Fix any bounded CI issues and hand off. Next controls after operator review: validated local backup/export and restore/import, then a local activity/history view. Only once controls are placed should the separately scoped color/opacity/glow pass begin.

## DECISIONS

Preserve current button dimensions and one-page flow. A repeat click proves intent but does not authorize duplicate work or bypass a store's safety guard. Color semantics are recorded separately, not applied to code here. No self-merge or local machine writes.
