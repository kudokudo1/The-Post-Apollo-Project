# R3c // Session host protocol controller (development only)

After #2579 corrected combined native PASS, extract reusable pure host logic
outside the demand-loaded pane. Actual DOC 2 consumer/projector on main;
history parser #2591 pinned 546bd0c3 for fixture only. No DOC 2 file edits.
Host owns atomic context and global sequence across STATUS/ACTION/DETAIL,
one outstanding history request, bounded ASCII JSON frames, owner epoch,
pending-before-write, frozen intent revalidation, no replay. Pending and
unresolved state persists in the controller across child disconnect/restart.
Fresh UUID and trusted child channel supplied by future desktop wrapper.
No process spawn, QML mounting, filesystem, timers or native provider here.

A controller startup or child reconnect ALWAYS starts with startupLocked.
There is intentionally no unlock or reconciliation acknowledgement function.
The fixture alone injects an unlocked state to test explicit submission.
Before enabling real controls, define durable host-side action intent
recovery and a bounded inventory/history query, including lost QUEUE (no
expected request UUID) and full shell crash. A healthy child or one detail
is not proof an unknown action did or did not commit. DOC 2 must present
startup gate and explicit reviewed reconciliation; no automatic replay.

Wire frames are compact ASCII from trusted child encoder; strict printable
ASCII validation and exact JSON stringify roundtrip reject duplicate keys,
alternate numeric spellings and noncanonical escape encodings. Bound partial frame 16 KiB,
chunk 64 KiB; upstream raw parser must bound reads and deadlines, signal
stop on timeout/exit, kill child as appropriate; no claim of actual QML
bounded receive or watchdog. Client does not compare clocks with owner.
No notification candidates transported, real Hub integration pending.
History parser receives exact outstanding owner/request and global sequence
floor; history invalidated by fresh publication. No authority, execution
or protected provider. #2412 remains HOLD.

## R3c revision 2 // DOC 2 reconciliation

DOC 2 #2594 overlaps this host and recommends HOLD in favor of one DOC 4
controller. Accept direction pending independent Nurse 2 disposition; no
merge or closure of #2594. Incorporate review safeguards: explicit startup
and history gate metadata on atomic context; global DETAIL sequence also
advances consumer watermark and invalidates previous preparation; validate
STATUS even during pending; canonical ASCII JSON roundtrip; monotonically
increasing caller-supplied child generation on start, feed and stop, reject
reused owner epoch. Distinguish pending action from publication handshake
(INVALIDATE then STATUS), preserve pending across scheduled publication.
Expose independent waiting categories for future wrapper deadlines; actual
watchdog and per-wait timeout fencing remain unimplemented. Upstream raw
read bounds still required. Host API is pre-mount and can change; DOC 2
presentation must consume explicit gate metadata. No startup unlock or
recovery acknowledgment; #2603 durable local action integration next.

## R3e // recovery projection

Canonical #2593 host now consumes owner-bound INVENTORY and LOCAL_ACTION
with one outstanding read across history/recovery/action, shared global
sequence, actual DOC 2 recovery parser, and explicit RECOVERY wait category.
Read calls are explicit and permitted under startup lock. Validated raw
inventory is retained only for the existing #2604 pane; recoveryContext()
provides agreed hostStatus and inventory atomically, with localAction
separately marked UNVERIFIED. Selection/read, publication invalidation,
action, owner loss and timeout discard stale recovery view. No unlock or
acknowledgment. Exact lookup null not noncommit evidence. Actual merged
history/recovery parsers now tested without candidate overlays. #2594
was also merged despite prior HOLD recommendation; no duplicate mount,
cleanup remains Nurse 2 disposition. Native wrapper, client watchdog and
full-shell durable pre-send/acknowledgment remain pending.

## R3g // native one-shot watchdog (unmounted)

MemoryQueueSessionWatchdog.qml accepts immutable canonical host state and an
explicit six-category duration policy, creates only one-shot timers for
active waits, retains deadlines across partial bytes and intermediate
packets, destroys timers when waits resolve, fences callbacks by generation
and unique ticket, latches first failure. No default production durations,
no timer when idle, no launch, automatic retry or unlock. Wrapper must
publish Host.stop for the exact generation before stopping the child;
policy rejection also requires fail-closed handling. Coalesced same-kind
waits conservatively keep earlier deadline. QML event-loop starvation is
not bounded by these timers; native raw parser and actual installed
wrapper still outstanding. Fixture-only values are not production policy.

