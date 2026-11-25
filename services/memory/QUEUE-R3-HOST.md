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

Wire frames are ASCII from trusted child encoder; JSON.parse does not detect
duplicate keys (server encoder never emits them). Bound partial frame 16 KiB,
chunk 64 KiB; upstream raw parser must bound reads and deadlines, signal
stop on timeout/exit, kill child as appropriate; no claim of actual QML
bounded receive or watchdog. Client does not compare clocks with owner.
No notification candidates transported, real Hub integration pending.
History parser receives exact outstanding owner/request and global sequence
floor; history invalidated by fresh publication. No authority, execution
or protected provider. #2412 remains HOLD.
