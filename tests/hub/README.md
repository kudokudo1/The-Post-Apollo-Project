# ApolloHubW // Preview and acceptance entry point

**Updated October 22, 2026.** This page replaces the pre-integration notes that incorrectly said `shell.qml` still mounted the old Calendar dock and most Hub tiles were placeholders.

## Current repository state

`shell.qml` now mounts one `ApolloHubLiveBridge` and the ApolloHub dock/window. The original Calendar-style dock was replaced. The original 10 module IDs have dedicated UI presentations or active local displays:

- Dashboard → Overview: Time, To-do, Calendar, Weather, Notes, Uptime.
- Console → Quick: Apps, CPU++, Network.
- Media → Player: Media and Time.

The layout is user-configurable, so actual placement may differ. The source contracts for all ten modules exist on GitHub. **That does not mean every module has been accepted on the running desktop.** See [B11 Integration Acceptance](../../services/hub/INTEGRATION_ACCEPTANCE.md) for the current verification matrix and safe runtime checks.

## Live shell versus standalone preview

The **real Hub** is launched from the existing ApolloHub dock on your synced, running Quickshell. It receives the shared services and the native QML singletons.

The repo-root standalone preview remains available:

```sh
cd ~/.config/quickshell
qs -p apollo_hub_click_preview.qml
```

The preview creates a **separate Quickshell process**, not a restart of the live bar, and uses the repo-root file so imports resolve correctly. It still uses `ApolloHubW` and its layout/UI but **does not inject the live bridge from `shell.qml`**. Therefore Calendar, Weather, Network, CPU++, Media, Apps, and Uptime may report disconnected/unavailable in preview even when the live Hub works. Do not use the preview as proof of their runtime failure.

The old `tests/hub/apollo_hub_preview.qml` is retained for history and is not a supported top-level `-p` entry point, because its directory changes import resolution.

**Data caution:** The preview can still load the Hub's standalone singleton stores. Do not assume a preview has an isolated data directory or that pressing To-do/Notes Save is read-only. Avoid creating, editing or deleting personal data merely to test appearance. Both launching a preview process and restarting Quickshell are local runtime operations and require operator approval if an assistant performs them.

## Manual keyboard smoke checks (live or preview)

With the Hub open, Tab/Shift+Tab cycles main modes, Shift+Left/Right cycles top submodes when present, ordinary arrows navigate tiles, and Escape closes the Hub. Enter is not a generic launch shortcut: it only cycles the selected module when in **EDIT** mode.

When typing in a To-do or Notes field or the mode-name editor, navigation shortcuts must not consume text/cursor keys. Repositioning/switching modules in EDIT should not modify personal task or note data.

## Source tests

- `python3 tests/hub/test_apollo_hub_foundation.py` validates shared Hub UI contracts for all ten presentations.
- `.github/workflows/apollo-hub-live-bridge.yml` validates the shared Weather/CPU++/Network/Media/Uptime/Apps backends.
- Dedicated workflows `apollo-hub-todo.yml`, `apollo-hub-notes.yml`, `apollo-hub-calendar.yml`, `apollo-hub-time.yml` cover the other local domain contracts.

CI is **source-level evidence**. Actual Fedora/Quickshell loading, state updates, write/restart persistence, and interaction/focus behavior remain separate desktop acceptance criteria. Do not infer local sync from GitHub `main`.
