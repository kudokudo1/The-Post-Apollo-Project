# R6 // Disposable ForestW process interface (proposal for review)

PATIENT: The-Post-Apollo-Project  
ROOM: Forest Integration  
OWNER: DOC 2F Runtime; UI1 process lifetime, UI2 presentation, DOC4F history, DOC3F security.  
STATE: PROPOSED, CI-only. No implementation, installation or production authority.

## Baseline and scope

R5 #2630, R5b #2645 and corrected Mind M6d #2644 are merged. R5b
source 7dba584a owns one temporary fixed public cherry journal and fake
provider. It has a synchronous open callback before the durable user
append, explicit step/stop, pinned pagination and committed-idle SQLite
reopen. Do not replace these with another journal or scheduler.
#2643/#2648 are separate UI mount and panel witnesses, not an installed
Runtime connection. Follow Nurse2F #7159300873, DOC3F #7159167314,
UI2 #7159180846/#7159283213 and DOC4F #7159179147.

First native CI trial only: fixed three R5 fixture prompts, two completed
turns and optional third STOP. No arbitrary text, model, endpoint, path,
Tree, session selection, native inference, private data, tool use,
C5 permission or protected transport. No user workstation activation.
The existing installed B5b/B5e deny-only experiments are not repurposed.

## Process and ownership

UI1 explicitly launches one reviewed Python fixture child using Quickshell
Process, fixed absolute interpreter/script argv, stdin enabled before
launch, no shell, no detached mode, no automatic restart. Use a fresh
CI-controlled isolated HOME/cwd/TMPDIR and explicit minimal environment;
no inherited secrets, no caller-supplied executable/path or Python
import path. Child owns only the temporary R5 journal it creates. UI1
tracks the actual Process object, its incarnation and actual Loader item
and gate; destroyed/replaced item invalidates that incarnation immediately.
No PID string, trial token, Tree hint or UI flag authenticates a process.
Parent UI remains event-driven, never spins a nested event loop waiting
for the child. No new socket, listener, daemon, scheduler or global state.

Child stdout is exclusively protocol, stderr discarded or independently
bounded and never displayed/logged as raw content. Use a reviewed bounded
incremental parser: candidate Quickshell SplitParser empty splitMarker
delivers arbitrary string chunks. This is NOT a raw byte API or proof of
native allocation bounds. Verify actual installed test version, reject
non-ASCII/control chunks before accumulation, enforce accumulator bound
before each append, never concatenate unlimited chunks or split unbounded
text. Child uses bounded raw byte line reads before decoding (no unbounded
readline). Non-ASCII/native read allocation limitation stays explicit;
if the actual parser cannot support the required evidence, HOLD rather
than introduce an unreviewed transport.

## R6a exact envelope proposal

Every frame is compact ASCII JSON followed by exactly one LF. Exact outer
keys: {"v":1,"trial":"<32 lowercase hex>","action":1,"kind":"HELLO","data":{}}.
No extra keys, null substitutions, coercion, whitespace, BOM, CR or NUL.
All decoded strings printable ASCII only in this fixed fixture; no free
text input. Integers are JSON safe nonnegative integers (no bool, fraction,
exponent, negative zero). Canonical encoding sorts object keys recursively
by ASCII order, no whitespace, standard JSON escapes only for quote and
backslash; arrays preserve order. Validate exact canonical round trip
before schema use on both ends. Python additionally rejects duplicate
keys explicitly; receiver canonical equality rejects overwritten duplicate
keys. Require full-match token and safe integer validation, never eval.
An invalid raw line cannot be repaired or partially interpreted.

Caps are candidate engineering decisions: parent frame <=512 bytes, child
frame <=16384 bytes, each INCLUDING LF; combined inbound+outbound accepted
wire bytes <=131072 for a trial (local endpoints count both directions),
<=64 actions, <=160 total frames including offers/ACK, one action pending;
parent and child independent monotonic deadlines: startup/action/offer ACK
5 seconds, trial 120 seconds. Cap enforcement BEFORE output submission,
before input append/decode, and before starting another action. Increment
counts for all consumed/submitted frames, no resetting on reattach or
reopen. No partial row, truncation, or retry to fit. On budget exhausted
close locally; no extra diagnostic frame beyond budget. Reject unknown
or oversized input, unterminated EOF, partial response, duplicate/gap,
timeout, unexpected exit or bytes after CLOSE. At most 2 public status
units in one action result; only the fixed R5 fixture may run.

trial = parent-issued fresh 32-hex opaque correlation for this tracked
child incarnation; HELLO action 1 binds it once, no restart/resume.
action = contiguous 1..64, chosen by parent; next action only after prior
result consumed. ACK is the only continuation of the SAME pending action.
Child validates exact phase and action before any effect. Parent rejects
unsolicited or stale output before calling a consumer. Correlation is
not authority, and a valid token cannot target a different Process/Loader.
Exact nested types:

