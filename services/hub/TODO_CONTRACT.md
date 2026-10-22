# 🏥💜 ApolloHubW // B7 To-do backend contract

**Status:** Source committed to GitHub `main`; on-device storage round-trip and To-do mini-widget UI acceptance pending.

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
