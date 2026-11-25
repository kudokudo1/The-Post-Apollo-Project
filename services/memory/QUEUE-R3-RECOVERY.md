# R3d // Durable local intent correlation

DOC 4 Python-side milestone. #2593 and DOC 2 #2594 overlap in host state
coordination; reconcile to one host with DOC 2/Nurse 2 before mounting.
No duplicate daemon or host, no DOC 2 edits.

Opt-in Runtime.local_action(message) under existing runtime lock. Strict
explicit QUEUE/REPLACE/CANCEL/EXPIRE message, no RECHECK journal or
execution. Reserve PREPARED in existing private SQLite DB before capture.
Fresh capture uses existing Runtime._capture with unchanged constraints.
Commit exact queue mutation and action result ID in same transaction
(reusing Queue validation/insert/finish). Terminal notification staging
remains after commit. LocalActions.commit requires same in-memory journal
that prepared exact message; consume that permission before transaction.
No startup replay; same action UUID never accepted again. Prepared failure
blocks additional correlated actions. Do not bypass using old methods.
No acknowledgment or deletion in this milestone.

Read-only lookup by action UUID and bounded inventory (1–16 latest rows,
truncation flag, any PREPARED, exact pending UUID). No raw file identity,
receipt, or authority in projection. Every result is UNVERIFIED for
kernel adjustment. COMMITTED means only local SQLite intent mutation,
not swap action or delivery. A lost QUEUE response is recoverable by
durable action ID even without an expected request UUID. If the entire
shell crashes before server receives the action, no row can prove whether
it was sent; startup remains locked until reviewed host-side recovery and
inventory semantics. Never infer noncommit from missing row alone.

Existing Owner/pipe and non-correlated methods intentionally unchanged.
This is not a complete live fence: legacy direct Queue/Runtime calls can
bypass the new journal until all cooperating paths are wired, same-UID
storage is not trusted or rollback resistant, no protected provenance.
Do not mount, unlock or migrate production without review. No retention
policy or acknowledgement selected. Reconcile exact action/intent history
and establish durable host-side pre-send record/handshake in next slice.
Tests use disposable SQLite, including forced rollback on correlation
update, no replay on reopen, capture failure, bounded inventory and
terminal links. No process SIGKILL or physical durability claim.
Protected observation #2412 and automatic execution HOLD.

## R3d revision 2 // existing owner integration

Revised existing Owner only, not a second owner or host. Explicit
durable_actions=True selects Runtime.local_action for QUEUE/REPLACE/
CANCEL/EXPIRE under the existing flock and action sequencing. No
fallback on error. RECHECK stays advisory, not a durable intent mutation.
Legacy owner construction and action dispatch refuse journal-enabled DB
(using a metadata read on explicit action only, no new polling). Direct
Queue/Runtime callers, same-UID interference and old binaries remain
outside this cooperating owner fence; not a protected boundary.
Owner.inventory(limit) and lookup_action(action_id) return owner-epoch
and global-sequence-bound INVENTORY and LOCAL_ACTION envelopes; both
require durable mode. Exact wire/host parsing not yet enabled, and missing
lookup is not evidence of noncommit. Proposed shape for DOC 2 review:
INVENTORY uses inventory field exactly as in LocalActions.inventory;
LOCAL_ACTION adds action_id and record (possibly null), both envelopes
standard version/owner_id/sequence/next_action_sequence/kind/can_execute.
No raw identity, receipt, credentials or unlock. DOC 2 #2604 presentation
must remain separate; agree hostStatus and invalidation before mounting.
No installed launcher, production startup approval or reconciliation
acknowledgment. Five extra owner regressions (14 local-action tests total).
Owner expiry change #2573 touches separate status() region; combined
merged-source verification still required. #2577 existing pipe ACTION
delegates to Owner.action, but its launcher/INVENTORY/LOCAL_ACTION
commands and composed recovery qualification are not implemented yet.

## R3h // staged local admission (in-process candidate)

Nurse 2 accepted #2636 corrected native watchdog, 5/5 PASS and merged.
#2635 actual AUTO workspace merged 7/7 PASS. Single canonical host retained.
Before an eventual two-message wire handshake, split local durable action
admission from mutation in the existing owner/runtime. Opt-in explicit
staged_max_age_ms (1..60000, no production default), requires durable mode.
Direct mutating Owner.action refuses in staged mode. prepare_action validates
exact owner/sequence/message, consumes sequence, stores PREPARED using the
existing journal before any provider capture or request mutation, returns
PREPARED_ACTION envelope with exact durable row. commit_action accepts only
the same message on same live owner and runtime instance, consumes live
continuation before checking/capture/transaction, returns existing ACTION
envelope. Deadline uses both owner wall and monotonic time, checked before
capture and again before commit. Stale/mismatched/failed/expired continuation
does not replay, durable PREPARED remains. No automatic clearing or fallback.
A reopened owner cannot commit the old PREPARED, but can read it; a lost
prepare reply must not trigger commit. A future host may send commit only
after matching PREPARED_ACTION, never on startup/retry. No second database,
process, polling or protected authority. Receipt is local intent only.

Existing legacy and one-call durable paths retained for fixture compatibility;
explicit staged selection is not persisted as a deployment policy. Direct
runtime APIs/old binaries still outside cooperating fence. No new wire
commands, actual host integration, durable reconciliation acknowledgment or
production startup unlock here. PREPARED remains blocking until independently
reviewed disposition protocol, not deletion or guessed rollback. Future
startup gate must require explicit operator review of exact outstanding
evidence and revalidate current DB/session; no inference from missing row.
Seven added disposable regression cases; native full-shell crash still
requires qualification. No changes to DOC 2-owned UI or protected helper.

