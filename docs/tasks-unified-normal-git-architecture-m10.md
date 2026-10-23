# TASKS // M10a Proposed Unified NORMAL/GIT Architecture

**Owner:** Proxy 1 (external ChatGPT development assignment; not live Hospital-registered)
**Patient:** `kudokudo1/The-Post-Apollo-Project`
**Status:** Draft architecture and executable read-only compatibility contract.
**Coordination:** Proxy 2 owns PLANNER interface and UI work. M10a does not touch
`TasksW.qml`, `shell.qml`, `TaskPlannerPane.qml`, or task storage.

## User contract

1. One PROJECTS workspace, clearly divided into **NORMAL** and **GIT** families.
   The project editor and navigation conventions are shared.
2. NORMAL projects have no remote dependency. They support richer, local-only
   fields and arbitrary non-software project domains.
3. GIT projects represent selected GitHub ProjectV2 projects. The user edits
   the Post-Apollo local working copy through the same editor, both online and
   offline. GitHub updates are queued, sent and **verified**, never assumed.
4. SYNC is an optional power/control surface for connection, queue policy,
   field mappings, conflicts and recovery. Everyday edits stay in PROJECTS.
5. Extra local fields on GIT projects must **not** be silently discarded when
   they cannot map to GitHub. PULL must not erase such fields.
6. Linking/unlinking projects must be explicit and reversible without
   automatically deleting local tasks or remote GitHub content.

## Verified present baseline

- `ApolloHubTodoPolicy.js` validates versions 1/2/3 and normalizes them into
  v3; projects use local `pN`, tasks `tN`, and a task has `projectId`
  pointing to at most one existing local project.
- `ApolloHubTodoStore.qml` is the single persisted writer, using one
  `FileView` with `atomicWrites:true`. It reports `saving` and only
  acknowledges success from `onSaved`. Its path is the existing
  `apollo-hub-todo-v1.json`.
- The current v3 clone drops unknown persisted fields. Attaching new metadata
  to a v3 document without changing the validator and writer would lose data.
- `GitHubProjectsService.qml` lives in GitW, owns GitHub CLI operations and
  can read ProjectV2 lists, metadata, fields and items. It already has remote
  mutation operations, but **TASKS has no approved write adapter**.
- Proxy 2 PLANNER M1 reads `todoSnapshot.items` and `dueDate` without writing.
  Any future model must continue providing the same read-only task projection.

## Logical data model (proposed, not yet persisted)

Common Project:
- `id`: stable local identifier, preserved across link/unlink
- `name`: user-facing title
- `family`: `normal` or `git` (explicit, NEVER inferred from title)
- `remote`: `null` for NORMAL; verified GitHub Project identity for GIT
- `fieldDefinitions`, `localExtensions`, presentation settings and timestamps
  live in a versioned model with user-controllable capacity limits

Common Task:
- stable local `id`, project relationship, title, description, completion,
  priority, due date and future scheduling metadata
- namespace-scoped custom field values and relationships
- `remote` item identity for linked items, maintained separately from local ID
- preserves existing task rendering with a compatibility snapshot for TODAY,
  Hub To-do and PLANNER

GitHub identity requires ALL of:
- provider `github`, authenticated owner login, verified **ProjectV2 node ID**,
  and project number (display/reference only)
- for each linked task, verified ProjectV2 **item ID**, content kind
  (ISSUE/PULL_REQUEST/DRAFT_ISSUE as applicable) and verified content node ID
  when that kind provides one
- field-ID and option-ID mappings tied to their actual parent ProjectV2 ID
- an identity verification record produced by the Git-owned read adapter

A syntactically correct ID is not proof that GitHub returned it. Repository
names, matching titles, or project number alone must never cause auto-linking.

## Durable offline operation model (proposed)

Model writes, remote effects, and confirmation are separate:
1. User edit -> local commit first; UI only claims "locally saved" after a
   durable local acknowledgement.
2. In the *same durable transaction*, record a pending operation with stable
   operation ID, target identity, field/intent, previous confirmed baseline,
   and dependent-operation ordering.
3. Online: perform fresh remote read, compare against the baseline, then
   apply only safe and authorized changes. Remote write transport stays
   owned by the existing Git service or reviewed adapter.
