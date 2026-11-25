# UI2-R1 // Original Forest restoration review (proposal)

PATIENT: The-Post-Apollo-Project
ROOM: Forest Integration
OWNER: UI2 functional integration
STATE: Proposed presentation contract; read-only recovery, production HOLD.

## Source and authority

Recovery assigned in #2161 comment 7160677299. UI2 gap assessment
7160744491. Historical original repository
kudokudo1/The-Post-Apollo-Forest-Project at
28895aafdddb07cf402f1e75574eea1ee79a516d, read-only.

Under raw-import/2026-09-22-transfer/The-Forest/bristlecone:
- runtime/task_session.py (blob a2458c4e): list_winter_tasks lines
  4724-4915, plan_spring_restoration 5788-6130,
  record_spring_restoration_decision 5231-5405,
  complete_spring_cleaning 3844-3890. These are separate discovery,
  planning, selection and verification mechanisms, not one restore action.
- model_form/continuity.py (0ad9769c): frozen same-task and execution-context
  instruction composition and completed exchanges; metadata inspect does not
  expose instruction contents. No provider runtime session in continuity.
- ui/actions.py (f8da410d), ui/keybindings.py (252d1614),
  ui/presentation.py (c1363848): stable action intent separate from invocation,
  menu-specific key conflict validation, host-independent presentation.
- raw-import/2026-09-22-transfer/Forest Logs/forest_core_design_doctrine_seasons_spirit_progressive_depth_2026-08-09.md
  (15e4e11a): Winter is dormant, not deletion; Spring lists Cleaning first.
- recovery/AUTHORITY.md: surviving code and doctrine are recovery evidence,
  not automatically certified/canonical or live permission.
No historical source copied; no certification claim.

## Current source comparison

Target main 52fb321a246632366d49902040d5b1298f63309f.
PublicConversationFixture.qml f016bd91, PublicHistoryViewState,
PublicHistoryDisplay.js, PublicRuntimeStatusView and shared ConversationFeed
already cover independent revision-pinned history/status presentation.
#2670–#2673 merged. R6a revision 1 frozen for disposable public CI only;
do not extend its envelope or actions with restoration.

B1 session_journal_v0.py d1533f150 uses OPEN/PAUSED/ARCHIVED and increments
revision on state change. None of those values establish seasonal truth:
PAUSED is not proof of Winter or resource retirement; ARCHIVED cannot
silently reopen. M4's existing OPEN history contract is not a dormant
task list. R5b connection reopen is not Winter or provider restoration.
Mind #2683 proposes layered selected Hot Context, not a restoration plan.
Body #2682 proposes static Workshop reference with live season unknown;
UI2 must not create another seasonal glossary or edit that view.
Security #2684 preserves deny-only distinctions, not grants.

## Proposed owner responsibilities and interaction

1. Dormant task selection (later UI2-R2): explicit user selection of an
   opaque task reference from a Runtime-owned scoped read-only list.
   No database paths, original internal IDs, historical model/adapter
   bindings or private titles in a public fixture. Ordering is supplied
   by owner; UI must not infer retirement from timestamps, absence or a
   hidden surface. Selecting a row never loads history or starts a task.
2. Spring Cleaning review (UI2-R1): explicit open/dismiss of a read-only
   plan for an independently selected task. Review is not Spring transition.
   Title "SPRING // CLEANING REVIEW" denotes feature intent, not live season.
   Unknown/closed/refused must not display previous plan or sample fallback.
3. Later decision recording is a distinct user intent; no implicit apply.
   Original record_spring_restoration_decision validates only offered
   Workshop/capability candidates. It does not activate them. Modern
   recording/apply require separate reviewed Runtime/Mind contracts,
   independent authority and Heart admission. Not implemented in R1.
4. Completion may only reflect independently verified owner outcome;
   never infer Summer from clicking a control, a plan, history load, or
   successful local callback.

## Proposed minimal presentation semantics (not a wire schema)

Owner-held scope must independently identify selected Tree/task, durable
plan revision and fresh local view lifetime. Do not adopt these fields
from an arriving plan. DOC2F/DOC4F choose exact task and revision semantics;
B1 conversation revision alone is insufficient for restoration plan identity.
UI1 owns placement and actual host lifetime; UI2 owns read-only display.

Fixed semantic categories for first synthetic review:
- PRESERVED: durable continuity known retained, not active resources.
- AVAILABLE: owner verified already available; not a permission grant.
- REVIEW: owner offered candidate requiring separate decision/revalidation.
- DORMANT: not selected for activation; previous reasoning/model intensity
  never restored from history alone.
- UNKNOWN: no current evidence. Never promote to available.

The old planner's keep/available/review/leave_dormant are behavior
references, not copyable packets. It contains previous/current working
sets, raw task IDs and runtime session bindings; these are specifically
excluded from a public UI2 fixture. DOC4F and DOC2F to agree which fixed
categories can be projected (e.g. conversation continuity, selected
knowledge, Workshop, capability, reasoning, model form), bounded
cardinality and exact safe labels. Display only bounded, allowlisted
metadata, no private text/prompt, arbitrary title, provider/model path,
runtime/session IDs or raw exception. All actions non-executing in R1.
No authority inferred from displayed category or historical Spirit label.
No new controller, DB, process parser, sender or transport.

## Acceptance criteria for first implementation

Use one UI2-owned additive isolated presentation/test, then UI1-approved
placement in existing controls. Do not modify reviewed R6 fixture or
shared panel before ownership/metadata agreement. Verify:
- default closed; no query, execution, history refresh or model load;
- explicit matching open only; fixed read-only example, clearly labeled
  synthetic, never presented as an actual active plan or actual season;
- all categories and unknown state distinctly labeled; Cleaning first;
- stale task/view/revision plan cannot populate or clear replacement;
- current refusal, invalid data or owner scope loss clears affected view;
- no automatic return to old example after failure/detach;
- read-only, no SEND/STOP/restore/apply activation, no grants;
- selection/dismiss/review never mutate underlying session or context;
- compact/normal placement and keyboard/focus checks after UI1 agreement;
- status and M4 history remain independent; existing R6 native coverage
  stays intact. Independent Nurse2F and security review at exact head.

## Decisions required before code

DOC2F: canonical dormant task metadata and independently observed plan
revision/currentness, read-only vs real lifecycle transition.
DOC4F: safe retained/review/dormant/unknown context summary, no raw
instructions, capability promotion or private data.
DOC3F: provenance and fixed public allowlist, no restored authority.
UI1: location, explicit review entry/dismiss, geometry and no duplicate
Workshop reference. UI2: existing presentation reuse and scoped consumer.
Nurse2F: independent scope review, operator acceptance separate.

R6b/c/d continues unchanged. This documentation PR is not approval of
new protocol, UI source, installation, inference, or protected release.
