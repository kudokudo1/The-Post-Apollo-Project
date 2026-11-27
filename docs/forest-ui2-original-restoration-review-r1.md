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


## R2-H1 // Dedicated host entry and original-only dismissal proposal

Nurse scope closure #7170548859 and scoped ACCEPTs #7170572869 and
#7170573728 are verified. Combined #2792 exact 2568bf90 is open, 8/8
workflows and 65/65 native phases; #2805 exact d319fd3b is open, 8/8,
28 host placement phases (14 at each supported size). The four UI2 blobs
match. Main a4d04135 at intake still has 41 replay phases, and #2805
borrows the inactive preview Loader only in CI. These are not installed
entry or physical keyboard acceptance. Merge #2792 first under operator
control, then reconcile #2805 to actual main and requalify. No new
selector implementation is proposed.

### Proposed UI1 host contract (requires separate approval)

Current ForestW uses PREVIEW (forestPublicPreviewButton), the measured
sessionPreview area, PublicPreviewGate and forestPublicPreviewLoader;
the root Escape handler closes active overlays/menu. Reuse the single
sessionPreview viewport, not the Workshop popup, another panel, or
a second conversation controller. UI1 chooses exact header placement
within the existing layout, without overlap at compact size.

- Introduce a distinct explicit DORMANT entry intent, clearly marked
  synthetic, default closed; no automatic mode switching. One host-owned
  mutually exclusive local mode: EMPTY, CONVERSATION or DORMANT. A
  different mode requires closing the current one and a new explicit
  entry. Do not change trusted session semantics or use PREVIEW as
  an implicit dormant command.
- The original public eligibility gates remain mandatory: visible open
  menu, CHERRY, independently known untrusted host, exactly zero active
  sessions, measured viewport at least 300x160. Unknown eligibility
  refuses. Neither mode may establish real owner evidence, query a host,
  alter permissions, or dispatch. Existing preview behavior must remain
  unchanged. Do not add a parallel gate or store; UI1 owns any change
  to the current gate and Loader.
- Host owns a fresh local incarnation per explicit entry, independently
  pinned whole catalog scope before openCatalog. One fixed local catalog
  of at most three opaque public aliases, no user text, network, real
  session IDs, disk read or lifecycle interpretation. Selection never
  opens a review. Fresh independent plan scope must be provided for the
  explicit review intent (not generated by arriving content). Keep
  existing R2 API, both 64 caps and 120-second monotonic catalog deadline.
  If additional intent signal or fixture data adapter is needed, agree
  exact minimal seam with UI2 before changing accepted component.
- Explicit catalog dismissal emits the existing dismissed signal after
  local clear. The parent connects only the original Loader item and
  retained incarnation; on callback independently confirm current mode,
  exact item and incarnation, then retire host pins before disabling
  Loader. Disconnect or invalidate on loss. A late signal from a retired
  object cannot close a replacement. Never infer dismissal intent from
  a derived state binding. Review dismissal returns to list, not host
  close. On timeout/owner/viewport/Tree/menu/host eligibility loss,
  retire original local scope and host mode; no return to old data or
  automatic conversation. Expiry may clear the component; any host
  expiry notification must be separate from explicit dismissal, scoped
  to the original item, with no new authority.
- Return to NO ACTIVE SESSION; preserve prompt draft on local close
  except existing menu-close semantics. Release local focus before
  removal, then restore to original eligible initiating control or
  existing prompt, not a new Loader item. Escape dismisses active review
  first, then browser, then follows existing menu behavior, with scope
  checks; physical keyboard/compositor focus requires separate native
  operator acceptance. SEND/STOP, Workshop and real restoration remain
  locked in synthetic mode.

### Required acceptance

Existing 65 composed and 28 host placement phases preserved. Test actual
dedicated entry and original-only dismissal wiring, not manual borrowed
Loader toggling: default off, competing entry refusal, original draft,
explicit open/select/review, review return, catalog close to empty,
old callback during replacement, scope/Tree/viewport/menu/host loss,
expiry including no automatic reopen, Loader error, narrow viewport,
normal/compact geometry, exact original focus request and unchanged
conversation controls. Verify no real session/permission/resource
mutation or hidden network/file operation. Separate user-reported
physical keyboard/visual acceptance from CI. No product mount code
until UI1, Security, Runtime and Nurse approve exact synthetic scope.

### Remaining backend boundary

