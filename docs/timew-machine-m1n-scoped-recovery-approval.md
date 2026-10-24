# MACHINE M1n // Exact-action consent and interrupted-operation review

**State:** Isolated backend/test milestone. No production UI confirmation, no
live desktop action, no ability to clear/retry a pending operation, and no
claim of Hospital worker registration or system authorization.

## Exact-action approval lifecycle

`MachineMoveApproval.MoveApprovalGate` is a memory-only short-lived control:

1. **REVIEW** (read-only): perform the existing M1k read-only preflight,
   bind the exact validated saved checkpoint document, canonical checkpoint
   UUID, app class, transient container ID, source and destination into a
   SHA-256 fingerprint. Return a visible before/after description and a
   required confirmation phrase. No command, journal record, or real Sway
   movement.
2. **CONFIRM** (test-only): validate exact review ID and phrase, unchanged
   fingerprint and 90-second monotonic deadline; produce a cryptographically
   random, review-specific, one-use ephemeral token.
3. **EXECUTE** (test-injected only): repeat fresh Sway preflight; require
   the exact unexpired token, checkpoint ID and request; consume token before
   opening the M1l journal or sending a move. Then the journal's before-state,
   dispatch, postflight and outcome transitions remain mandatory.

No boolean, label or previous chat confirmation counts as live authorization.
The current synthetic fixtures supply the phrase deliberately, **not** by
checking who the operator is. Production needs a trusted operator UI and a
secure way to bind the approval to the exact currently viewed preview, without
an API path that self-approves. No token is stored in the journal or checkpoint.
Reviewing a different action invalidates the prior review; neither token nor
review survives a process restart. An expired or consumed grant does not
authorize a second action.

## Interrupted-operation reconciliation

`MachineMoveReconciliation.inspect_pending(journal, read_runner=...)` makes
exactly one on-demand, read-only Sway observation if pending operations exist.
For each prepared, dispatching or uncertain journal record it returns an
advisory classification such as:

- `appears_at_origin` / `appears_at_target`
- `appears_elsewhere`
- `saved_window_not_identified`
- `identity_conflict` / `ambiguous_candidate`
- `workspace_or_window_unavailable` / `state_unavailable`

All these results **require manual review** and are *not proof* of historical
process identity. Sway container IDs can be reused after a restart. Inspection
never changes the journal phase, clears a pending lock, retries movement or
performs Undo. Even `appears_at_target` cannot automatically declare the
old operation successful.

M1l's journal stays separate from desktop checkpoints, PX/Hospital and user
application data. No browser URL, title, PID, command line, screenshot,
clipboard or terminal content is stored or emitted.

## Acceptance

- Memory-only one-time tokens are scoped to one canonical checkpoint UUID,
  one immutable saved document and one exact window move.
- Time expiry, stale ID, changed checkpoint, wrong phrase/token, reused
  approval and new review replacement are rejected.
- Synthetic M1k and real disposable M1m Sway tests must still pass using
  scoped injected approvals, proving no regression in durable preflight or
  one-window postflight.
- Reconciliation remains read-only; synthetic fixtures exercise original,
  target, missing, duplicate, changed identity and unavailable output states.
- TimeW has no apply/reconcile button in this milestone, so there are no
  new user-facing controls until a separate operator-approved action flow.

## Remaining before live activation

A trustworthy in-widget consent screen and per-action approval validation
must still be designed and independently reviewed. SwayFX compatibility,
disposable matching-version testing, cancellation/expiration behavior,
recovery/Undo reconciliation, accessibility and unsaved-work safeguards
remain gates. The user's UI sequencing/color/overflow cleanup is deferred
until the functional recovery boundary is ready.
