# MACHINE M1l // Durable single-move recovery journal

**State:** Backend implementation and isolated tests only. No production entry
point, Sway runner, Quickshell action, automatic retry/rollback or local
activation. No Hospital assignment or permissions assumed.

## Mechanism

M1k's `execute_one` now requires an explicitly supplied
`MachineMoveJournal.MoveJournal` object, in addition to synthetic Sway
read/write runners. It validates the target again, atomically persists a
before-state, durably transitions to `dispatching`, then issues at most one
narrowly scoped injected Sway command. It re-reads the compositor and writes
a durable final classification before reporting a result.

The operations journal is independent of stored checkpoints and PX/Hospital.
Its proposed location is:

`$XDG_DATA_HOME/post-apollo/machine/move-operations.db`

or `~/.local/share/post-apollo/machine/move-operations.db`.
**This PR never creates that database on the operator's machine.** The
journal constructor needs an explicitly provided absolute path; no implicit
open occurs. Tests use fresh temporary directories.

SQLite uses WAL, synchronous FULL, owner-only directory/database permissions
and transactions. Each record contains exactly a UUID, the bounded
`con_id`, `app_id`, source/target workspace, state/timestamps and
optional observed workspace. It does not store window titles, URLs, process
IDs, command lines, browser contents, or approval tokens.

## Crash-state meanings

| Durable phase | Meaning at next process start | Automatic behavior |
| --- | --- | --- |
| `prepared` | Before-state stored; command **not known** to have been sent | None; manual review |
| `dispatching` | Dispatch about to begin or in flight; may have applied | None; manual review |
| `verified_moved` | Sway accepted the command *and* postflight verified the placement | Read-only record |
| `refused_no_confirmed_move` | IPC refused and original placement was still verified | Read-only record |
| `uncertain_requires_manual_review` | IPC/result/state conflicted or disappeared | No retry or Undo |

The transition to `dispatching` must commit *before* the command is issued.
A crash in that narrow window is intentionally considered uncertain; without
a durable proof, nobody should pretend to know whether it moved. A failed
journal begin or dispatch commit prevents the command. A failed completion
commit prevents a verified-success response and leaves `dispatching` to
be found on restart.

`MoveJournal.pending()` only reads records. It does not apply, reconcile,
close, resend, or automatically delete a pending operation. It blocks a new
journaled move while there is a prepared, dispatching or uncertain operation.
A future separately approved operator-reviewed reconciliation will be needed
to unlock it. No automatic recovery or cleanup is implemented.

## Approval and limits

A boolean `approved` in the current synthetic pilot is **not a real
operator approval token**. It exists only in fixture-run code. A future
live implementation needs actual per-action consent tied to a specific
checkpoint ID, window, destination and expiration, and fresh compositor
validation immediately before execution.

The recorded before-state supports a *non-executable* Undo preview, not an
automatic rollback. A restored process may have no matching transient Sway
ID. This release does not restore tabs, process RAM, unsaved files or desktop
arrangements. The user requested interface sequencing, overflow and color
polish later, so these concerns remain explicitly deferred.

## Verification

- `tests/timew/test_machine_move_journal.py`: crash windows, read-only
  reopen in another Python process, state replay refusal, schema and permissions,
  symlinks, private metadata rejection, terminal/uncertain transitions.
- `tests/timew/test_machine_window_move_pilot.py`: synthetic Sway command
  requires the journal; failed pre-dispatch writes produce no command, failed
  final writes yield no reported success.
- `tests/timew/test_machine_window_move_pilot_contract.py`: no production
  command runner or TimeW UI apply surface.

Still required before live activation: disposable Sway/SwayFX movement and
focus testing, immutable scoped UI approval, cancellation/expiry handling,
operator-reviewed reconciliation/Undo, and separate approval for any local
window movement.
