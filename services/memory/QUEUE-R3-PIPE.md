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

## R3e // recovery reads

INVENTORY {version:1,kind:"INVENTORY",owner_id,limit:1..16} and
LOCAL_ACTION {version:1,kind:"LOCAL_ACTION",owner_id,action_id} delegate
to existing durable Owner. Both use standard sequence envelope; inventory
or action_id/record fields as #2603. Legacy mode refuses; owner mismatch,
unknown command or malformed input fails session. No capture, observation,
action sequence consumption, scheduler change, acknowledgment or unlock.
A null lookup is not proof of noncommit. Existing frame size bound applies.
Four additional Python fixture cases exercise dispatch, 50 repeated reads,
new owner recovery, invalid fields and legacy refusal. No production launch.

## R3l // staged pipe candidate

On merged #2675/#2677 combined main 52fb321a, add explicit staged
owner configuration only. Legacy wire unchanged; no mode selected by
client. PREPARE_ACTION {version:1,kind,message} returns existing
PREPARED_ACTION envelope plus random UUID challenge. No capture, queue
mutation or publication while waiting. COMMIT_ACTION {version:1,kind,
message,prepared_sequence,challenge} must match exact preparation in
same live session. Consume receipt before dispatch. Existing ACTION reply
then INVALIDATE/STATUS. Challenge is correlation, not a security grant.
Unexpected command, mismatched receipt, failed emit, timeout or EOF
terminates staged session, retires live state, preserves durable evidence.
Server monotonic wait bound starts before PREPARE; existing owner admission
clock independently checks wall/monotonic under lock. No autonomous retry,
startup unlock or recovery acknowledgment wire. A transaction already
admitted is not undone by EOF. Seven added tests including actual OS pipe
EOF after durable PREPARE, new owner lookup and old commit refusal.
Canonical JS host integration is a separate reviewed next step; it must
validate PREPARED_ACTION exact schema/owner/sequence/message, retain pending
through receipt, send exactly one matching commit after receipt, retain
unresolved on loss, never commit recovered evidence. No installed launcher
or production timeout default. No DOC 2 source changes.

## R3n // explicit review acknowledgment server transport

Stack on #2692 exact abe274b8 (8/8 workflows, all five native trials
passed; independent review pending) to preserve both reviewed/candidate
heads. Explicit trusted review_max_age_ms configuration, absent by
default, requires staged owner. RECOVERY_REVIEW {version,kind,owner_id,
action_id} returns existing owner RECOVERY_REVIEW envelope. User must
explicitly acknowledge exact live review via RECOVERY_ACK {version,kind,
owner_id,review_id,review_digest,review_sequence}; consume one-use ticket
before dispatch. RECOVERY_REVIEW_HISTORY {version,kind,owner_id,review_id}
reads saved historical receipt only, null is not proof of noncommit.
No action sequence consumption, queue mutation, startup unlock, or replay.
No additional polling; existing scheduled publication remains independent,
review expiry bounds wait. Unrelated input, wrong receipt, expiry, EOF or
emission failure closes staged session. Exact safe receipt shape prevents
extra source fields crossing wire. Seven disposable regression cases,
including lost ACK and actual OS pipe EOF after review. No canonical host
review UI/ack command yet; future host must never auto-ack review and keep
startup locked, handle scheduled publication independently, retain unknown
on loss and lookup old receipt explicitly. No production duration selected.
