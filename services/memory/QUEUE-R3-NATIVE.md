# CPU++ R3b // Native candidate pipe qualification

Test-only integration, separate direct-main draft. DOC 2 #2575 7982ff18,
DOC 4 #2577 659321a3 and #2573 d7b42622 are pinned exact candidate heads.
All individual workflows passed at preflight. The native CI uses the same
Quickshell 0.3.2-1 package/environment as the existing memory UI native
fixture. Actual pane/consumer/projector and component files are copied from
DOC 2 candidate, actual Python pipe/runtime from #2577, expiry owner from
#2573. No edits to other owners' files. Re-pin on any relevant head change,
switch to actual checkout after all candidates merge.

The offscreen QML fixture uses a real Quickshell Process and SplitParser,
and invokes actual pane prepareIntent/confirmIntent methods (not physical
mouse clicks). A fixture-only host checks frozen intent, establishes pending
state before writing, and supplies deterministic unique test UUIDs.
Child runs actual serve() on stdin/stdout against a private temporary DB
and synthetic source capture, with observations always unavailable.
No host procfs, root reader, memory adjustment, live Hub or production IPC.
Test queue, duplicate confirmation refusal, deliberate lost replacement
reply followed by child exit, explicit reconnect/new epoch, history detail
readback and acknowledgement, cancel, idle and EOF invalidation. Verify
large Linux inode values are absent from UI action/history messages.
No automatic reconnect or replay. Expiry qualification is separately
covered by #2573; this fixture does not exercise the expiry timer or
native readiness. Test fixture uses periodic UI assertion timer only,
not a production monitor.

A genuine production host must still implement bounded framing on client
side (SplitParser alone is not a hard receive bound), timeout/watchdog,
fresh action UUID generation, lifecycle across pane unload and shell
restart, explicit history reconciliation, configuration/installer review
and native resource acceptance. The fixture host is not that host.
Protected reader transport remains unresolved #2412; no production
provider, daemon or privilege. Notification Hub delivery remains separate.

## R3b revision 2 // native failure correction

Initial native run 45544515128/job 138970769932 reached actual QUEUE but
failed at prepare REPLACE. The fixture host incorrectly replaced the whole
actionContext with null while awaiting a reply, hiding pending state from
the pane's submitted-latch lifecycle. Keep atomic {state,projection} when
owner/pending/unresolved exists, with null projection during invalidation;
retain unresolved context on disconnect. Add explicit pending-context,
latch-retirement and preparation diagnostics. This is a host-fixture fix,
not a DOC 2 source change or relaxation of confirmation guards. The exact
cause of the native refusal remains a hypothesis until revised CI passes.

## R3b revision 3 // DOC 2 latch correction qualification

Revision 2 f65e9db7 passed all three workflows with the original DOC 2
b7819842 pane. Raw native run 45544876951/job 138971970511 confirms queue
commit/latch retirement, new epoch/unresolved preservation, replacement
history reconciliation and full cancel/EOF PASS. This demonstrates the
host-context correction is sufficient for that fixture, not that it is
the sole cause of the original failure. DOC 2 independently corrected
QML binding order in #2575 head 7982ff18 (6/6 CI PASS), reading the new
context directly rather than relying on a derived binding during change
notification. Pin that exact revision and repeat the unchanged native
scenario. No source changes to either candidate; no weakened checks.
Production host, real provider, Hub delivery and native resource acceptance
remain outstanding. New combined CI must pass before merge review.

## R3f // actual-checkout durable recovery qualification

Nurse 2 designates MemoryQueueSessionHost.js as canonical; keep separate
reference coordinator unmounted. Add disposable native Quickshell fixture
using actual checkout host, durable owner, pipe, DOC 2 AUTO and recovery
panes. Initial empty inventory cannot unlock. Explicit fixture-only state
injection allows one QUEUE confirmation; discard successful reply before
host consumes it, stop child, explicitly restart with new generation and
recover exact committed local intent via INVENTORY and LOCAL_ACTION.
Display UNVERIFIED and preserve unresolved + startup lock; refuse CANCEL,
clear recovery on EOF. No automatic replay or acknowledgment. Actual
checkout, no pinned overlays in this new workflow. Earlier R3b fixture
retained unchanged. Real Process pipes, test timer and synthetic source;
no raw byte-bounded QML parser, real watchdog, full-shell crash, native
resource acceptance, production launcher/provider or Hub. Test invokes
pane methods rather than physical clicks. No production unlock method.

## R3f revision 2 // container preflight and DOC 2 atomic pane

7637bbbd returned 7/8 workflows PASS; native job 139037356751 failed
at git rev-parse HEAD with dubious checkout ownership, before executing
Python or QML. Scope git safe.directory to exact CI checkout paths per
command, not global wildcard. DOC 2 #2631 exact f21740ed5d4786c487ffa4b31d24c2377e0fd9a9 passed 4/4 workflows;
overlay only its two recovery presentation files and verify pin. Everything
else comes from actual checkout. Native fixture now binds atomicMode and
Host.recoveryContext, uses actual pane requestRead signals for inventory,
exact committed lookup and missing lookup, verifies pending duplicate
refusal and EOF invalidation. No production code or gate weakening.
Re-pin or switch to merged checkout when DOC 2 candidate changes/merges.
New CI required; prior native runtime has not run.