Merged #2621/#2631 native PASS at dd2a89e8 (raw job 139044396578).
Remove candidate overlay and run actual checkout. Two disposable native
trials: original lost response and actual delayed reply after local commit
(test-only Runtime subclass sleeps 8s; ACTION watchdog 1.2s). Verify exact
host invalidation before stop, one trip, explicit reconnect, durable local
commit recovery, no replay, no idle deadlines. Does not prove full shell
crash recovery, protected kernel action or physical durability. No DOC 2
source edits. Startup reconciliation and Hub delivery still outstanding.

## R3g revision 2 // isolate actual watchdog module

Initial baba39bf: 4/5 workflows passed. Native job 139047832100 stopped
before either acceptance scenario could execute: importing the production
memory directory loaded its qmldir MemoryOperation singleton, whose
qs.services.time dependency is intentionally absent in the isolated scene.
Follow Nurse 2's REVISE/HOLD disposition. Copy actual Python sources only
into the backend directory and byte-identical MemoryQueueSessionWatchdog.qml
plus MemoryQueueSessionHost.js into a separate narrow QML directory; no
production qmldir, singleton, fake time service, or dependency stub. Both
fixture host and watchdog resolve the same actual JS copy. No changes to
watchdog or host source, timeout durations, trial steps, or acceptance
assertions. Both native trials must pass at the revised exact head before
independent review. DOC 2 #2635 workspace qualification is separate;
no shared fixture or presentation modifications.

## R3m // canonical staged host candidate

Stacked on #2680 reviewed 053f103a; preserve reviewed server. Explicit
host start mode STAGED supplied by trusted wrapper; LEGACY default
retained for existing fixtures only. No negotiation/downgrade. Confirm
publishes existing Consumer pending before PREPARE frame; RECHECK remains
ordinary ACTION. Strict receipt validation via actual recovery row parser,
owner, watermark, sequence, exact typed pending message and challenge.
Receipt is not completion. takeCommit is one-use state transition: wrapper
must publish returned state before writing frame, never retry a failed write.
Same ACTION watchdog remains active throughout; no extension. Reject extra
frames while receipt ready, premature ACTION, malformed receipts. Preserve
unresolved on loss in any stage, erase transient challenge on stop; restart
never emits COMMIT from history. No additional controller or startup unlock.
DOC 2 context adds presentation-only actionStage; existing pending gating
unchanged. Native fixture adds staged ROUNDTRIP, LOST and EOF trials with
actual child, panes and isolated watchdog; previous two trials preserved.
Fixture-only startup injection and durations; no installed wrapper, raw
byte-bounded reader, event-loop starvation or whole-shell recovery proof.
No recovery acknowledgment wire or release of PREPARED. CI pending.

## R3o // canonical review acknowledgment interface

Stacked on reviewed #2698 exact c95bf995, previous #2692 and #2680 unchanged.
Explicit staged start option reviewEnabled (default false) must match trusted
server configuration. beginReview, acknowledgeReview and readReviewReceipt
are separate explicit transitions returning state/frame; wrapper must publish
state before each write and fail terminally on write loss. No automatic ACK.
Review uses exact wire fields and existing recovery row parser; live receipt
requires current owner, selected action, exact sequence and digest. Review
blocks unrelated requests, remains under existing RECOVERY watchdog without
reset across phases, tolerates scheduled publication; ACK unavailable while
publication pending or concrete pending ID differs. Server independently
revalidates exact snapshot and deadline under SQLite lock. ACK selection binds
reviewId/digest/sequence/generation; history cannot create live ACK. Loss
after ACK submission retains exact review in memory across reconnect; only
matching historical receipt clears review-loss marker, null leaves unknown.
Action unresolved and startup lock never cleared. Separate reviewContext
for DOC 2; no new controller, no production UI edits. Tests cover invalid
receipts, stale selection, publication, explicit one-use ACK and history.
No full-shell durable host-loss record, native ACK fixture, startup unlock,
PREPARED release, production launch or protected consent. Combined actual
main verification required after operator merge decisions.

## R3p // native acknowledgment qualification candidate

