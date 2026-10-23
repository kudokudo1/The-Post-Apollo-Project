# 🏥💜 ApolloHubW // B7 To-do backend contract

**Status:** B7 v1 is the historical baseline; TASKS M4 v2 is merged. M6 v3 local grouping is proposed in a separate draft PR; live acceptance remains pending.

**Ownership boundary:** This is a tiny personal checklist **inside ApolloHub**, not a Hospital Room/Assignment/Worker/Session, AppControl process list, Koinoikos task, calendar service, or Notes/The Study. It changes none of those systems. `shell.qml` and Hub UI are unmodified by B7. Features beyond this first local checklist require separate scope and operator decisions.

## Implementation

- `services/hub/ApolloHubTodoPolicy.js`: pure, tested v1 document schema and intentional state transitions.
- `services/hub/ApolloHubTodoStore.qml`: **one Quickshell singleton**, imported through `qs.services.hub`, that owns the private on-disk checklist.
- `services/hub/qmldir`: registers `singleton ApolloHubTodoStore 1.0 ApolloHubTodoStore.qml`.
- **Path:** `Quickshell.dataDir + "/apollo-hub-todo-v1.json"`. Separate from `ApolloHubStore.layoutJson` and all AppControl/Hospital records.

There is no subprocess, network request, background AI, notification, timer, or automatic task creation.

The v1 file is JSON:
```json
{
  "version": 1,
  "nextId": 2,
  "tasks": [
    {
      "id": "t1",
      "title": "Example task",
      "done": false,
      "createdAtMs": 1000000,
      "updatedAtMs": 1000000
    }
  ]
}
```
The example is schema illustration only, not preloaded content.

Maximum 200 tasks and 160 characters/title. Numeric `nextId` makes stable IDs monotonically increasing, including after a task is deleted. Titles are plain text, not executable commands or HTML. Completed items are retained until explicitly removed. No due dates, recurrence, priority, cross-device sync, or associations are asserted by v1.

## UI consumer contract

`import qs.services.hub` exposes `ApolloHubTodoStore`; the UI can read:

```qml
readonly property var todoSnapshot: ApolloHubTodoStore.snapshot
```

`todoSnapshot` is a shallow, read-only display projection:
- `state`: `loading`, `empty`, `ready`, `saving`, `error`, or `unsupported`.
- `writable`: true only in `ready` / `empty`. **Never report a pending write as saved.**
- `error`: empty normally, reason code on error/unsupported.
- `total`, `remaining`, `completed`, `items` (unfinished first, then completed, preserving source order within each).
- `items[]`: `{id, title, done}` only; no raw file object, timestamps, or mutation handles.

On **direct, intentional UI events only**:
- `ApolloHubTodoStore.addTask(title)`: trim/create a task, fail on empty/malformed title or full list.
- `ApolloHubTodoStore.setTaskDone(id, bool)`: mark incomplete/complete; accepts only booleans.
- `ApolloHubTodoStore.renameTask(id, title)`: rename while retaining the stable ID.
- `ApolloHubTodoStore.removeTask(id, true)`: delete **only after UI confirmation**; omission/false must do nothing.
- `ApolloHubTodoStore.reloadFromDisk()`: explicit recovery/reload when not saving.

Each operation returns `true` when an *asynchronous write is initiated*, **not** proof of persistence. The UI must observe `snapshot.state` changing from `saving` to `ready` or `empty`, or to `error`.

## Storage safety and failure semantics

`FileView` is used with `atomicWrites: true`, `blockWrites: false` and a single pending document. Only `onSaved` publishes the pending document into confirmed state. `onSaveFailed` preserves the last confirmed state, locks writes, and reports `FILE_SAVE_FAILED`. Further writes require deliberate reload and reconciliation.

A genuinely missing file produces `empty`, but **does not create a file** until a real user command. Malformed JSON, invalid records, ID conflicts, or future/unsupported schema versions fail closed. They are **never replaced with an empty file**, and no automatic migration is attempted.

`watchChanges: false` is intentional v1 single-writer behavior, avoiding external reload races against a pending async write. The UI should provide explicit reload/recovery, and must not imply multi-process/concurrent editing or external synchronization. If file permissions or directories prevent writes, the store displays a save failure rather than claiming success.

**Caution:** This is a small task-data file, not a robust transactional database. An independent runtime acceptance must verify missing-file boot, create/edit/complete/delete, data survival across Quickshell restart, deliberate reload, and failure recovery.

## Testing

`tests/hub/test_apollo_hub_todo_policy.cjs` executes the real domain policy, including:
- create / rename / complete / delete with confirmation and stable IDs
- capacity/title limits, malformed JSON, duplicated records, version mismatch
- failed/no-op operations, display privacy and write eligibility

`tests/hub/test_apollo_hub_todo_store.py` statically guards the one-store QML/persistence contract and absence of background/machine actions.

The independent workflow `.github/workflows/apollo-hub-todo.yml` runs both in CI, with repository grammar validation remaining separate.

## Next