## R3i // exact recovery review acknowledgment (prototype)

Before release of an unresolved preparation, preserve what was actually
reviewed. New owner only, explicit begin and acknowledge, exact old row
and current pending ID plus digest bound to one short-lived review ticket.
Atomic comparison and append of historical acknowledgment in existing
private DB. No queue mutation, no capture/poll, no row deletion, no replay,
no startup unlock. Missing row cannot be acknowledged. Selection change,
wrong ticket/digest, changed pending record, timeout or owner loss refuses.
Review of COMMITTED describes only local intent. Same-UID storage is not
trusted, digests are correlation not signatures, no operator identity or
protected consent claim. Historical acknowledgment is not current state.
Six tests. No production UI/wire and no production deadline selected.

Abandonment is deliberately separate: v1 PREPARED/COMMITTED and its unique
partial index cannot represent a terminal abandoned preparation. Adding
ABANDONED in place would break existing strict parser and old binaries.
Proposed versioned migration (requires Nurse 2 + DOC 2 review and operator
policy): preserve original action and append disposition, make old readers
fail closed, validate exact old row plus current pending state under same
owner lock/transaction, permanently refuse old action UUID, never resume or
infer protected outcome, retain unknown if evidence incomplete. Acknowledging
review is not abandonment and does not release the PREPARED fence. Decide
retention and schema/version migration separately before enabling release.

## R3j // P1 transaction-admission deadline correction

Post-merge #2654 Nurse 2 review 6055525024 / 6055951300: both staged
commit and review acknowledgment checked time before SQLite BEGIN
IMMEDIATE (up to 1 second of lock wait). Recheck wall and monotonic
deadline after the write lock and exact journal/current request validation,
before request mutation. Staged QUEUE/REPLACE retain original validated
capture and collection start timestamps; reject stale source or expired
request at admission; use admitted wall seconds for durable correlation.
Legacy explicit timestamp APIs unchanged. No external provider call under
the DB lock. Review acknowledgment consumes ticket once, rechecks clock
inside transaction after evidence validation and before insert (including
after any schema creation), records admitted time, rolls back on expiration.
Deadline means mutation admission, not a guarantee of fsync completion.
Eight disposable real SQLite contention tests use a separate writer and
advance injected wall/monotonic clocks during BEGIN IMMEDIATE wait:
independent clock expiry, source age, request expiry, and valid admission
timestamps for both paths. No replay, clearing, or startup unlock.
Explicit session disconnect/continuation invalidation is a distinct next
correction; ordinary publication invalidation is not session teardown.
No wire changes or production policy.

## R3k // explicit disconnect and continuation retirement

Stacked on independently reviewed #2675 exact 5c228392; do not edit its
reviewed head or merge it without operator decision. Ordinary invalidate()
remains publication-only. Terminal Owner.close() (already used by serve on
EOF/failure) clears both owner and Runtime live staged messages, journal
fresh continuation and recovery review ticket before releasing owner flock.
No persistent row changes, no provider calls. Owner gate and Runtime lock
serialize teardown with cooperating dispatch; busy teardown refuses rather
than releasing a live owner. Caller must stop accepting commands and
serialize terminal teardown. Invalid/malformed COMMIT consumes both live
states; failed PREPARE receipt construction retires live state as well.
Direct Runtime completion always clears journal transient continuation.
Six regression cases cover late owner/runtime/journal continuation,
review ticket, malformed/mismatch, ordinary publication, failed receipt,
and busy teardown. No change to #2675 deadline checks, startup gate, wire
protocol or production policy. An already admitted synchronous transaction
is not undone by disconnect; full shell crash and actual staged wire still
require native qualification. Direct callers outside cooperating owner fence
remain outside protected trust boundary.

## R5 // operator-approved explicit local disposition and retention

Operator policy approval recorded #2433 comment 7167564838: dismiss only
after exact evidence review, retain original records indefinitely pending
separate retention deletion policy, no auto resume, fresh protected
authorization required for subsequent protected operations. Explicit v2
staged Owner and Runtime configuration only. Atomic journal migration
adds nullable dismissal evidence column and replaces v1 PREPARED unique
index with v2 unresolved-only index. Original seven fields never changed
by disposition; original UUID remains globally unique. V1 journal schema
rejects migration rather than misreading dismissal; v1 pipe explicitly
refuses v2 owner. Raw Queue APIs and old unjournaled direct callers remain
outside cooperating owner contract. No deployment migration selected.
Separate Owner.dismiss_recovery_preparation consumes the current live
review, exact digest/current pending snapshot and both admission clocks
under writer lock. Existing ACK does not dismiss. Only exact PREPARED row
may be dismissed; missing or committed evidence cannot be relabeled.
Disposition receipt preserved in original row, validates exact snapshot/
digest/record, UNVERIFIED, startup_unlock:false, can_execute:false.
Inventory v2 separates original record and historical disposition and
reports only actually unresolved preparation; exact disposition lookup.
New UUID may enter ordinary local queue after explicit dismissal in v2
direct owner tests; old UUID forever refused. No raw operation authority,
no deletion, no checkpoint rotation or startup unlock. Current host wire
and DOC 2 controls still require coordinated v2 disposition integration,
including retained host checkpoints and fresh local session gate. No
automatic dismissal, expiry, retry or protected execution.