Stacked on #2701 exact 865e356e (8/8 workflows, existing five native
scenarios passed; raw host job 139176185929 and native 139176187189).
Extend disposable actual-checkout fixture only. Stage a local QUEUE and
close stdin after PREPARED; restart locked and explicitly review exact
old action. Three additional trials: ACK (one explicit fixture
confirmation, received receipt), LOST (harness drops committed ACK before
host feed), EOF (close stdin after review but before ACK). Third owner
retrieves exact historical receipt or null. No startup unlock, no action
replay, no protected operation. Independently verify SQLite action remains
PREPARED and acknowledgment count is exactly one/one/zero after process
exit. Existing five trials retained. Actual Quickshell, watchdog, canonical
host, Python pipe and existing recovery pane; acknowledgment UI is still
fixture-driven, not DOC 2 production controls. No installed wrapper or
full-shell persistent host correlation. CI pending. Review timeout and
staged duration are disposable fixture parameters only.

## R3q // persistent host pre-send checkpoint candidate

Stack on #2706 c5bc7891, 5/5 workflows and eight native scenarios PASS
(raw native job 139180239877, ACK/LOST/EOF exact database counts).
Before actual PREPARE and explicit ACK writes, future trusted wrapper must
call checkpointForFrame, save exact returned record through HostCheckpoint,
wait for successful file and directory fsync, publish transition state and
write exactly once. A bounded private caller-supplied directory has two
fixed write-once slots (one action, one review ACK), strict canonical JSON
and SHA-256 corruption detection, no symlinks/hardlinks or unsafe mode,
no overwrite/delete/clear, bounded reads; partial/corrupt files refuse.
The review digest is independently checked before saving. This is a
library contract, not a second controller or a daemon. On restart load
and restoreCheckpoint create fresh stopped state with only unresolved
action and historical review-loss identity, never pending, live challenge,
review ticket or startup unlock. Null snapshot is a blocker; empty slots
do not establish noncommit. Full-shell lookup requires fresh owner. Actual
wrapper integration and crash-before-send qualification still outstanding.
Same-UID adversaries, directory rollback and physical storage guarantees
outside scope; single cooperating writer required. This deliberately
single-use prototype cannot support ordinary repeated operations until
a reviewed terminal disposition and retention policy is implemented.
No production directory or launch path selected. No DOC 2 edits.

## R3r // checkpoint-gated transmission candidate

Stacked on #2711 5a791eb2, 10/10 workflows and 7/7 storage tests PASS.
Explicit checkpointRequired option on canonical staged start (default off
for previous fixtures). confirm and acknowledgeReview now return checkpoint
request and no transport frame in this mode. Publish state before launching
the fixed one-shot Python adapter, feed one bounded record via stdin to EOF.
Adapter returns exact CHECKPOINT_SAVED only after durable file+directory
fsync, or nonzero exit; LOAD exposes bounded validated snapshot only.
Wrapper MUST check successful exit, bounded stdout and generation, call
finishCheckpoint with exact result (null on failure), publish consumed state
before writing returned frame once. No resend, no second controller.
While saving, any incoming channel bytes terminate conservatively, including
scheduled status refresh: never send stale intent. Existing ACTION/RECOVERY
watchdogs remain active across storage and transport. Lost/failed save
conservatively preserves unknown; absence not proof of noncommit.
Composed Node tests use actual Python subprocess and private disposable
files to verify both save gates, mismatched/duplicate/stale completion,
occupied/corrupt refusal and fresh restore. Actual QML process adapter,
bounded native raw reads and full-shell SIGKILL remain next. No production
path, timeout policy, startup unlock or repeated-use retention selected.
No DOC 2 source changes.

## R3s // native checkpoint IO adapter candidate

Direct main baseline 8e2b759d (all R3l-R3r dependencies merged; final
combined CI not returned). Unmounted MemoryQueueCheckpointAdapter.qml
launches one fixed Python LOAD/SAVE at a time, explicit trusted absolute
paths and timeout, bounded retained parsed reply, exact operation/ticket/
generation/exit correlation, terminal cancel or failure; no queue frame
write in adapter. Canonical host still owns all state and frame release.
Native fixture PASS loads empty locked checkpoint, test-only initial
confirmation, saves PREPARE and ACK before frame release; FAIL uses corrupt
slot and proves no local preparation or evidence overwrite. Prior eight
native scenarios retained. SplitParser does not bound upstream raw
allocation; trusted fixed helper only, no arbitrary provider/command.
Full shell kill, startup restore from nonempty storage, repeated-use
retention, production launch paths and provider still unqualified.
No startup unlock API or DOC 2 source edits. CI pending.
