# MACHINE // SAVE and CUSTOMIZE fail on real desktop: isolated Python import boundary

**Patient** The-Post-Apollo-Project  
**Room** TimeW MACHINE / desktop recovery  
**Staff** DOC external, read-only local system  
**Source** GitHub main after merged PR #1649  
**Observed** Screenshot dated November 9, 2026: TimeW loads; SAVE reports `SAVE OR CAPTURE UNAVAILABLE`; CUSTOMIZE reports `NO CURRENT CAPTURE`. No successful saved checkpoint was established by screenshots.

## Diagnosis

The real widget executes:

`python3 -B -I <quickshell>/services/time/MachineSaveBridgeV2.py inspect`

or `save`. Python isolated mode (`-I`) does **not** prepend the
script directory to `sys.path`. The newly merged bridge imported its
sibling `MachineCaptureSaveV2` before setting the path and could exit with
`ModuleNotFoundError`, without emitting the JSON response the widget
expects. Existing synthetic tests imported the bridge as a module after
inserting a test search path, accidentally hiding the launcher defect.

This repair adds the script's own resolved service directory explicitly
before its sibling imports, matching the already established pattern in
`MachineSwayRead.py`. It does not use user-provided paths or environment
variables as import roots.

## Verification

- A new test launches the actual `python3 -B -I` bridge as an **external**
  process in an isolated temporary XDG directory. It requests an invalid
  action and asserts it reaches the bridge's bounded action rejection,
  rather than failing to import. No Sway socket or database write is used.
- The existing real two-output **disposable stock Sway** CI test now
  launches both the `inspect` and `save` CLI as standalone isolated
  processes with a socket explicitly pinned to the child compositor.
  A private throwaway SQLite database is used, with the old v1/v2 atomic
  writer and full geometry roundtrip.
- The bridge maps errors to bounded categories, not raw Sway JSON, private
  window titles, SQL internals, sockets, or filesystem paths.

## Safety and acceptance

No edits, reloads or writes on the operator's running Fedora desktop.
No Brave session inspection, exact RESTORE activation, schema migration or
old-checkpoint rewrite. Any local patch/restart requires separate approval.

**Native stock Sway CI success cannot prove Fedora/SwayPX capture compatibility**.
After applying this change, verify both read-only CUSTOMIZE and normal
SAVE on the real desktop, then load the created checkpoint from STORED.
If the new bridge reports `SWAY GEOMETRY UNSUPPORTED`, evaluate a
read-only, redacted SwayPX fixture before changing parsers.

## Next

1. Exact-head CI.
2. Operator approved deploy + real Quickshell verification.
3. Only after a successful saved/reloaded v2 checkpoint, continue
   checkpoint notes/restorable MARK, Brave sessions, and exact restoring.