- Ref = {requestId,viewKey,generation}, distinct 32-hex tokens and positive
  JS-safe integer; same R4b correlation. Fresh per operation and across
  Process/Loader recreation. Never use an internal operation identifier.
- HistoryScope = {treeKey:"CHERRY",generation,sessionId,revision,viewKey}.
  generation positive JS-safe; revision nonnegative JS-safe; sessionId
  and viewKey distinct 32-hex public aliases; history-only generation/
  viewKey independent of status. No raw journal IDs.
- PageRequest = {requestId,treeKey,generation,sessionId,revision,after,limit}
  exactly existing UI2 reference keys. requestId fresh 32-hex selected by
  parent; after nonnegative safe integer <=revision; limit 1 or 2 only.
- R4b Unit = exact existing six-field envelope (requestId,viewKey,generation,
  sequence,kind,statusPacket); sequence starts 1, safe integer, transition
  only, existing exact seven-field STATUS or WITHDRAW/null.
- Page = exact existing M4 history-display schema and fields, with public
  session/turn aliases and parent-selected requestId (see below). No
  model, provider, recorded time, operation/attempt IDs or private titles.

## Actions, responses and state

All data shapes below are exact; braces describe object keys, not optional
fields. All response envelope trial/action equal the outstanding request.
No generic error text, raw trace, or separate unsolicited status stream.

| Parent kind and data | Child frames, in order | Effect / gate |
| --- | --- | --- |
| HELLO {} | RESULT {code:"READY",units:[]} | New child only, no user append |
| NEXT {} | OPEN_OFFER {ref}; after matching OPEN_ACK {ref,accepted:bool}, RESULT {code:"TURN_STARTED",units:[]} | Only idle, next fixed R5 turn; no append before true ACK |
| STEP {ref} | RESULT {code:"ACTIVE" or "TERMINAL" or "UNKNOWN_HOLD",units:[0..2 R4b units]} | Exactly one existing R5 advance, matching active scope |
| STOP {ref} | RESULT {code:"STOP_OBSERVED",units:[0..2 R4b units]} | Exact active scope; no cancellation receipt |
| REOPEN {} | RESULT {code:"JOURNAL_REOPENED",units:[]} | Verified committed idle only, existing R5b connection reopen |
| HISTORY_ATTACH {} | HISTORY_OFFER {scope}; after matching HISTORY_ACK {scope,accepted:bool}, RESULT {code:"HISTORY_ATTACHED",units:[]} | Explicit read-only idle attachment, no execution |
| HISTORY_PAGE {scope,request} | PAGE {scope,page} | Exact accepted history scope and pinned M4 request; no status units |
| CLOSE {} | RESULT {code:"CLOSED",units:[]} then normal EOF/exit | Explicit cleanup, no effect/rollback receipt |

For any semantically refused valid action, the sole terminal response is
RESULT {code:"REFUSED",units:[]} or {code:"UNKNOWN_HOLD",units:[]};
close trial after refusal in the first witness. Malformed/uncorrelatable
input, missing/late ACK or partial IO may close silently. False ACK never
appends. RESULT codes are local fixture outcomes, NOT receipts, positive
permission, successful model inference or evidence a result painted.
No result can reopen a closed view. A successful CLOSE requires matching
result, drained stdout with no remainder, and normal child exit; on
uncertainty retain HOLD, never claim rollback. Child must not exit before
cleanup on normal CLOSE. Parent teardown is independent of status STOP.

One stateful owner at each end. HELLO -> idle -> NEXT waiting ACK ->
active -> STEP/STOP -> terminal idle on known commit, or blocked on
unknown/abort -> CLOSE. REOPEN is allowed only after exact R5b verified
commit and no stream. HISTORY_ATTACH and PAGE are permitted only idle
with independently verified durable fixture state (initial empty/known
committed; known ABORTED read-only after STOP requires explicit Mind
agreement on durable inspection, not the UNKNOWN_HOLD label). A fresh
NEXT/REOPEN/CLOSE clears old presentation/history locally before action,
invalidates old child-side correlation before invoking R5; no queued
WITHDRAW can target the replacement. Do not automatically continue or
send a new turn after STOP/unknown. HISTORY_ATTACH may follow REOPEN
without NEXT once the independent history-only seam is implemented.
No action simultaneously executes and reads history. Do not infer
revision change from a status label. Explicit fresh history attach
required after any operation mutation. This deliberately limits the
first native witness; later concurrent history/execute is a new contract.

## OPEN handshake and actual consumption

