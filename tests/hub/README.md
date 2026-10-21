# ApolloHubW // Isolated preview and keyboard smoke test

**Status:** ApolloHubW and its Calendar-styled dock are on GitHub main, but
`shell.qml` still mounts the original Calendar. Nothing activates the new
center dock in the running taskbar without a separate shell integration.

The original `tests/hub/apollo_hub_preview.qml` is kept as source history but
is **not** a valid top-level `-p` entry point: Quickshell roots the
configuration at the chosen file's directory, making parent imports unresolved.

To test the Hub *without touching your live Quickshell instance*, use the
repo-root standalone click-and-keyboard harness:

```sh
cd ~/.config/quickshell
qs -p apollo_hub_click_preview.qml
```

That starts a separate 113x50 dock and a Hub popup. Click the white-arrow /
orange-calendar / white-stars button. The button glow should be magenta.
In the Hub: Tab / Shift+Tab cycles main modes, Shift+Left/Right cycles an
available top sub-mode, ordinary arrows select tiles (orange selection outline),
and Escape closes the Hub. No bottom sub-mode is currently present, so no
Ctrl+Left/Right shortcut is registered. Enter only cycles a selected module
while in EDIT mode; preview cards do **not** activate real widget services.

Click the MODE text field in EDIT mode and type using arrow keys, Tab and Enter
normally. Closing the editor should restore the Hub's local navigation focus.

Only time and date are live; Weather, CPU++, Media and other cards are
placeholders. Layout/configuration persistence is implemented but restart
round-trip and Sway keyboard acquisition must be accepted on-device.

Safety: the preview is a separate process, not a new live-bar integration.
Do not restart or replace the main Quickshell instance as part of this test.
The shared shell and Koinoikos focus broker require separate integration
verification; shortcuts are window-local until then.