R7c-b #7170547577 permits an owner-exclusive fixed-public B1/B3 transaction
fixture only; ACTIVE/PENDING/WINTER revisions and durable original
effect outcome do not constitute a real catalog or protected read.
Runtime owns real task lifecycle and metadata, Mind owns independently
versioned retained context, Security owns disclosure/decision/effect
custody, Heart owns admission. Later selective restoration decision
recording and application require their own contracts. No proposed
H1 entry, selection, review, dismiss or expiry creates a durable
retirement, Spring transition, claim, grant or resource action.


## S1 // Distributed seasonal indicators — operator direction supersedes menu priority

Operator clarification and confirmation (Hospital #2161 comment
7171079179): put each entity's own season at its normal location, not
one central dormant destination. This supersedes R2-H1 dedicated global
DORMANT entry as the primary presentation proposal. Preserve accepted
R1/R2 contextual review/selection code and existing native coverage;
do not implement a competing global entry while UI1/Nurse reconcile
the revised direction. This is design only, not a new state machine.

Use the existing Body recovery doctrine (4ceb4f5c): Spring Cleaning
first, Summer Growing, Fall Shedding, Winter Dormant (not deletion).
Use fixed icons and short labels/tooltips in addition to color:
spring sprout/green, summer sun/yellow, fall leaf/orange, winter
snowflake/ice blue. UNKNOWN is neutral and distinguishable from Winter.
A season is not an activity indicator, permission, connection state,
resource claim, wall-clock season or model residency observation.

### Existing surfaces and gaps verified at main f4518d5c

| Entity surface | Actual source | Proposed placement / boundary |
| --- | --- | --- |
| Tree | ForestW.qml a17ab91a treeSlots, treeSelectorRepeater/DockButton, selected Tree chat heading | Small trailing or corner indicator within each existing Tree row; mirror exact selected Tree status in heading only if space permits. Preserve 59px row, identity ink, artwork, hover/selected glow and hit target. |
| Colony/chat | ForestChatList.qml c43db1d6 delegates and selected chat workspace | Small trailing per-row indicator and optional same-status selected heading. Chat is a potential Colony presentation, not proof of canonical Colony identity. Runtime must define mapping. |
| Clone/worker | No verified canonical worker-instance list in the inspected ForestW/ForestChatList surfaces | Place on existing instance row when owner identifies/recovers that surface; do not repurpose resource observation, Tree slot or equipment slot as worker. |
| Assignment/task | Existing isolated PublicDormantTaskSelector and PublicRestorationReview | Contextual task rows under their verified owner when available; indicator per assignment. Existing fixed-public Winter list is a fixture, not evidence that actual tasks are dormant. |

ForestW currently declares chatHostTrusted=false and activeChatSessions
empty; treeSlots are five static presentation identities. ForestChatList
uses ForestChatSessionPolicy.openSessions with strict seven-field B1
metadata, and admits OPEN only. PAUSED/ARCHIVED are excluded; do not
rewrite its authorization/filter semantics, attach arbitrary seasonal
fields to B1 records, synthesize missing Colony/worker rows, or present
fake counts. Showing retained dormant entities in their normal lists
needs a separately owner-approved metadata projection, not relaxing
the current filter. No actual entity enumeration is authorized here.

### Proposed bounded UI2 presentation scope

Request a single reusable read-only indicator, initially tested in
isolated fixed-public examples, no host mount, service, database or wire
change. Use fixed local enum/labels/icons, no arbitrary text from input.
Expose UNKNOWN when no independently current supported season is known;
distinguish stale/unavailable internally without implying another
season. Exact entity identity, parent scope where applicable, and
independent lifecycle revision/currentness must be provided by the
responsible owner before any live projection. No inherited season:
Tree and Colony can differ from their descendants; no aggregate season
derived from any number of child states. A selected item and an inactive
item are not necessarily Summer and Winter respectively. Invalid or
lost current evidence clears its indicator to UNKNOWN; stale other
entity updates cannot alter replacement. No click-to-transition, hover
query, automatic restoration or change of permissions. Any future
contextual Cleaning action is separate explicit scoped intent, not
an indicator state mutation.

Proposed isolated visual/native tests: four canonical seasons plus
UNKNOWN; same Tree and two distinct child examples with intentionally
different season; independent worker/task examples; no cross-entity
propagation, wrong type/unknown enum/stale scope/loss, accessible
season label, color-independent glyph, normal/compact fit without
changing identity colors or row height. Preserve 65 composed phases,
28 R2 placement phases, 22 R1 placement and joined typed abort/DB
witnesses. Do not count fixture as actual status or operator acceptance.

