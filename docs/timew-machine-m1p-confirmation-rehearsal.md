# MACHINE M1p // Typed confirmation rehearsal (non-operative)

**Stage:** implementation draft. **No live move, approval grant, automatic Undo,
journal write, or new background service.** This stage trains the interaction
boundary before production activation. It is not a trusted operating-system
permission mechanism.

## Operator path

In Clock → MACHINE → STORED, select and OPEN SAVED METADATA for a checkpoint,
then RESOLVE LIVE, choose a uniquely eligible app and REVIEW MOVE. M1p shows
the required phrase tied to that window and target workspace, e.g.
`MOVE kitty FROM 1 TO 2`. Enter that phrase exactly and select
**VALIDATE ONLY**. The helper performs a *new read-only* Sway preflight;
success reports `PHRASE VALIDATED // NO APPROVAL OR MOVE`. Wrong/stale
source, expired application window, changed candidate, invalid checkpoint,
incorrect phrase or absent display refuses validation.

The operator can also CHECK INTERRUPTS as before. This remains read-only.

## Binding and limitations

`MachineMoveConfirmRead.py` accepts only `confirm-preview` with a bounded
JSON record on standard input: canonical checkpoint UUID, validated saved
document, selected live candidate, typed phrase. It calls the existing
M1o review bridge, which in turn uses the M1n read-only gate's preflight.
The phrase is checked against the *freshly revalidated* action. Neither
adapter creates an M1n approval token, starts a move, writes to the journal,
or persists a confirmation.

The QML view discards confirmation state when the selected saved checkpoint
or resolved window changes. A revalidated dry-run response is accepted only
if the live selected candidate still matches the submitted action. This is
not an authorization or recovery guarantee. Later live execution will need
a separately reviewed, trusted operator confirmation transport, an atomic
single-use token and a fresh pre-dispatch Sway read.

All seven existing user checkpoints remain untouched. The journal stays
independent of stored checkpoint data. Reboot retention is reported by the
operator separately; the dry-run never alters persistent checkpoint storage.

## Deferred UI debt

The operator wants functionality before visual redesign. Button sequencing,
white-on-white blending, conditional content overflow and marker clipping
remain later UI work. This stage only adds a functional TextField and one
validation button in the existing STORED review section.

## Verification

`tests/timew/test_machine_move_confirm_read.py` covers one exact phrase,
case/spacing/mismatch/no-op/missing/stale inputs and rejects every CLI action
except `confirm-preview`. `tests/timew/test_machine_move_confirm_ui.py`
proves no apply/approval/token path exists. The TimeW foundation workflow
runs them alongside previous M1o tests and all existing MACHINE regressions.

**Before live activation:** trusted UI identity/permission boundary,
SwayFX version match, isolated real session acceptance, journal reconciliation
and an explicit operator decision about local desktop window movement.
