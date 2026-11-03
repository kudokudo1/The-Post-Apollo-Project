# Social / Inline Save & Error Feedback v1

PATIENT: kudokudo1/The-Post-Apollo-Project
PROVIDER: OPEN AI // CHATGPT; external Hospital-compatible; no live registered Room or Staff Role
ASSIGNMENT: Control 4 of 7 in the accepted single-page Organizations usability checklist
STATE: Draft repo change. CI, operator merge and live acceptance are separate boundaries.

## IMPLEMENTATION

One read-only LOCAL SAVE STATUS // ALL ORGANIZATION RECORDS line below the existing Search in Social → USER → SETTINGS → ORGANIZATIONS. No new menus or new record action forms.

All seven original owner-local QML store singletons expose state, saved.revision, and errorCode. Their Python writes are asynchronous: a return of true from an editor's action means only that a write was queued, not persisted.

The new observer tracks each store independently. On saving it captures the old revision and displays SAVING. If the same store returns ready with a higher revision it displays SAVED with the store name and revision. A ready result without an advanced revision displays NOT CONFIRMED. A failed writer displays SAVE FAILED with its original backend error code. REVISION_CONFLICT explains that the operator should review their input and reload the affected section before retrying, with no automatic overwrite. A read-only reload shows RELOADED, never SAVED. Current saving/error states take priority over previous success.

The observer has no process, file, write, operation buttons, credentials or backend changes. All original edit/rename/archive/restore/relationship methods remain untouched.

## HOW TO USE

After operator-approved merge and separately approved local update: open Social → USER → SETTINGS → ORGANIZATIONS. Use existing Add, Save, Archive, Restore or Apply Modifier actions. The inline status distinguishes Saving, Saved with revision, Failed with code, and Reloaded. For REVISION_CONFLICT review input, reload the affected section through its existing control and manually retry only after inspecting the result.

## VERIFY

Static contracts assert one-page integration, the original seven stores, revision advancement gating, error codes, and no privileged commands. The real Qt6 offscreen test sends fictional JS snapshots through ready revision 3 → saving revision 3 → ready revision 4, then saving → REVISION_CONFLICT, read-only reload and separate Portfolio save, plus an unconfirmed ready without increment. Existing private-store and genuine Quickshell regression suites remain available; no live data is used.

## WATCH OUT FOR

Revision confirmation is based on the existing local Python writer result, not an independent disk audit or verified company identity. No new source data, storage transaction, backend, permission grant, authenticated company switch or local workstation change.

## CHECKLIST

- [x] Verify merged #1145, GitHub current sources and Syntagma/Hospital protocols
- [x] Observe actual store state/revision/error transitions
- [x] Single inline status, no new menus or backend writes
- [x] Add static and real Qt tests
- [ ] Exact-head CI green
- [ ] Operator review and merge
- [ ] Live desktop UI acceptance

## NEXT

Correct bounded CI issues, hand off to operator. Control 5, unified refresh, is separate and not in this PR.

## DECISIONS

Do not show SAVED on button press or read-only reload. No automatic retry on optimistic revision conflict. No workstation mutation or self-merge.