### Owner decisions before code

- DOC2F: define which entity kinds actually own seasons, exact canonical
  identity and parent/child relationships, current revision and evidence
  source. Existing R7c-b task retirement transaction fixture is not Tree,
  Colony or worker state. Determine whether Clone and worker are aliases
  or distinct identities, and Colony vs chat/session mapping.
- DOC4F: define retained continuity/knowledge scope per supported entity;
  absence of context or history is not dormancy.
- DOC3F: agree read-only minimal metadata, currentness/refusal and
  protected disclosure boundary; no new positive authority.
- UI1: confirm real normal-row locations and exact nonoverlapping
  geometry; no new global dormant panel; do not alter existing palette
  or chat host/Loader ownership. Reconcile #2810 pending host entry
  scope with operator direction before code.
- Nurse2F: authorize precise isolated visual fixture and independent
  review. Live metadata wiring and installed placement require separate
  scoped integration and operator acceptance.

User has approved the design direction, not guessed entity definitions,
new data producers or real lifecycle transitions. No real status is
displayed until independently verified owner evidence exists.


## S2 // Reconciled distributed Colony / member / Assignment design

Status: coordination record, **not executable approval**. S1 reusable
indicator #2831, actual-row rehearsal #2839 and UNKNOWN-only Tree source
mount #2843 are merged. Operator screenshot and visual acceptance
#7175409015 confirm current neutral glyph appearance, not lifecycle
truth, physical pointer/keyboard qualification or other row coverage.
Keep that appearance. Nurse withdrew the centralized H1 entry priority;
do not implement the earlier global DORMANT button. R1/R2 remain
contextual fixed-public fixtures, not a live metadata producer.

### Canonical identity boundary (resolved non-equivalence)

Original frozen 28895aaf checkpoints 0d15621d, 58408002 and d1780343
describe a Colony as one Tree and its Clones, grouped by tree_id.
An Ortet or Ramet is independently addressed by execution_context_id;
binding and runtime-session identities are separate. A member's current
foreground/background or dormant state is not its identity. These are
historical architecture references, not modern authenticated records.

Runtime #7175745212 confirms actual B1 chat records are not Colony,
member, Clone or Assignment records. B1 d1533f15 has session_id,
owner_key, tree_key, title, state and revision, without member/task
lineage. B6r1 b7fdcfc5 TaskContext separates principal, Tree, optional
Clone, task, execution context, generation and origin. It is an
owner-side reference, not a roster or proof of active process.
M2 1085bc56 currently refuses Clone contexts. BarkAttachment can link
multiple presentation recipients to one task, and background work may
have no attachment. Detach is presentation-only. Neither session rows
nor Bark counts establish a roster or lifecycle. Do not derive new
identities, mutate B1 or equate B1 PAUSED/ARCHIVED with Winter.

### Reconciled placement and intent

> Historical S2 placement decision: the exclusive CHATS/Colony view and
> its default below are superseded by operator decision #7202168479.
> Retain this record for provenance; apply the S4 reconciliation below
> for current interaction design. Identity, disclosure and contextual
> restoration safeguards remain in force.

UI1 #7176088888/#7177006429 and UI2 #7176099165 agree on a future
explicitly selected Colony view reusing the existing secondary rail.
Keep CHATS default, identity and OPEN-only filter unchanged. Rail width
184/148/0 means the compact hidden rail stays hidden; no extra window
or squeezed review. Existing Tree rows and indicators remain unchanged.
No fake live rows, sample fallback, guessed counts or automatic first
selection. The following are required behaviors, subject to a separately
approved actual owner projection and host scope:

| User intent | Presentation result | Not implied |
| --- | --- | --- |
| Open Colony view | Independently authorized member rows under exact selected Tree/Colony | Chat membership, inherited season |
| Select member | Exact current member selection, contextual Assignment metadata only | History retrieval, process activation |
| Select Assignment | Exact current Assignment selection | Task claim, Spring entry |
| Explicit Cleaning review | Independently pinned plan for an eligible dormant Assignment, in existing bounded workspace if separately approved | Restoration/apply, authority or automatic conversation |
| Dismiss review | Return to original valid member/Assignment context | Activate or restore whole Colony |
| Scope/visibility loss | Retire original affected selection/review, withdraw stale display | Clear unrelated chat draft/history or replacement |

