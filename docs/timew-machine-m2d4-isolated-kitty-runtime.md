# MACHINE M2d4 // isolated real Kitty native-API compatibility smoke test

**Scope approved 2026-10-26:** merge of #812 (already complete) and first
**disposable** Kitty native-read test. This phase does **not** authorize
changing the user's running Kitty sessions, enabling remote control on their
Fedora Silverblue workstation, connecting to a user socket, writing their
machine, or adding a permanent session collector.

## Verified baseline

- PR #812 was merged before this work started; its TimeW and Grammar
  checks passed. Source: `services/time/MachineKittyRead.py`.
- Official Kitty CLI: `kitten @ --to unix:<socket> ls` returns JSON with
  top-level OS windows, nested tabs and Kitty windows. The native response
  may include private titles, command lines, PIDs and environment data.
  Sources: https://sw.kovidgoyal.net/kitty/remote-control/ and
  https://sw.kovidgoyal.net/kitty/rc_protocol/
- `allow_remote_control=socket-only` is not truly a read-only socket:
  *anyone with permission to use that socket may send powerful requests*.
  This is acceptable only in a freshly created, private, disposable CI
  environment. Source: https://sw.kovidgoyal.net/kitty/conf/

## Test environment

`.github/workflows/timew-kitty-isolated.yml` runs on a GitHub-hosted,
short-lived Ubuntu 24.04 runner, installing an Ubuntu-packaged Kitty and
Xvfb. The Python test is disabled outside CI by a required explicit
`MACHINE_KITTY_ISOLATED_CI` variable and `GITHUB_ACTIONS=true`. This
software gate prevents accidental standalone runs, **not** a trust-worthy
security authorization token.

`tests/timew/test_machine_kitty_isolated_runtime.py`:

1. Requires the virtual X display and installed `kitty`/`kitten`.
2. Creates an owner-only temporary directory and isolated `HOME`, XDG
   cache/config/data paths; launches exactly one new Kitty process with
   `--config NONE`, `allow_remote_control=socket-only` and a private
   Unix socket beneath that directory, with restrictive umask.
3. Waits for **that temporary** socket, validates it is a socket with
   current-user ownership and no group/other permissions. No automatic
   discovery of the user's live Kitty instance is permitted.
4. Calls the actual dormant `read_existing_kitty_inventory` function
   once against the CI socket. It validates structural counts and verifies
   sensitive fields never leak into the sanitized projection.
5. Removes the disposable Kitty process group and temporary files, even
   when the test fails. It never prints Kitty's raw JSON.
6. Preserves `input_origin_verified=false` and
   `host_window_binding_verified=false`. A real native inventory is
   still not proof of the SwayFX window association or a restart-stable
   session identity.

## What successful CI means

Only: the app's documented native command and our privacy-stripping parser
worked on the **specific Ubuntu-packaged Kitty version** reported by the
CI run. That is a step beyond the earlier M2d3 injected subprocess test.

It does **not** demonstrate Fedora Kitty compatibility, SwayFX host-window
correlation, persistent Kitty-to-checkpoint identity, profile restore,
arbitrary session reconstruction, actual REVIVE, or historical RESTORE.
A Linux Xvfb test also does not establish Wayland/macOS/Windows support.

## Next gates

- Review the successful native output shape without retaining raw private
  data, then compare Kitty versions to the user's installation via a
  *separate authorized* compatibility check.
- Design an authenticated, narrow host-window correlation method. Kitty
  OS-window IDs are ephemeral and compositor `con_id` is ephemeral.
  Do not guess from window names or order.
- Extend the family-based adapter model to supported browsers/editors and
  other terminals. Kitty is one adapter, not the product's scope.
- Present explicit opt-in and rollback for any future local changes.
  Disabling/removing the CI-only test requires no local rollback. Preserve
  all seven existing v1 checkpoints and the REVIVE/RESTORE separation.

## Execution and ownership

No local user files or Quickshell state were accessed. Existing MACHINE
repository source remains unchanged by this PR except new CI test/docs.
No PR merge or production runtime activation without operator approval.
Follow `Meta-Apollo-Logos-Syntagma/AGENTS.md` and current GitHub and
Hospital ownership before the next milestone.
