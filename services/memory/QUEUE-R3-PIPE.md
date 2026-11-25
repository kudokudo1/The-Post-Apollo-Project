# CPU++ R3a // Session-scoped desktop pipe reference

Proposed unprivileged transport for DOC 2 review. Quickshell Process supports
stdinEnabled, write() and stdout parsers (https://quickshell.org/docs/v0.2.1/types/Quickshell.Io/Process/).
Use one non-detached child scoped to the shell session, not per AUTO pane,
not a second monitoring daemon. Do not automatically restart or resend after
exit. Installed Quickshell version, process lifecycle, launcher/storage path,
real QML parsing, UI timeouts and resource budget need native qualification.
No executable entry point, installation, mounted QML, or actual provider here.

serve(owner, read_fd, write_fd, io_timeout_ms=explicit) operates on existing
anonymous pipes, one cooperating owner, single ordered client. No socket or
network listener, no command dispatch, no shell. Bounded 16 KiB newline
JSON frames, duplicate keys, unsupported types, non-JS-safe integers and
oversized frames refused. Input and output descriptors are caller-owned;
EOF or protocol error ends the session, closing the owner. A partial frame
or backpressured write has explicit bounded I/O lifetime. Provider callbacks
must independently enforce their deadline; a blocked provider is not made
safe by this loop. No production timeout or scheduling defaults chosen.

Startup HELLO {version,kind,owner_id,can_execute:false}, INVALIDATE of same
shape, then existing STATUS envelope with exact R1 projection (notification
candidate suppressed on UI pipe). Every scheduled publication sends
INVALIDATE first, then STATUS; only owner clock schedules. No pending
request or expired reconciliation report -> no timeout, blocking read.
Client opens AUTO from cached publication; cannot request a tick. Explicit
ACTION wrapper {version:1,kind:"ACTION",message:existing_action_message};
reply existing ACTION envelope followed by INVALIDATE + fresh STATUS.
Client must handle ordered control messages, clear status before submission,
on INVALIDATE, exit, disconnect or timeout. UNKNOWN must not replay.
Host must qualify timeout/watchdog independent of blocked Python work.
No UI clock comparison, no current READY claim. Unresolved local actions
require explicit reconciliation after owner/client restart.

HISTORY {version:1,kind:"HISTORY",owner_id,request_id} is read-only; DETAIL
envelope contains reduced request fields, notification attempt history and
unbound-evidence state only. No raw inode/device, digest, unsigned nested
VERIFIED receipt, reservation packet, or authority. History does not poll.
No transport command for publish, passive read, arbitrary paths or execution.
Malformed action/protocol closes session; treat outstanding action as
UNKNOWN even if it may have committed.

No notification delivery is wired; candidate remains in local ledger and
requires separately reviewed synchronous Hub integration and stage recovery.
No approved native identity/recovery reader yet (#2412); do not invent one
or weaken permissions. No subprocess launch in library. Fixtures use fake
source, deterministic clock, temporary private DB, and real anonymous pipes
for idle startup/EOF. These are not actual shell or native memory tests.
Protected completion, reduction and automatic execution HOLD.
