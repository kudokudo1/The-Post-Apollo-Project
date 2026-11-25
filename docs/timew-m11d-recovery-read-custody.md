# TimeW M11d // Recovery read failure custody

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE / Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION

M11c's independently pending exact source remains unchanged in its parent draft #2585. M11d is a stacked draft on that source; only the TimeW recovery panel, its existing tests/workflow and this note change. Ordinary Save, MARK, STORED, Restore and all storage services remain unchanged.

Each explicit read creates its own Process, StdioCollector and 45-second Timer. Callbacks carry the originating Process object and monotonically increasing generation; watchdog callbacks also check their originating Timer identity. Retired callbacks cannot mutate a new read or signal a new child. Normal successful display still requires the original strict M11a packet, matching token/selection, both stream completion and normal process exit. Closing/navigating invalidates display, never causes a read.

At deadline the request token is revoked, the display is cleared and a HOLD message appears. If the owned reader remains running, its own Process.signal(9) is invoked; no arbitrary external PID, shell kill, other process or Save/Restore path is targeted. Release on timeout requires the Process to report non-running and no process ID. If that cannot be established, stay busy/HOLD; do not overlap. A failed executable launch with no exit/stream signal can retire at the deadline after the same stopped/no-ID check. Qt objects retire via deferred destruction only after ownership is revoked. Later explicit reads are independent; there is no automatic retry.

## HOW TO USE

Existing MACHINE → SAVE RECOVERY → explicit REFRESH/INSPECT. On timeout, the read-only request is discarded. A later explicit read becomes available only when the owned child has stopped. No user file mutation, retry of Save or Restore authority.

## VERIFY

Adapt M11b source-handler Node regression harness for per-read Process/Timer objects. Preserve original normal completion, correlation, context and no-automatic-read checks; add stale callback/watchdog, missing-signal, missing-launch and owned-child cancellation tests. Native workflow continues using Quickshell 0.3.2 in private Xvfb/HOME/XDG with actual panel and local SQLite fixture. The sixth child now hangs indefinitely and ignores SIGTERM; assert it is gone before the seventh explicit process starts. The eighth reads normally. Separate real failed-executable case uses a private empty PATH and the unchanged executable name; it must retire after actual deadline without producing a new read or changing database bytes. Regression CI remains required; no claim of native PASS without observed logs.

## WATCH OUT FOR

Process.running/processId are Quickshell observations, not independent protected custody. Cancellation targets only the direct read-only child, not an arbitrary descendant tree; a child stuck in kernel uninterruptible sleep or a runtime that cannot observe termination remains HOLD. Missing executable recovery may take the full 45 seconds. This does not establish physical input/Wayland/full installed UI acceptance. No native capture source or protected Restore admission. The parent #2585 must be independently reviewed and merged before retargeting/reviewing this stacked work. No workstation modifications.

## NEXT / DECISIONS

Review exact native evidence, parent dependency and merge order. Then ordinary local genuine fractional capture and active Save integration may advance separately from protected Restore. No production activation.
