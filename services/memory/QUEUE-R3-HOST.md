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
