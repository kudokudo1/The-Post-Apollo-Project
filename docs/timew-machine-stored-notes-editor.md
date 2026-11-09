# MACHINE // STORED checkpoint name and notes editor

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / checkpoint management  
**STAFF ROLE:** External Hospital-compatible DOC, not live Hospital-registered  
**PREDECESSOR:** PR #1665 merged, persistent revisioned annotation sidecar and isolated notes CLI  
**STATE:** GitHub draft / CI and operator acceptance pending

## IMPLEMENTATION

The existing `TimeW.qml` STORED pane now includes **NOTES // RENAME**.
It opens the selected checkpoint's persistent display name and private note,
shows the immutable original label and metadata revision, then permits an
explicit **SAVE NOTES** or **CANCEL // CLOSE**. No preview, new database,
compositor command, browser inspection, or new QML `Process` is added.

To avoid reopening a private note on every checkpoint navigation, names
are overlaid using a separate read-only and bounded query that returns
only annotated checkpoint UUID, display name and revision. The list
never returns personal note bodies. When the editor is opened, the
specific checkpoint is read by canonical UUID.

The editor reuses the existing `machineSaveBridgeProcess` and newly
supported actions:

- `notes-list`: read-only names for the 30 latest checkpoint records
- `notes-read <UUID>`: load only the selected note and revision
- `notes-update`: a single bounded stdin JSON line with ID, display
  name, note and expected revision; invokes the already-merged
  `MachineCheckpointAnnotations.set_annotation`

Only the explicit SAVE NOTES click writes. `MachineCheckpointNotesCLI._input`
remains the shared size/field validator. Note text is never passed in
command-line arguments, sent to Sway or written to Quickshell settings.
The original `checkpoints.label`, saved/captured UTC, v1 JSON, v2 exact
window geometry and geometry checksums are preserved.

## CONCURRENCY AND UX

- The editor binds to the selected saved UUID. Late read/update
  responses for a different checkpoint are discarded.
- Unsaved name/note drafts prevent record navigation, STORED refresh and
  BACK TO CAPTURE. **CANCEL // CLOSE** explicitly discards local edits.
- The backend uses optimistic revision checking; a second editor with
  an outdated revision receives `CHECKPOINT NOTES STALE`. It cannot
  silently overwrite the first editor's changes.
- On an uncertain update process exit the UI reports
  `NOTES UPDATE UNCERTAIN // REFRESH BEFORE RETRY`; it does not
  advertise success or suggest blind retries.
- Newly displayed annotation names are separate from original
  checkpoint labels. A legacy-only checkpoint can be annotated, but its
  geometry verification still reports LEGACY ONLY.
- The STORED panel is already scrollable; the notes text area lives in
  that existing scrollable viewport. No extra window or mode was added.

## VERIFICATION

Dedicated tests execute the real `python3 -B -I` SAVE bridge in a
temporary XDG directory with no compositor socket:

- Empty read-only label list must not create a database
- Reading original legacy checkpoint yields its original name and empty note
- Explicit update changes only the metadata sidecar, increments revision
- Label list returns name and revision but never the private note body
- Second stale update is refused; invalid fields and unknown UUIDs refuse
- Original row bytes, captured timestamps, v1 schema version are unchanged

The QML source contract requires 15 existing processes, distinct SAVE
and RESTORE advanced toggles, and unique root properties. It verifies
the selected UUID, dirty-draft guard, NOTE editor buttons, and original
SAVE/VERIFY/RESTORE interfaces remain.

CI cannot prove live Fedora/SwayPX native widget rendering, focus
behavior, actual user checkpoint writes, or full desktop restoration.
Those require separate operator-authorized local verification.

## NEXT

1. Pass exact-head CI, independently review, and obtain operator decision.
2. Separately approve local sync/Quickshell test and complete the actual
   SAVE DESKTOP → STORED → VERIFY SAVED GEOMETRY cycle.
3. Verify STORED notes/rename persistence across a Quickshell restart,
   stale revision warning and cancellation behavior.
4. Only then design MARK as a real checkpoint transaction and continue
   Brave session correlation and precise geometry RESTORE.

**No merge, local file modification, Quickshell restart or production
restoration is performed by this draft.**