Parent explicitly starts NEXT and stores pending action and exact original
Process/Loader/gate before sending. Child uses R5's existing open callback
to emit OPEN_OFFER, then waits on bounded pipe read for exact same action,
trial/ref and true/false ACK. Child independently checks state, not trusting
UI authority. Parent validates offer in pending NEXT only, observes actual
eligible original Loader, installs whole ref, calls openRuntimeLifetime
once after initialized/eligible. True ACK only if accepted local open
and still current; false or missing ACK prevents durable append.
The child callback's local return is a handshake outcome, never attested
view/currentness. Lost ACK / timeout after possible append -> UNKNOWN_HOLD
and no replay. Parent never blocks GUI or trusts incoming ref as eligibility.

R4b callback on child side copies only validated status units into the
bounded per-action result, no UI object or unbounded queue, returns None.
That is local submission, not the synchronous Qt witness or actual paint.
Parent validates complete action result and all units before consumption,
then independently checks original Process, Loader, gate, correlation and
sequence immediately before each void receiveRuntimeUnit. A refusal or
callback failure after partial paint invalidates ONLY original ref; never
retarget or replay. Old-process output/exit cannot clear new Loader.
Owner can independently clear on detach even without output. On loss of
eligibility/transport or parser failure the first R6 witness closes that
trial and reaps the tracked child (bounded graceful exit then kill only
that child if required). No automatic new trial. This stricter initial
cleanup differs from same-process detach-and-continue; it is not a STOP
or protected revocation/rollback receipt. No native model is running.
Child-side status units are never sent on HISTORY_PAGE. NO_UPDATE emits
zero units but the explicit STEP still returns one RESULT to release
the action slot. No status-triggered page request or synthetic reply.

## History-only attachment and aliases (requires DOC4F/UI2 agreement)

R5b history_page currently binds to an operation and generates requestId.
Do not call start_next or fabricate OperationRef for a read-only reopen.
Propose a narrow Mind-owned projection seam over the same journal:
independently resolve canonical cherry session and durable revision,
fresh read-only B6 context/attachment without an execution operation,
stable random public session and per-turn aliases maintained only in
the finite host lifetime. No raw IDs transmitted, no second DB; aliases
survive connection reopen, not child death. Mapping exists before page
serialization; reject unrecognized/reused/incorrect alias; never derive
it from QML. Scope offer is metadata-only, from independently read
canonical state, accepted only for pending explicit HISTORY_ATTACH
and current Process/Loader; parent retains scope separately from status.
Parent chooses fresh requestId and invokes existing history openPage/
nextPage before dispatch. Child independently validates scope, request
pin, cursor and current durable revision in read transaction, projects
existing M4, substitutes only stable public aliases and echoes exact
parent requestId; no title/body added except allowed fixed public rows.
Parent checks PAGE outer scope against pending action and actual current
history lifetime before invoking existing M4 validator/controller.
No response-derived expected revision, no silent fallback to literal
sample, no status-to-history refresh. M4 original 64KiB bound remains,
outer R6 ASCII serialized bound stricter; whole page refused, no
truncation. UI2 owns existing fixture's mutually exclusive literal
preview vs connected history mode; no competing controller/feed.
DOC4F owns exact mapping/custody and history-only context semantics.

## VERIFY / acceptance matrix before activation

R6a: owner/security review this document, agree types, budget, history
mode and failure semantics. No code or installed activation in this PR.
R6b: child byte parser, canonical exact schemas, duplicate keys,
oversize/truncated/invalid input, bad IDs/phase/ACK, finite limits, actual
no append before true ACK and no replay; actual existing R5 host.
R6c: native Quickshell Process incremental parser witness with fragment/
coalesce, non-ASCII, overflow without LF, EOF, stderr and timeout/exit;
verify actual version behavior and bounded retained accumulator, not a
claimed raw native allocation guarantee. UI1 and UI2 own parent code.
R6d: actual joined disposable panel two turns, explicit fresh M4 history
and committed-idle reopen, STOP with independent durable result, old
child/Loader output/withdrawal/refusal/exit isolation, callback fail
after paint, no per-DELTA units and no implicit history, verify SQLite
outcomes via CI owner evidence without exposing IDs to UI.
Nurse2F independently reviews exact heads and raw CI. DOC3F verifies
both process ends and protected-data refusal. Heart owns resource safety;
native Ollama, selectable SEND, authenticated custody, protected release,
process crash recovery, operator visual acceptance and production HOLD.

## Decisions pending

Confirm canonical encoding, caps/deadlines, strictly closed-on-loss
first trial vs detached continuation, child startup/cleanup mechanics,
single action/result batching, history-only attachment/alias ownership,
and actual native parser limits. UI1/UI2/DOC3F/DOC4F ACCEPT/REVISE
required before wire freeze. No installed transport code in this proposal.
