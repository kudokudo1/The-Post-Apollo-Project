# MACHINE // Persistent MARK NOW in the normal SAVE screen

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / desktop checkpoints  
**ROLE:** External Hospital-compatible DOC, not live-registered  
**Scope:** Named persistent MARK, not full Brave/tab reconstruction  
**Predecessor:** M2 SAVE verified receipt and PR #1669 STORED notes/rename

## Purpose

The historical `MARK` button made a session-local in-memory timestamp,
never a desktop checkpoint. It disappeared after Quickshell restarted and
could not be selected in STORED. A user reasonably expected MARK to make a
named, recoverable point in time instead.

This milestone adds a new **MARK NOW** next to SAVE DESKTOP. The operator can
name the moment (40 characters maximum) or leave it blank. Blank uses the
existing shared Post-Apollo Clock readout. The generated checkpoint name
has the prefix `MARK // `, has at most 48 characters, and uses the same
`MachineSaveBridgeV2.py save` operation as normal SAVE DESKTOP.

## Data mechanism

MARK:
1. Receives the name from the user or local Clock display time.
2. Calls exactly the same `machineBeginSaveBridge("save", {...}, "mark")`
   path as ordinary geometry SAVE. No required preview or new process.
3. Captures Sway outputs, workspaces and geometry with the existing
   two-observation stability check.
4. Atomically stores v1-compatible checkpoint metadata and v2 geometry
   in the existing `machine.db`; returns a stable checkpoint UUID.
5. Independently rereads both records; only then shows
   `MARK SAVED + VERIFIED` with real monitor, workspace and window
   counts.
6. Adds the checkpoint to the same STORED collection. Its name is
   visible on restart; it can later be renamed or annotated through the
   existing STORED notes editor.

If save has an uncertain response, MARK reports **MAY BE STORED** or
**OUTCOME UNKNOWN** and tells the user to check STORED before clicking
again. A failed save leaves the draft name intact. A verified save
clears the draft.

## Old timeline preserved, but clearly differentiated

The original 24-item session-only timeline and its manual add/remove
functions are kept under ADVANCED for compatibility. Its action is
renamed **TIME ONLY** and clearly says LEGACY / NOT RESTORABLE. The new
MARK NOW never calls `addMachineMarker`, never increments a local
timeline ID and does not use the old in-memory marker list.

No migration of temporary timestamps to desktop checkpoints is possible
because those timestamps did not contain desktop geometry. Existing
durable checkpoint records, notes and snapshots remain untouched.

## Verification

- Source QML contract ensures that MARK NOW calls the verified SAVE path,
  never the legacy in-memory marker function.
- The new input uses the shared Clock presentation, does not alter the
  system clock, and is bounded at 40 characters plus 8-character prefix.
- Quickshell still uses 15 existing Process objects, with distinct SAVE
  and RESTORE ADVANCED state; the full QML root-property duplicate test and
  punctuation-balance checks remain.
- Native stock headless Sway CI uses the exact standalone
  `python3 -B -I MachineSaveBridgeV2.py save` path to write a MARK-labeled
  two-monitor, three-window checkpoint, then reopens it from another
  process using `verify` and `notes-read`. This proves that it persists
  in SQLite and is available in STORED, independent of the original process.
- Prior SAVE, legacy marker, checkpoint notes, restore and Clock CI remain.

## WATCH OUT FOR

The MARK is a *durable geometry checkpoint*. The current RESTORE DESKTOP
flow still cannot guarantee exact tiled placement or Brave window/tab
sessions. Therefore “MARK SAVED + VERIFIED” means its saved data can be
read back, not that the entire original desktop has been accurately
reconstructed. The mark is eligible for the existing limited RESTORE
workflow, but full visual recovery requires a later acceptance milestone.

No new database writer, optional table, auto-trigger, background marker
generator, local filesystem write, merge or Quickshell reload is performed
by this GitHub draft.

## NEXT

1. Exact-head CI and owner review.
2. Operator-approved local activation and visual MARK NOW → STORED
   → VERIFY SAVED GEOMETRY acceptance, including restart persistence.
3. Consider retiring the legacy TIME ONLY controls once the operator
   confirms they are no longer useful.
4. Continue native app/browser session identity and exact geometry
   RESTORE, then selective timeline/merge operations.