R1/R2 require at least 300x160. A future contextual review belongs in
the existing sessionPreview workspace only with separate UI1 approval.
Current PublicPreviewGate is CHERRY-only synthetic conversation, not
membership authority. Preserve existing Escape overlay precedence,
local draft on contextual dismiss, and existing menu-close behavior.
Do not replace an active conversation implicitly. No proposed new
Loader mode or executable action is authorized by this record.

### Projection and disclosure requirements

UI2 #7177004561 and Spirit #7177013987 agree that a future owner
projection must bind independently resolved parent/member/task
identity, exact lifetime and current snapshot. Runtime defines the
source, not the UI. Spirit requires independently current recipient
and purpose with separate enumeration, alias, count/completeness,
season and action-detail entitlements. Completeness means completeness
of the authorized projection, not the global roster. If completeness
itself is unavailable or forbidden, show unavailable rather than a
count/empty signal that leaks hidden membership. Authorized row with
denied or unknown season displays UNKNOWN; unauthorized row is absent.
No raw execution, owner or credential IDs exposed as labels.

Acceptance criteria for that later contract:
- Multiple Barks attached to one canonical Assignment do not duplicate
  it. Authorized background Assignment without a Bark remains eligible
  for discovery. Detach never infers retirement.
- Complete authorized empty differs from unavailable/partial/refused;
  no forbidden counts or inferred zero.
- Tree/Colony/member/Assignment states independent; unknown season
  remains neutral; no aggregation from child, model, cache or session.
- Member replacement/lifetime change retires original selection and
  review. Stale or cross-member snapshot cannot populate or clear a
  replacement. Revocation/lost current scope withdraws affected rows,
  selection and cached visible details. Preserve unrelated context.
- Separate explicit Cleaning review and current action entitlement;
  row visibility/selection never grants history, Spring or execution.
- Preserve accepted S1 72 composed phases, 18 actual Tree placement
  phases, 3 default UNKNOWN markers, 28 R2 and 22 R1 placement phases,
  joined DB/STOP/negative and all-size regressions.

### Open owner dependency

No authoritative modern member/Assignment roster or independent
lifecycle producer has been established. Nurse #7176450660 retains
design-only status. Runtime and Spirit must specify exact actual
owner source, mapping, freshness, parent binding and disclosure first;
UI1 and UI2 then request exact bounded implementation approval.
Mind M7g derived-cache design is separate from lifecycle evidence.
No new schema, producer, executable source, synthetic membership,
installed mount, query or authority is proposed in this reconciliation.


## S4 // Unified Tree, Clone and conversation interaction reconciliation

State: design contract, not a connected UI or an implementation claim.
Operator direction #7202168479 supersedes the exclusive S2 placement
above. UI2 #7204240406/#7204310531, UI1 #7204351741, Spirit and Runtime
owner dispositions reconcile the boundary. Nurse #7204663398 and
operator relay #7204485179 authorize bounded owned development without
repeated preliminary approval loops; independent completed-source
review and operator acceptance remain. Production/native/protected HOLD.

### Current disconnected slice versus future projection

UI1 owns S4-U1 host implementation. Its four-file scope retains existing
184/148/0 rail geometry, 55px header, 56px B0 strip, neutral Tree
indicator, chat pane and composer. The selected public Tree name is a
plain elided heading, not identity or membership evidence. The honest
unqualified states are COLONY UNAVAILABLE and, independently,
CHAT HOST OFFLINE or CHAT COVERAGE UNKNOWN. No inferred zero or empty
roster, new filter controls, fake rows, connected source or action
dispatch in S4-U1. This document does not change those four files.

The future unified presentation has one Tree heading and one rail
collection of authorized conversations and member presences. ALL is
the proposed default; CHATS and CLONES are visibility filters only,
not competing workspaces or sources. Preserve standalone conversations
when no authorized member link is established. Do not infer a link,
one-to-one cardinality, base member, role or current work from titles,
B1 rows, process state or model state. User-assigned member display names
take precedence over owner-issued sequential defaults. Names and
numbers are labels, never identity, and missing numbers must not
disclose hidden membership. Runtime owns numbering, namespace, durable
identity, versioned binding and succession; Spirit owns disclosure and
action eligibility.

### Interaction and acceptance proposal for the later connected slice

