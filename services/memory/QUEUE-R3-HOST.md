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
