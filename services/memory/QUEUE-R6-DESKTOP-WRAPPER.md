# R6h // Unmounted recovery-only desktop session wrapper

Depends on reviewed R6g #2799 and R6f #2791. Neither dependency merged at
creation. Do not merge this draft into a development branch; retarget to
main only after both predecessors land there and rerun CI.

MemoryQueueDesktopSession composes the canonical Hub binding (sole host
state), generation-aware checkpoint adapter and watchdog. The trusted
shell supplies absolute paths; first open pins configuration. Explicit
open loads and validates persistent checkpoint before launching one
generation-bound direct child. No arbitrary frame dispatch or queue
PREPARE/COMMIT/unlock API is offered to DOC 2. Review/dismissal and
acknowledgment require exact durable pre-send checkpoint; retention needs
a fresh loaded dismissal and history proof, exact explicit selection,
retired controller, clean exit of the exact Process instance, and
correlated helper result plus new locked load. Closing does not restart.
Failure/timeout blocks the instance; no automatic retry.

The new native fixture seeds disposable evidence through real Owner,
runs the actual wrapper with existing Hub/adapter/watchdog and real v2
backend, checks LIVE dismissal, RECOVERED receipt and MISSING refusal,
and uses independent pidfds and a DB-lock helper barrier. CI pending.
The wrapper's direct-child exit signal is not yet an installed trusted
launcher/pidfd security attestation. Fixture-only helper and independent
process supervisor are not production code. Trusted installed path and
identity custody, raw byte allocation bounds (SplitParser), policy
timeouts, failed-process recovery, committed-action retention, combined
notification acceptance and visible operator controls remain gates.
Eight-second timeouts are development choices, not approved installed
policy. No installed mount or production activation.