1. UI owner implements the To-do mini-widget against the **existing singleton**; no second store, no new shell instance.
2. Verify the actual Quickshell FileView persistence round trip on the operator's desktop before treating user tasks as durable.
3. Revisit richer features (due dates, priority, calendar links, notifications, external sync, revisions/undo) only after an explicit design decision and separate work authorization.

**No local files or running Quickshell processes are altered by this GitHub source checkpoint.**

## TASKS M4 // v2 personal task fields (2026-10-22 proposal)

**Current change boundary:** The M4 branch extends the shared personal checklist, not
Hospital Assignments, AppControl process tasks, Calendar, GitHub Projects or Obsidian.
B7's one-writer/singleton model and explicit save lifecycle remain in force.
This section documents the proposed v2 source contract, not live deployment.

- The established path `Quickshell.dataDir + "/apollo-hub-todo-v1.json"`
  is **not renamed or automatically rewritten**; the path historically carries
  a v1 suffix. An existing v1 document is parsed and **upcast in memory** to
  v2 with defaults `priority:"none"`, `description:""`, `dueDate:null`.
- The first **explicit task mutation** writes a full v2 document to that same
  file using the existing atomic writer. Opening TASKS or Apollo Hub alone
  never writes. An older binary/policy limited to version 1 cannot read v2
  after the upgrade; **do not downgrade without restoring a verified backup**.
- Each v2 task keeps `id`, `title`, `done`, `createdAtMs`, `updatedAtMs`
  and adds `priority` (`none|low|medium|high|urgent`),
  `description` (plain text, ≤2000 characters), and `dueDate`
  (`YYYY-MM-DD` real Gregorian date or `null`).
- Existing Hub ADD/EDIT/complete/delete continues to preserve all new fields.
  The TASKS detail pane edits the three new fields together as one validated
  store operation, with a separate draft, SAVE/DISCARD, pending/error feedback,
  and explicit selection by tapping a task title.
- Only known fields pass the parser; invalid values, duplicate IDs and unknown
  format versions fail closed. Unknown untrusted metadata is discarded rather
  than becoming arbitrary persisted executable/user state.
- The `snapshot.items` projection now includes these three task details,
  but still excludes internal timestamps and storage/sequence controls.
  It is a display snapshot, not direct access to the mutable disk document.
- Max 200 tasks, 160-character titles. JSON size bound increases to 1 MiB
  to support descriptions. No automatic synchronization, filesystem watching,
  remote calls, notifications, task scheduling or conflict merging.
- GitHub Projects custom fields, identifiers, assignees, iterations and
  Obsidian/Markdown/TXT/Git adapters are **not** part of M4. These require
  later mapping, ID and version/conflict decisions.

**Verification required before production:** CI on real policy; v1 reload;
create/edit/complete/reopen/delete; persistence through Quickshell restart;
correct leap day and invalid date handling; disk save failure preserving draft;
Hub and TASKS simultaneous editing; no typing captured by unrelated widgets.
Live operator acceptance is not implied by source tests.

## TASKS M6 // Local Projects v3 (2026-10-22)

**Status:** Draft implementation; requires CI and operator runtime acceptance.  
**Scope:** local grouping only. This does NOT yet create, query, or edit GitHub Projects.

- One singleton, one `FileView`, one existing storage path (`apollo-hub-todo-v1.json`). No other file is automatically created and no network synchronization occurs.
- v1/v2 on-disk documents are **read as v3 in memory**, keeping task IDs, timestamps, status, priority, descriptions and due dates. No automatic rewrite simply from opening TASKS/PROJECTS.
- The next explicit local mutation writes **v3** using the existing guarded atomic writer. **Older v1/v2-only policies cannot read a v3 document.** Preserve a verified backup before downgrading.
- v3 documents add `nextProjectId`, `projects[]`, and a nullable `projectId` on each task. Project entries have stable `pN` IDs, name, creation and update timestamps. Task IDs remain independently stable `tN`.
- Capacity is **30 projects**, with **1–64 character names**. Names are unique ignoring case. A task can belong to at most one local project in this initial version; changing assignment is an explicit user click.
- The store validates all project references, rejects unknown IDs, duplicated IDs/names and sequence rewind, and strips unrecognized fields when parsing. It continues to report `saving` until the file's `onSaved` event, never when writing merely begins.
- The read-only UI snapshot now includes `projects:[{id,name,total,remaining,completed}]` and each task's `projectId`. It does **not** expose project timestamps, internal sequences, or the writable raw document.
- PROJECTS mode provides **Create project**, project selection, assignment/clear of tasks, and OPEN navigation back into the existing TASKS details editor. **Rename/delete projects, subtasks, multiple project memberships, GitHub Projects, and sync** are separate milestones.
- M5 TODAY continues to use the unchanged task due-date snapshot. Apollo Hub task editing preserves project assignment on rename/complete/delete, all through the existing store.
- On-device acceptance needed: v2→v3 read/restart, actual creation, assignment/reassignment, clear, preservation after restart, no data loss on disk failure, and cross-view consistency with Apollo Hub. CI alone is not runtime approval.

