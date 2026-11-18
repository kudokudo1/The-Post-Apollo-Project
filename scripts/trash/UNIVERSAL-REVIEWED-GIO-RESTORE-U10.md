# 🏥💜 Trash++ U10 // Reviewed GIO Restore Revalidation

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle · GIO file Restore
STAFF ROLE // External Hospital-compatible DOC, live Hospital registration not verified
ASSIGNMENT // Narrow stale-selected GIO Restore windows after operator-reported U5/U9 native recovery 6/6
SCOPE // Trash-owned CLI, Trash UI, U4/U9 tests and new synthetic U10 tests
PERMISSIONS // GitHub feature branch + draft PR only; no operator-host writes, running GIO against personal files, merge, Burn expansion or Protected Archive authority

## IMPLEMENTATION

Operator reported all six native disposable Camera Gallery -> GIO Trash -> Trash++ Restore checks PASS, including original-path SHA-256 recovery; recorded at U9 #2017 comment 6962934315. U9 #2017 separately proved an isolated real-GIO round trip in CI. U9 Nurse 2 audit identified a listing-to-Restore race.

Before U10 the U4 Quickshell reviewGioFileRestore checked the displayed reviewId and complete-inventory revision, but invoked the CLI with only the selected trash:/// URI and original path. The backend made one fresh inventory, checked exact tuple and destination nonexistence, then called GIO. It never received the UI-approved snapshot revision.

U10 adds a NEW CLI command: restore-reviewed URI ORIGINAL FULL_INDEX_REVISION ROW_REVIEW_ID. The UI now passes both reviewed tokens and the exact row tuple. Backend behavior:

1. Strict lowercase 64-hex revision and row token. No arbitrary full path from generic ActionDeck.
2. Fresh full GIO Trash inventory. Require selected URI+original tuple, full revision equal to reviewed revision and exact row-review hash.
3. Refuse occupied original destination, including symlinks (os.path.lexists).
4. Re-enumerate and require the same GIO executable, same selected tuple, complete revision and review hash; refuse any observed late destination occupancy.
5. Invoke unchanged gio trash --restore URI, with no shell command expansion.
6. After successful GIO exit, require another successful index showing the same URI+original tuple absent and the original target present. If completion cannot be observed, return RESTORE_RESULT_UNVERIFIED rather than a false success or automatic retry.

This is a stronger checked revalidation contract, not an atomic transaction. Unrelated Trash item changes may now cause TRASH_CHANGED_REFRESH_REQUIRED; user refresh/review is the correct path. The new source path does not change Camera's one-use plan, the underlying GIO restore semantics, Restore source ownership, Burn or Burn All.

The existing restore URI ORIGINAL CLI verb is retained for existing callers as an explicitly LEGACY path. The Quickshell reviewed path uses restore-reviewed. No claim is made that callers of the legacy verb inherit full U10 review checks.

The U9 real disposable runner now invokes restore-reviewed for collision, success and stale replay cases; this provides real CI evidence for the new command without touching operator files.

## HOW TO USE

After independent review and authorized merge/sync: Trash++ -> TRASH -> REFRESH -> select the GIO file -> RESTORE. The UI carries the reviewed revision and row token automatically; users do not type CLI parameters. If the listing changed, refresh the list before reviewing again. No changes to Media or protected Archive.

Only CI runs the real-GIO disposable test; never run its fixture directly on the operator workstation.

## VERIFY

- Unit tests inject a changed index between both reads, stale/missing items, wrong review token, incorrect full revision, destination collision before and during the second read, GIO failure, uncertain completion and false post-GIO listing.
- U4 Node tests assert the actual extracted Quickshell Restore reviewer passes correct tokens into the new CLI command.
- Existing all-Trash Python/Node and the separate U9 real-GIO CI step must succeed at exact head. Test with disposable isolated data only.
- U9 real-GIO receipt additionally requires verified:true; the fixture independently compares restored SHA-256 bytes.
- Residual negative proof: even three good lists cannot atomically lock a GIO item against other processes or prevent creation of an original path after the final lexists check. A success receipt confirms only observed post-state, not byte identity of arbitrary user files. The existing U9 CI compares bytes of its controlled file separately.

## WATCH OUT FOR

NOT A COMPLETE TOCTOU REPAIR. There is no documented atomic compare-and-restore precondition on the GIO CLI. The second inventory narrows but cannot close the interval before GIO uses a URI or creates its destination. A real no-overwrite guarantee across competing processes/mounts must be enforced by the actual storage provider/transaction operation or source-owner-controlled staging design; do not infer one from Python's preflight.

GIO trash:/// row token is SHA-256 of URI+original string, NOT file inode, content or provenance. Full revision likewise covers listed tuples, not content identity. An actor who swaps contents while keeping URI/original unchanged may evade these two hashes. Never call them cryptographic authorization credentials.

On an uncertain post-GIO outcome, do not retry automatically. Inspect the actual original path and Trash before any second action. No Burn or Trash Empty action is appropriate in recovery.

No production Archive migration, protected snapshot capture, C3e/C5 approval or remote authority is affected.

## CHECKLIST

- [x] Recheck Syntagma, current main, Trash backend/U4 reviewer and neighboring Media/Archive ownership
- [x] Operator-reported native U5/U9 acceptance checkpoint already persisted to #2017
- [x] Add reviewed CLI with triple inventory, row/revision validation, and poststate uncertainty
- [x] Route UI to reviewed command; update U4 Node tests
- [x] Update U9 real disposable GIO fixture to the new reviewed command
- [x] Add isolated adversarial Python tests; no personal files
- [ ] Exact-head GitHub Trash, U9 real GIO, Node, Grammar / relevant integration checks
- [ ] Independent Nurse 2 review and operator merge acceptance
- [ ] Independent provider-level atomic no-clobber design review, if full concurrent mutation guarantees required

## NEXT

Run all exact-head CI including real GIO. If the existing disposable runner reveals incompatible backend behavior, fix the scoped U10 integration without weakening GIO's source ownership or mocking a pass. On technical green, hand off to independent reviewer and wait for operator merge decision.

A separate future U11 could investigate actual storage-provider atomic no-clobber/trash-row identity primitives and review broad mount/race semantics. That cannot be asserted complete by U10's second snapshot alone.

## DECISIONS

Bounded, additive reviewed command; original CLI compatibility maintained; no production keys, host writes, actual user files or Burn expanded. Rollback: close unmerged U10 PR; remove only U10 new code/test/runbook and reverse its scoped UI/U4/U9 integration. Operator's final acceptance remains separate from CI.
