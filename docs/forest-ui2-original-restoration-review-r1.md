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

## R1 implementation scope approved

Nurse2F #7162318447 accepts exact #2690 a5550565 and all four owner
agreements (#7161256592, #7161314589, #7161359214, #7161019466).
PublicRestorationReview.qml is an isolated, nonmounted synthetic view.
Local test owner independently sets syntheticOwner and entire ownerScope
(CHERRY, distinct opaque 32-hex taskAlias/viewKey, positive planRevision).
Explicit openReview(ref) precedes receiveReview(ref, rows). The only allowed
ordered rows are CONTINUITY=PRESERVED, CONTEXT=REVIEW, WORKSHOP=AVAILABLE,
MODEL_FORM=DORMANT, REASONING=UNKNOWN; fixed local labels, never raw inputs.
Refusal and malformed current plan clear rows; stale ref ignored; dismiss,
visibility/viewport or scope loss clears. Fresh view required for every open;
64-view local replay cap, not actual owner custody. No real grant, plan query,
season, restored resources, decision/apply, history refresh or R6 action.
Existing composed preview native witness expands 22 to 31 phases, then mounts
only the isolated review at 480x240 and 300x160. Tests cover default-off,
explicit open, exact rows, stale/replacement, malformed/duplicate plans,
dismiss, independent owner and viewport loss, no fallback, unload.
Actual keyboard/focus and panel placement remain UI1 joined review; local
Dismiss is nonexecuting. No ForestW or shared controller change. CI pending.


## R2 proposed dormant task selection // separate from restoration

Census #7168544466 and Nurse reconciliation #7168860879 identify dormant
task selection as an outstanding UI2 recovery gap. Rechecked target
main dcf22ace4872fab3e408051650980483dbe52e7c; R7a #2703 is a merged
Runtime proposal, not a dormant catalog implementation. Its R7b
retirement eligibility witness is a separate pending scope decision.
Original task_session.py a2458c4e, list_winter_tasks and
begin_spring_cleaning, re-read at frozen original 28895aaf.
Historical listing ordered summaries by retirement order without loading
full content on selection. It also exposed raw task IDs, path, adapter,
reasoning and model metadata, silently skipped damaged files, and
used legacy timestamps as a fallback. Recover the discovery/selection
separation, not those fields, storage conventions or ambiguity handling.

### Interaction sequence (proposal, not a transport or storage schema)

| User intent | Local presentation effect | Explicitly not performed |
| --- | --- | --- |
| Open dormant-task browser | Request a separately scoped metadata view, initially empty/pending | Enumerate private files, read journal bodies, start a task |
| Receive current list | Display a bounded, owner-ordered safe summary or distinguish empty/refused | Infer Winter from PAUSED, hidden UI or timestamps |
| Select one listed row | Highlight one current opaque selection; retire old review scope | Query history, wake task, allocate model or apply old permissions |
| Open Cleaning review | Ask for separately current plan for selected identity | Claim active slot, enter Spring, restore context |
| Dismiss, change Tree or lose view | Clear selection and affected review; no automatic fallback | Retire or delete a durable task |

Real dormant metadata and task/plan identity remain Runtime-owned.
Actual lifecycle/custody proof precedes publication; history OPEN
scope, B1 conversation revision and REOPEN are not dormant-list evidence.
Mind owns context truth, Security disclosure policy and Heart admission.
A list is neither a lease nor a claim; selection is not a decision to restore.

### Smallest proposed isolated fixture scope

Subject to owner and Nurse acceptance, implement a native, nonmounted,
read-only synthetic selector in UI2. Reuse the existing review component
and shared local shape validation; no extra service, database, parser,
sender, or alternative history controller. One explicit local list
lifetime, one local selection, at most one review scope. Proposed fixed
fixture inputs: CHERRY, fresh independent list-view token, positive
catalog revision, up to three owner-ordered rows with distinct opaque
32-hex task aliases; labels constructed locally as PUBLIC TASK 1/2/3.
No arbitrary titles, private content, raw IDs, paths, model or adapter
names, timestamps or resource estimates. Label the entire surface
SYNTHETIC // NO LIVE DORMANCY. Catalog revision is synthetic correlation,
not a durable lifecycle revision or grant. A complete empty list is
distinct from unavailable, stale or pending; refuse over-limit or
malformed lists instead of silently truncating. Do not imply a complete
real catalog from this fixed example. The proposal establishes no
production fields or new frozen wire contract.

Parent sets whole independent list scope before explicit open; a response
cannot open the browser or establish owner currentness. Stale response,
selection and dismiss intent cannot mutate a replacement scope. Current
malformed/duplicate receipt clears the list and selection. Selection
requires a displayed current row, never an index alone. Selection change
or list invalidation retires only its associated original review before
a new review is possible. Opening review is a separate explicit action;
require independently owner-supplied R1 taskAlias/viewKey/planRevision
matching selected alias, no reuse of list revision as plan revision.
Review uses existing PublicRestorationReview exactly; no auto-populate
sample rows on selection, no automatic activation or positive action.
No list refresh on model status/history events. No auto-select after
reorder/reopen. Preserve no authority and SEND/STOP/restore locked.
Local lifetime cap and exact values require final scope agreement.

### Acceptance matrix

- Default closed, explicit open, pending vs empty vs refused vs displayed.
- Distinct aliases and owner order; duplicate/malformed/over-limit input
  refuses entire current list; no data display from stale owner scope.
- Explicit selection only, no select by stale row/index or unknown alias.
- Selecting a different row retires old review without creating a new one.
- Review opens only on independent current R1 plan scope and explicit
  action, distinct from list request and selection; no grant inferred.
- Replacement catalog/view, Tree change, viewport or owner loss clears
  local selection/review; old list/plan/click cannot clear or populate new.
- Dismiss and unload cannot reopen; no implicit history, execution,
  restoration, selection of first row, automatic query or durable writes.
- Native normal/compact fixture acceptance; actual ForestW placement and
  keyboard/focus integration require UI1 agreement; keep existing 41-phase
  R6 replay and independent history/status behavior intact.

### Required owner decisions before implementation

DOC2F: ACCEPT/REVISE the fixed synthetic catalog scope and separate list,
selection, plan and real lifecycle identity. No claim that R7b is approved,
that actual retired tasks exist, or that R7a is a real catalog.
DOC4F: ACCEPT/REVISE distinction between list summary and independently
versioned context review; no content read or automatic rehydration.
DOC3F: ACCEPT/REVISE fixed synthetic metadata allowlist, currentness/refusal
and no protected disclosure or rights. Real list/title access remains
separate protected operation.
UI1: ACCEPT/REVISE isolated fixture and eventual existing-panel placement,
focus and lifecycle; no second production menu or controller.
Nurse2F: exact scope disposition before executable R2 fixture.
R6 pending #2761/#2764/#2765 continue independently. No actual dormant
list, Spring entry, plan decision, protected action or production mount
authorized by this documentation.