4. On remote uncertainty: mark operation `UNCERTAIN`, re-fetch remote state,
   and reconcile before retrying. Never blind-retry non-idempotent creates.
5. After confirmed remote outcome, advance the baseline and mark journal
   `ACKNOWLEDGED`. Conflicts block only affected fields when safe.
6. When offline, retain queue and local model after restart. Recover from
   partial transfers without dropping local or remote versions.

Illustrative states: `LOCAL_SAVED`, `PENDING`, `SENDING`,
`UNCERTAIN`, `ACKNOWLEDGED`, `CONFLICT`, `BLOCKED`.
No current code implements this state machine. Auto-sync remains opt-in.

**Storage choice pending evaluation:** the current v3 atomic JSON writer cannot
transactionally coordinate independently persisted model, identity map, and
queue files. Candidate strategies are a single atomic versioned envelope or
a transactional SQLite-backed store. Select only after crash/upgrade testing,
realistic workload limits, and Quickshell integration cost are measured.
Do not claim crash safety from `FileView.atomicWrites` for multiple files.

## Conversion and deletion policy

- Existing v3 projects preview as NORMAL; their `pN` IDs stay stable.
  Unassigned tasks remain unassigned.
- NORMAL -> GIT is an explicit link operation after verified ProjectV2
  identity and field-mapping review. No automatic creation by matching titles.
- GIT -> NORMAL unlinks **the local relationship only** after pending-edit
  disposition. It never silently deletes GitHub data.
- NORMAL deletion does not touch GitHub. GIT deletion/archive/unlink are
  separate explicit actions with previews and independent confirmations.
- Unknown future on-disk versions, invalid documents, and incomplete journal
  recovery all fail closed rather than overwriting existing data.

## Migration and rollback gates (before any real schema write)

- Freeze and independently back up original v3 bytes; test file hash and
  restoration before first migration.
- Parse and validate v3; produce dry-run counts and stable identity mapping;
  test old v1/v2 upgrades and adversarial corrupt/unsupported input.
- Run copy-on-write migration into a new versioned candidate; verify all
  tasks, project IDs, dates, priorities, descriptions, and assignments.
- Ensure old Hub, TODAY, and PLANNER readers continue to receive compatible
  projections until the new consumers are accepted.
- Verify restart, interrupted save, permission denial, disk-full,
  malformed/unknown version, and rollback before enabling writes.
- Maintain a durable migration marker to prevent partial/repeated upgrades.
- Operator approves actual on-disk migration separately. No desktop
  activation or data rewrites occur in M10a.

## M10a source deliverable and limits

`services/projects/UnifiedProjectContract.js` is a **pure, read-only**
prototype that checks proposed project-family/remote-reference *shape*
and projects current v3 snapshots as NORMAL, with no inferred GitHub links.
It is **not** a v4 serializer, migration engine, or new data writer.

Acceptance: isolated Node tests verify identity rules, v3 compatibility,
unchanged source objects, malformed storage fail-closed, and no network,
process, or file access. CI reports only source-level tests.

## Responsibility and upcoming contracts

- **Proxy 1:** project model, read bridge specification, migration and
  durable offline journal, syncing/conflict engine.
- **Proxy 2:** PLANNER, user-facing layout and view-specific QML files;
  consumes read-only compatibility snapshots.
- **Shared integration:** `TasksW.qml`, `shell.qml`, GitW service public
  interfaces, ApolloHubTodoStore/QML adapters, workflow cross-edits only
  after coordination. M10a deliberately does not modify these.
- **Operator:** authorizes merges, on-device tests/changes, data migrations,
  remote write enablement and actual Hospital registration.

## Decisions still awaiting explicit design acceptance

- Durable storage mechanism and maximum supported data sizes.
- Whether tasks can belong to multiple projects (v3 supports one);
  relationship schema must not assume an unapproved answer.
- Global versus per-project custom field definitions and visibility.
- Default auto-sync policy and whether content edits are field- or document-
  granular for unsupported GitHub item types.
- Remote deletion/archive semantics and exact conflict UI.

This document is a draft implementation contract for review, not a production
activation, migration permission, or final answer to unresolved decisions.
