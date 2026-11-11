# Trash++ // V2f Explicit Pilot Source Snapshot Controls

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal lifecycle
PROVIDER // OPEN AI // CHATGPT
STAFF ROLE // DOC-compatible development
CONNECTION // External, no verified live Hospital registration
ASSIGNMENT // Attach existing owner-witness V2b preview/capture to the single Archive UI
PERMISSIONS // GitHub branch / draft PR only. No local Quickshell writes, merge, production activation, source writes or destructive permission expansion.

## IMPLEMENTATION

- Adds SAVE SNAPSHOT beneath the existing legacy SAVE COPY button on exactly two allowlisted original source rows: Weather EVENT HISTORY and disposable quotes.toscrape.com WEB SCRAPE. Saved snapshots, Hub data, Hospital, Identity and other source rows never gain this control.
- First click launches a dedicated process with preview: it reads the selected source through the existing V2b strict owner reader and returns a SHA-256 source revision witness and display metadata only. **It does not create an Archive database or store any copy.**
- The first click changes the button to CONFIRM COPY. Second click supplies the expected source witness to the new snapshot capture process. It re-reads the source, verifies exact selected content and timestamp, then stores one independent immutable copy in the V2a SQLite archive.
- A source rewrite, missing source, invalid identity, duplicate snapshot, malformed witness, symlink or disallowed owner fails closed. The owner source is never edited, deleted or restored.
- The V2f CLI has exactly the preview/capture verbs. It imports trusted app-root Python modules even when invoked through the existing python3 -I -B Quickshell convention.
- Preview and capture share the same normalization and source validation via new PilotSnapshotReader and existing PilotSnapshotAdapter subclass. The old PilotSnapshotAdapter public API remains intact.
- V2 copies remain read-only in the Archive list. No V2 Trash/Restore/Burn action is offered, even after successful capture. The existing V1 managed-copy Trash/Restore/Burn actions and their permissions are unchanged.
- Dedicated snapshotCaptureProcess and bounded state machine are separate from GIO, managed-copy and read-only V2 index processes.
- Closing the menu cancels an uncommitted preview, but an already-confirmed capture is allowed to finish; a validated receipt reports its outcome without inventing success. No auto-save, auto-copy, background scanner or scheduler is added.

## HOW TO USE

After separately authorized merge, local installation and native verification:
1. Open Trash++ > ARCHIVE.
2. For an approved Weather event or demo research source row, click SAVE SNAPSHOT.
3. After SOURCE CHECKED is shown, click CONFIRM COPY on that same row.
4. On successful capture, see SAVED // INDEPENDENT READ-ONLY COPY and refresh the V2 index. The snapshot appears under the existing ALL/COPIES filters.
5. If the original record changes between preview and confirmation, the request is refused; refresh the source inventory and start again.

SAVE COPY remains the older **managed** copy operation with independent V1 Trash/Restore/Burn permissions. SAVE SNAPSHOT is the newer immutable **read-only** copy; those two actions are intentionally distinct until separately approved migration/retention rules exist.

## VERIFY

Run Trash Bottom-Left Launcher CI and Meta Apollo Grammar. Synthetic tests cover:
- Preview without database creation or leaked source payload
- Correct CLI execution under Python isolated mode
- Both approved owners and rejection of other owners/arbitrary paths
- Source bytes unchanged after capture
- Source revision mismatches including same-timestamp rewrites
- Exactly-once snapshot identity: duplicate refusal
- Two-click UI preview/confirm dispatch
- Close-after-preview and close-during-capture state
- Legacy V1, GIO/Camera and Burn isolation.

GitHub CI cannot verify live Quickshell installation or the host's private data root ownership. A Native four-chassis visual and real approved demo/Weather test is still required after explicit local deployment permission.

## WATCH OUT FOR

- Source witnesses are not permission credentials. This pilot only authorizes two previously allowlisted, independently disposable source families; future owners need separate contracts.
- SQLite payload quota (default 512 MiB) is **not** a whole-database disk quota. Full file/system quota, backup and recovery guarantees remain separate work.
- Snapshot integrity digest protects payload bytes; metadata authenticity and signed provenance are not yet sufficient for automatic restore/deletion decisions.
- The CLI's input data root is host-provided, not an arbitrary UI path. All source path selection is fixed inside existing owner readers. The Python process still runs as the desktop user; same-UID hostile processes are outside the scope of this pilot.
- V1 managed copies and V2 read-only copies are two distinct storage models. Avoid treating the latter as a replacement for managed deletion workflows.
- Confirmation and live visual tests must ensure that temporary previews do not become permanent pending state when the user changes menu or closes it.

## CHECKLIST

- [x] V2e merge status, GitHub HEAD and overlapping Trash++ owner PRs checked
- [x] Preview-only reader does not create a DB
- [x] Dedicated fixed-verb preview/capture CLI
- [x] Explicit source-only two-step Archive UI
- [x] Separate V1 and V2 destructive permissions
- [x] Synthetic Python and JS tests plus CI workflow
- [ ] GitHub CI pass and bug corrections
- [ ] Independent security, native compact/medium/large/full UI tests
- [ ] Operator approval to merge and deploy on live desktop

## NEXT

Verify CI, correct any failures, then obtain independent security and user visual review before merging or enabling on the host. Future separate milestones: disk-footprint quotas, provenance metadata, evidence-safe source consent, recovery/restore contracts and retention/Burn protocols. No protected data owner expanded in V2f.

## DECISIONS / RECOVERY

RECOVERY BRANCH // feat/trashpp-pilot-snapshot-capture-v2f-20261110
Rollback // revert only this PR. No data migration or deletion. V2a/V2b/V2e existing APIs and V1 managed/GIO records remain as they were.
STATE // awaiting CI, independent review and operator acceptance, never autonomous production activation.
