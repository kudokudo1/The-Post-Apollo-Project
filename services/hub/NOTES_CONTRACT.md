# 🏥💜 ApolloHubW // B8 Notes backend contract

**Status:** B8 source implemented on GitHub `main`. Automated CI and on-device storage verification are distinct from UI implementation and operator acceptance.

**Scope and ownership:** This is a *small personal notebook inside ApolloHub*, not **The Study**, Forest, a cross-project note bank, a Hospital record, or an existing To-do. Do not migrate or conflate any of those data sources. The B8 backend does not touch `shell.qml`, app widgets, `ApolloHubStore.layoutJson`, To-do data, or other worker-owned UI.

## Implementation and persistence

- `services/hub/ApolloHubNotesPolicy.js`: pure v1 schema, validation, stable IDs, optimistic revision checks, and compact display projections.
- `services/hub/ApolloHubNotesStore.qml`: the **one** native Quickshell singleton, registered by `services/hub/qmldir`, which loads and saves the user's notes.
- `Quickshell.dataDir + "/apollo-hub-notes-v1.json"`: user-local JSON file, separate from `apollo-hub-todo-v1.json` and `apollo-hub-layout.json`.
- `FileView` uses `atomicWrites: true`, `blockWrites: false`, `watchChanges: false`. The file is not created until the user deliberately creates a note.

V1 bounds: 100 notes, 120-character title, 8,192-character plain-text body including newlines, and a one-megabyte source file limit. Stable IDs increment monotonically (`n1`, `n2`, etc.) even after deletion.

An example on-disk record (illustration, **not** preloaded):

```json
{
  "version": 1,
  "nextId": 2,
  "notes": [
    {
      "id": "n1",
      "title": "Example",
      "body": "A personal quick note.",
      "revision": 1,
      "createdAtMs": 1000000,
      "updatedAtMs": 1000000
    }
  ]
}
```

## UI integration contract

`import qs.services.hub` exposes the singleton `ApolloHubNotesStore`.

For the Notes mini-card, read `ApolloHubNotesStore.snapshot`. It contains:
- `state`: `loading`, `empty`, `ready`, `saving`, `error`, or `unsupported`.
- `writable`: true only when state is `ready` or `empty`.
- `error`: an error code when unable to load, persist, or understand the file.
- `total`: number of confirmed notes (zero on unavailable/unsupported sources).
- `items`: most-recently-edited first, each `{id,title,preview,revision,updatedAtMs}`. Preview is at most 160 flattened plain-text characters.

To open an editor for an existing note, call **`ApolloHubNotesStore.getNote(id)`** while storage is ready. It returns a detached `{id,title,body,revision,updatedAtMs}` or `null` when unavailable. The UI maintains its own temporary text fields; typing must **not** change the file.

Supported explicit actions:

```qml
ApolloHubNotesStore.createNote(title, body)
ApolloHubNotesStore.saveNote(id, expectedRevision, title, body)
ApolloHubNotesStore.deleteNote(id, expectedRevision, true)
ApolloHubNotesStore.reloadFromDisk()
```

**Each mutation returns `true` only when an asynchronous save has started.** The UI must distinguish `saving` from saved. Successful `onSaved` advances the confirmed document to `ready`/`empty`; `onSaveFailed` sets `error` and never presents unsaved text as committed. The mini-card should disable editing during `saving`, and the editor should retain unsaved text if saving fails.

A note's `revision` increases after a completed edit. `saveNote()` and `deleteNote()` require the currently loaded revision. A stale edit or stale deletion cannot replace more recent content. Deletion additionally requires explicit UI confirmation, not merely clicking a row. Display note text using `Text.PlainText`, not rich-text interpretation of user-provided content.

## Corruption and access safety

A **missing file** means an initially empty notebook, without automatically writing a replacement. Malformed JSON, duplicate IDs, invalid timestamps/revisions, or unsupported version fail closed. **Do not silently reset or migrate corrupted notes.** A failed save preserves the previous confirmed document and locks writes until deliberate user recovery/reload.

B8 is intentionally **single-writer** and does not pretend to support concurrent external edits, cloud storage, cross-device sync, autosave, note version history, content search, Markdown rendering, AI summaries, notifications, or calendar integration. `atomicWrites` protects a single file replacement; it is not a transactional database or a backup strategy.

## Verification and rollout

- `tests/hub/test_apollo_hub_notes_policy.cjs` executes production policy on create/edit/delete, revision conflicts, multiline text, malformed files, capacity, and display privacy.
- `tests/hub/test_apollo_hub_notes_store.py` guards read-only initialization, one file writer, absence of autosave/background actions, and sibling service boundaries.
- `.github/workflows/apollo-hub-notes.yml` runs both in CI.

**Desktop acceptance pending:** Confirm first-load missing-file behavior, deliberate create/edit/save, deletion confirmation, revisions after reopening, corrupted-file protection, and notes surviving a Quickshell restart. Source-level checks alone do not prove that the installed Quickshell version writes FileView atomic files correctly.

**No local machine files, running services, or live Quickshell process were changed by the GitHub implementation.**
