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