Keep selected Tree, inspected member, selected conversation and
composer target conceptually separate. A chat target must be explicitly
selected and independently current, authorized and visibly identified
where disclosure permits. Selecting or inspecting a Clone or Assignment
does not silently change the conversation or target. Never dispatch
from a hidden, stale, unknown or unverified target. A filter must not
grant, revoke, rebind or fetch protected data by itself.

| Intent or event | Required presentation behavior | Must not imply |
| --- | --- | --- |
| Open unified view | Show only independently current, authorized projection for the selected Tree | Complete roster, live process or global counts |
| ALL / CHATS / CLONES | Change visibility, preserve an otherwise valid selected conversation and draft | Implicit target switch, history fetch or action |
| Filter hides selected conversation | Keep its current target explicitly identified if permitted; otherwise lock dispatch until explicitly reselected | Send to first visible row or disclose hidden label |
| Select member or Assignment | Inspect separately authorized metadata and contextual controls | Chat retarget, session creation, task start or grant |
| Select conversation | Explicitly establish matching chat target; retain unrelated draft/history according to owner contract | Member reassignment, activation or permission transfer |
| Rename or rebind | Present separately authorized, current, versioned action/result; retain stable identity and original authorship | Rename creates identity, automatic draft migration or history relabel |
| Execution succession | Preserve independently verified durable conversation/member identity; withdraw stale incarnation status | New chat required, replay, old effect settlement or inherited grant |
| Tree change / scope loss | Retire affected view/selection/target and withdraw stale protected data; preserve unrelated authorized context | Global clear, durable deletion or replacement mutation |
| Compact rail hidden | Preserve composer geometry and current target only if safely represented; no hidden rail activation | New overlay/window or invisible actionable controls |

A missing binding differs from an independently authorized unbound
record; do not label a hidden relationship as absent. Complete-empty
requires authorized current completeness for that projection, not
hostConnected, visible row count or silence. Partial or unknown
coverage must not leak hidden records, categories or counts. Separate
member/task/season status from active model, operational home and chat
state. Member home is not execution location or permission.

