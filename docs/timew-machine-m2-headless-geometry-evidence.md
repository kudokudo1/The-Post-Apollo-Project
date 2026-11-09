# MACHINE // M2 real headless Sway geometry compatibility test

**ROOM:** TimeW MACHINE / desktop recovery  
**PATIENT:** The-Post-Apollo-Project  
**SOURCE:** `tests/timew/test_machine_geometry_headless_sway.py`  
**STATE:** CI acceptance candidate; no local operator-machine trial  
**DEPENDENCY:** M2 geometry-v2 model merged from PR #1621

## Why

The previous M2 geometry contract passed synthetic fixtures, but no real Sway
`get_outputs`, `get_workspaces` and `get_tree` frame had exercised its
nested layout and exact rectangle parser. A practical SAVE needs confidence
that a real compositor supplies the expected geometry and tiling shape before
we add a persistent checkpoint writer or a new UI.

## What runs

The CI job installs stock Ubuntu Sway and foot, creates a new private
temporary XDG runtime, strips all inherited Sway/Wayland/DBus connection
variables, launches software-rendered Sway with TWO headless outputs, and
passes every `swaymsg` read/command through the child's private IPC socket.
The test refuses to run unless both `CI=true` and
`GITHUB_ACTIONS=true`.

Three disposable `foot` windows are launched, two sharing the same app ID
to emulate same-app multiplicity and one floating window. Two workspaces are
placed on independent virtual outputs. One coherent read of output,
workspace and tree data feeds the `MachineGeometryV2` pure projector.

Assertions verify:

1. Both output positions and workspace/output ownership.
2. Two distinct checkpoint-local keys for identical app IDs.
3. Individually measured non-zero window rectangles and different tiled
   positions, rather than app/workspace counts alone.
4. A floating window on the other output.
5. Ordered nested tiling containers and split metadata are accepted.
6. The strict v1 projection from the **same** compositor frame agrees with
   geometry's app/workspace/floating multiset. This is **not** proof of a
   same-window session identity.
7. No transient container IDs, titles or private client fields are emitted.
8. All compositor and child processes are terminated in cleanup; all test
   files live in the temporary CI directory.

The accompanying source contract rejects accidental dependence on normal
user Sway environment variables, a live QML bridge, or model-side
subprocess/network access.

## What this does not certify

- Stock headless Sway is not the user's SwayPX compositor. Native SwayPX
  verification and dual-monitor pixel fidelity are separate gates.
- A geometry **capture** parser is not a compositor **restore** implementation.
  It does not create or reconstruct nested split/floating layout, launch
  Brave, restore browser tabs or persist v2 snapshots.
- Full desktop contents, unsaved forms, app RAM and terminal running programs
  are outside this test's scope. No real Brave profile is inspected.
- Nothing writes to or migrates the operator's existing
  `~/.local/share/post-apollo/machine/machine.db`; current v1 checkpoints
  remain unchanged.
- CI pass should be reported as `HEADLESS STOCK SWAY GEOMETRY PASS`, not
  `PRODUCTION SwayPX RESTORE VERIFIED`.

## Follow-up gate

Once real geometry shape passes, implement an isolated same-frame capture
coordinator and additive, private **v2** checkpoint transaction. Preserve
the established v1 reader and seven existing records. Do not make
`CAPTURE PREVIEW` a mandatory user action; normal SAVE should capture,
validate and persist in one operation after v2 storage is verified.

**Verification status is determined by the exact PR head CI.**
