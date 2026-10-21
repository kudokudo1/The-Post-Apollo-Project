# ApolloHubW // Foundation preview

**Status:** first-stage GitHub-only development scaffold. This is not installed
in the live Post-Apollo bar; `shell.qml` deliberately remains unchanged.

After a local sync is separately authorized and the operator has checked the
working tree, a **separate Quickshell preview process** can be started with:

```sh
quickshell -p tests/hub/apollo_hub_preview.qml
```

This proposed preview command has **not yet been runtime-verified** on the
operator's Fedora/Quickshell installation. Do not restart or replace the live
shell to test it.

In the preview, try Dashboard/Console/Media, press EDIT, add a mode/group/tile,
rename a mode, and use the left/right arrows to swap tile positions. Tile
positions and menu choices are stored in Quickshell's data directory as
`apollo-hub-layout.json` and should survive restarting the preview process.
Only local time and date are live; all other cards intentionally say preview
until Post-Apollo data-source adapters are connected.

The first pass supports two preset tile widths, a 6-mode / 6-group / 8-tile
safety cap, and cycle-through tool selection. It does **not** support arbitrary
drag/drop, resize handles, removal of modes/tiles, custom icon picking, mature
cross-widget adapters, or in-Hub expanded views. Those remain future
development work and require operator direction.

Verification boundaries: source assertions plus pure JS layout behavior can
check configuration logic, but do not establish Quickshell loading, rendering,
focus behavior, persistence across real restarts, or final operator acceptance.
