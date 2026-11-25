# Runtime original lifecycle recovery // R7a proposal

PATIENT: The-Post-Apollo-Project · Forest Integration · DOC2F Runtime.
Development ACTIVE; native model, protected data and production HOLD.
Source-only owner coordination; not a frozen contract or permission to act.

## Evidence and ownership

Original read-only source: kudokudo1/The-Post-Apollo-Forest-Project
at 28895aafdddb07cf402f1e75574eea1ee79a516d, under
raw-import/2026-09-22-transfer/The-Forest/bristlecone.
Assignment #2161 comment 7160677299; succession 7161256592.
Target main 52fb321a246632366d49902040d5b1298f63309f.
R6b #2696 ec9ca309 remains separate and unmodified. Frozen R6a R1
is CI-only and cannot transport lifecycle operations.

| Original mechanism (source blob) | Current evidence (source blob) | Recover / do not infer |
| --- | --- | --- |
| task_session.py a2458c4e: end_task 6227+, lock, durable Winter record before clearing active slot | B1 session_journal_v0.py d1533f15 set_state 231+ checks owner/revision/time; R5 7dba584a close/reopen | Recover durable same-task retirement with no loss or double activation. PAUSED/ARCHIVED and close do not prove Winter or model release. |
| list_winter_tasks 4724+, load_winter_task 6130+ | B1 sessions/turns and M4 public history | Discover scoped metadata separately from content/activation. M4 OPEN fixture is not a Winter registry. |
| begin_spring_cleaning 4976+: empty active slot, durable worksheet, write active then cleanup dormant record | R5b reopen keeps same local journal; UI2 #2690 proposed synthetic review | Separate actual dormant selection, task claim and worksheet from review display. No auto activation, deletion or adoption of historical runtime IDs. |
| plan_spring_restoration 5788+, record_spring_restoration_decision 5231+, apply_spring_restoration 2712+, complete_spring_cleaning 3844+ | B1 revision + R3 events, no equivalent plan revision in reviewed seams | Read-only plan, explicit intent, authorized apply, independently verified completion; independent plan revision and currentness. |
| session_identity.py 64e97968 and session_store.py fff28521: execution context + binding, adapter and provider session ID distinct | I2 model_binding_i2.py e8a9a5d1; R3 runtime_events_r3.py 291dbaa4 OperationRef; B3 turn_bridge_b3.py c5dbbc29 | Preserve exact task/context/binding/attempt distinction; fresh provider session on uncertain old lineage; no old credentials or live session assumed. |
| model_residency.py a19a754c: compatible binding can share weights, not execution state | Heart H2 heart_resource_custody_h2.py 55100576 fixture-only custody | Separate execution quiescence from retained shared weights and actual release. Never unload another task's weights or credit unobserved memory. |
| conversation_continuity.py 39d2a20b; turn_composition.py 12c472b8: completed exchanges and bounded reference composition | B3 atomic attempt/context and Mind M2/M4, M7 proposals #2683/#2691 | Reuse committed continuity and exact revision, Mind owns selection/assembly. No inherited authority or private context via restored bindings. |
| task_session.py guarded binding/handoff 8284+, 8406+, 8660+, 9254+, 10565+ | R2/R3 one-shot STOP/commit arbitration; B4d recovery_inspect_b4d.py e4f4a537 | No automatic retry or optimistic rollback. B4d local RESERVED/ABORTED/COMMITTED is not C5 settlement or provider quiescence. |

Historical file duplication favored recoverability after interruption.
Do not copy the YAML active-slot/Winter-file implementation, best-effort
provider teardown or old resource assumptions. Prefer an atomic durable
transition in existing owned storage if ownership/schema review establishes
it is appropriate; no second journal or daemon. A duplicate or contradictory
recovery record is HOLD, not permission to choose the newest timestamp.

## Proposed lifecycle invariants (for owner agreement)

These are conceptual states, not a new wire or database schema.

1. Explicit retirement intent binds independently resolved principal, Tree,
   Task/execution context and current task revision. Freeze new dispatch
   before resolving the current attempt. A stale intent cannot retire a
   replacement task. Preserve committed conversation and its revision.
2. Resolve existing B3 attempt locally via B4d. RESERVED, ambiguous receipt,
   lost worker or contradictory identity remains UNKNOWN_HOLD. STOP request
   or client EOF is not terminal proof; do not auto-abort after commit entry.
3. Verify exact provider/runner terminal outcome and no remaining active work
   using independently attributable evidence. Reconcile H2 custody with
   Heart; an idle shared residency can remain resident only under approved
   accounting. Never interpret retained weights as active task or free RAM.
   Protected authority/settlement requires Security's separate evidence.
4. Only after required terminal, quiescence and custody checks, durably
   retire same task without erasing committed continuity; then acknowledge.
   On ambiguous write outcome, inspect exact persisted identity/revision and
   hold rather than retry. Atomic storage and native evidence are not yet
   implemented or approved. A new activation cannot pass an unresolved
   conflicting retirement.
5. Discover dormant metadata under current authority, no content read or
   resource activation. Selection and review are read-only. Independent
   task identity, view lifetime and plan revision must match; UI2 aliases
   are presentation only. No R6 action or dependency on B1 revision alone.
6. Actual Spring entry requires explicit intent, verified dormant identity,
   exclusive claim and durable worksheet. Plan changes invalidate earlier
   decisions. Retain references as advisory, revalidate Mind context and
   Security permissions, then record choices without executing them.
7. Apply requires exact current plan/decision, Heart admission and Runtime
   enforcement, with new operation identity. No previous provider session,
   reasoning intensity, capability or grant restored from historical state.
   Unknown apply holds; no auto retry. Summer/completion requires separate
   verified applied state, not a successful click or local history read.

## First bounded implementation gate

Propose R7b as an isolated disposable retirement eligibility/transition
witness using existing B1/B3/B4d evidence, after the exact owner contract is
agreed. No provider, no new storage engine, no production or seasonal claim.
Do not edit shared B1/B3 until Mind/Security custody and writer ownership
agree. H2 is a fixture reference, not independently verified release.
Use explicit fixture provenance and all authority/action flags false.

Negative matrix for review: active/RESERVED attempt; STOP-only; local
COMMITTED but provider still running; local ABORTED but unknown settlement;
wrong task/Tree/binding/attempt; stale revision; unknown quiescence;
shared weight residency vs task work; duplicate retirement; interruption
before/after durable commit; conflicting active/dormant evidence; stale
restoration plan/decision; revoked context/authority; failed Heart admission.
Verify no loss of original rows, no duplicate activation or automatic retry,
and no inferred authority. Native provider/host changes need separate approval.

## Owner decisions requested

- Mind: exact task-to-continuity reference, snapshot and plan invalidation;
  whether existing journal can support the lifecycle record without a new
  store, transaction ownership and explicit retrieval boundary.
- Heart: distinguish exact attempt quiescence, release accounting and
  retained compatible residency under H9; no availability credit from STOP.
- Security: current authority and exact terminal/settlement evidence,
  protected writer custody, revocation and unknown outcome handling.
- UI2: prior exact five-row synthetic review ACCEPT unchanged; real plan
  metadata is not yet approved. UI1: no mount or R6 wire change.
- Nurse2F: independent scope review of R7a and approval of bounded R7b
  candidate before executable lifecycle work. Operator acceptance separate.

R6b remains at its independently reviewable head. No code, database,
native runner, existing provider, shared UI, production or host change here.