Preserve S3 scoped stale/withdrawn-view evidence (#2928/#2936);
its single explicit withdrawal is not a general revocation mechanism.
An invalid old response must not populate or clear the replacement.
Exact currentness and source/effect ordering remain owner contracts.
Keep existing R1/R2 contextual Cleaning review separate from selection,
and preserve 300x160 minimum and UI1-owned placement. Current local draft
clears on menu close; do not claim durable draft continuity from this
behavior. Future durable draft association is a separate owner contract.

### Scope and next implementation boundary

This is UI2's one-document reconciliation of a superseded interaction
direction. The filter/selection table is a proposal for subsequent
review, not a new wire schema, roster source, permission system or
approved connected implementation. Reuse existing UI2 projection and
history components where their actual relationship fits; do not widen
public fixtures into protected sources. UI1 owns native geometry,
accessibility and installed host; Runtime owns binding and lifecycle;
Mind owns Leaves/provenance; Spirit owns disclosure; Heart owns
resource evidence. Review actual S4-U1 source and existing disposable
CI at handoff. No code, test, workflow, protected data, host execution
or merge in this document change.


## S5 // Group conversation participation control: operator example

Source: operator clarification recorded in Hospital #2161 #7215453268,
followed by this exact user-selected example. **Design contract and
non-executable fixture only.** The four names and preferences below are
illustrative configuration, not real members, default operating policy,
enrollment, authority or tool grant. No connected group-chat producer
or durable participant registry currently exists.

### Two independent participation policy scopes

A room's mode defines a maximum allowed interaction envelope. The
individual member's mode and suggestion preference further restrict
its behavior inside that room. Being included, visible, observing or
permitted to speak does not require an answer on every turn. Neither
mode changes tool grants, information access, original assignment,
send recipient authorization or resource admission. Cross-Tree
participants must independently qualify audience and disclosure.

Example, within a collaborative room:

| Example member | Individual speaking mode | May volunteer proposals | Execution authorized? |
| --- | --- | --- | --- |
| Maple | collaborative | yes | no, not by these settings |
| Cedar | observe | no | no, not by these settings |
| DOC 1 | directed | yes | no, not by these settings |
| DOC 2 | directed | no | no, not by these settings |

**Collaborative Maple:** may participate in bounded relevant discussion,
but is not compelled to speak for every message. Suggestion enabled
permits only a proposal when room/user bounds allow it. **Observing
Cedar:** receives only independently authorized shared messages and
does not proactively answer or propose. Even an explicit address to
Cedar requires a deliberate mode/room allowance; otherwise keep silent
or present a neutral inability to route rather than silently overriding
the observer setting. **Directed DOC 1:** normally speaks upon deliberate
address. Proposal volunteering permits a bounded, non-executing
suggestion when the room policy separately permits proactive input;
it does not make an ordinary mention a request. **Directed DOC 2:**
speaks only when deliberately addressed or separately assigned a
covered report; volunteering is disabled. Work execution and reporting
authorization are independent of the speaking mode, so silent workers
may have ongoing explicitly authorized assignments.

### Distinct event and intent semantics

| User/participant event | Routing and state result |
| --- | --- |
| "Maybe DOC 1 should build X" | Discussed entity only; no address, task, approval or tool call |
| "I propose we get DOC 1 to do X" | Proposal about DOC 1, not DOC 1 accepting an assignment |
| "@DOC 1, what would X require?" | Addressed question; answer/proposal only within current bounds |
| Quoted, negated or historical "@DOC 2, implement X" | Literal content, not an actionable directive |
| DOC 1 says "DOC 2 should build X" | Participant recommendation, not user approval or delegation |
| User accepts exact design revision | Record design acceptance with its scope; not necessarily authority to implement |
| User has already authorized implementation and delegation for an exact bounded scope, and DOC 1 validly hands DOC 2 that revision | DOC 2 verifies independent source/current grant, own role/permissions and original assignment/effect, then may perform covered work without repeated user prompt |
| Scope revision, lost original custody or unverified handoff | HOLD the affected effect, not an inferred new grant |
| DOC 2 completes a covered change | Post actual result/receipt/artifact to authorized room audience; never report success merely from accepting a task |

Address, mention, quoted command, suggestion, explicit task assignment,
verified existing authorization and effect execution are separate
events. A free-text @ token alone is not a reliable intent classifier.
Direct participant addressing by UI selection is an explicit routing
choice for a reply, not a file-write grant or implicit transfer of
shared chat authorship. In a group room, messages may have multiple
authorized readers and independently authored replies; the earlier
"one prospective writer per conversation" recommendation applies, at
most, to controlled conflicting effect assignment and must **not**
enforce one allowed speaker or one participant for the room. Runtime
must establish durable multi-author ordering and per-effect identity.

### Future UI acceptance criteria, not executable policy

- Show separately the room's mode, each member's participation mode,
  proposal-volunteering preference, intended addressees and current
  task/effect owner, where each field is independently authorized.
- No all-participants auto-response or tool dispatch from a collaborative
  room; idle/observing/directed members may remain silent indefinitely.
  Prevent participant-to-participant response loops with owner-specified
  turn/budget bounds, explicit stop/interrupt, and per-recipient
  currentness. Exact schedules and budgets are not selected here.
- A mode or suggestion toggle cannot create consent, make sensitive
  history public, activate a dormant worker or dispatch an assignment.
  Permission loss withdraws affected presentation and routing without
  erasing underlying history or settling in-flight original effects.
- A covered design handoff need not request the **same** approval
  repeatedly. The recipient still independently verifies original
  operator grant, exact approved revision, delegability, role/file
  ownership and currentness. The sender's assertion alone cannot grant
  implementation permission.
- Distinguish proposed, user-approved design, assigned, in-progress,
  completed-original-effect and finally accepted-by-user statuses;
  no single "agreed" utterance must silently advance all states.
- A room may contain different Trees and Clones, but membership,
  readable shared messages, attachments, underlying private memories
  and tool capabilities are independently scoped. No broadcast of
  every participant's private context merely because they share a room.
- Changing mode or recipient cannot redirect an already prepared
  stale outbound send or old mutation. Preserve exact original effect
  identity through lost acknowledgements, scope withdrawal and restart.
- These four example names and modes are a **test/example table**, not
  the user's live chat configuration, universal default or proof of
  their actual worker identities.

Runtime owns authenticated author/order, task handoff and effect
lifecycle; Spirit/Connections own audience, permission and revocation;
Mind owns exact versioned approval/knowledge context; Heart owns
resource/turn accounting; UI1 owns installed host; UI2 owns semantic
controls and selection. A qualifying actual owner projection and
independent review must precede implementation. Native/protected/
production HOLD. No new store, issuer, source, API, schema, model
execution, tool call or installed UI in this document.
