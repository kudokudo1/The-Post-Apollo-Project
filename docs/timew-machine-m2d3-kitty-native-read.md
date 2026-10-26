# MACHINE M2d3 // Kitty native read-only session inventory

**Milestone:** First real *native-format* application adapter, **dormant**.
**Date:** 2026-10-26. GitHub draft PR only. No live desktop access,
socket connection, installation, permission change, application launch,
checkpoint capture or restoration was performed.

## Why Kitty first

Kitty has a documented native `kitten @ ls` interface that returns a
JSON tree with separate OS windows, tabs and inner terminal windows/panes.
This is better than the old v1 assumption that all windows with the same
`app_id=kitty` are indistinguishable. Unlike previous M2d synthetic
identifiers, this adapter understands **Kitty's actual native response
shape** and can extract usable structural inventory.

It cannot yet establish which Kitty OS window is which SwayFX window, or
whether the same terminal process survived a restart. No arbitrary
checkpoint reconstruction has been demonstrated.

**Security warning:** The same native `ls` response can include tab/window
titles, current working directories, process IDs, command-line arguments
and environment values, including sensitive data. And enabling Kitty
remote control can also allow writing or executing operations. We must not
activate a new general-purpose control socket as a side effect of MACHINE.

Sources: https://sw.kovidgoyal.net/kitty/remote-control/ and
https://sw.kovidgoyal.net/kitty/rc_protocol/ and
https://sw.kovidgoyal.net/kitty/conf/#opt-kitty.allow_remote_control

## Implemented

`services/time/MachineKittyRead.py` adds:

- `normalize_kitty_ls(payload)` accepts Kitty's JSON output as bounded
  UTF-8 bytes/text; checks nested OS window / tab / pane IDs and unique
  values; strips all unapproved fields. It outputs **only** ephemeral
  numeric OS-window/tab/pane IDs, counts, and explicit unverified/disabled
  flags. It never includes original cwd, argv, environment, title, PID,
  buffers, URLs, credentials or other unapproved metadata. No log writes.
- `read_existing_kitty_inventory(...)` is a **dormant function**, not
  wired to QML or a command-line main. It requires an explicit opt-in
  argument, an explicit `unix:/absolute/socket/path` target inside the
  supplied runtime directory, owner-only socket and directory validation,
  and an existing Kitty remote-control endpoint. It never creates or
  enables one. If an authorized future caller invokes it, it runs the
  **fixed read-only command** `kitten @ --to unix:/... ls
  --output-format=json` through `subprocess.run(shell=False)` with
  bounded timeout/output, then immediately projects away private fields.
  No command text is derived from browser content or user-supplied shell
  fragments.

**Opt-in argument is NOT trusted operator authorization.** It is only a
deliberate call-site guard to prevent accidental runtime entry. The
current runtime has no trusted UI authorization/consent gate, no validated
host app mapping and no active connection. A future integration still
needs a real consent mechanism and OS peer/endpoint provenance verification.
The socket ownership check protects against common misconfiguration but
is not a complete pathname race or peer-identity security proof.

The parser emits `input_origin_verified=false`,
`host_window_binding_verified=false`,
`checkpoint_session_match=false`,
`runtime_ids_ephemeral=true`, `safe_actions=[]`,
`capture_enabled=false`, `restore_enabled=false`.
It does not classify identical tab *counts* as exact content equality.
The current v1 store and seven user-reported checkpoints are unchanged.

## Safety test

`tests/timew/test_machine_kitty_read.py` uses a structurally realistic
Kitty native JSON fixture with four Kitty OS windows, tabs and inner panes,
populated with intentionally private fictional cwd, command, env, PID and
title values. All of those values must be absent from output. It tests
wrong types, duplicate IDs, size bounds, path traversal, link/ownership
problems, missing/denied opt-in, non-Unix targets, timeouts, and the exact
fixed native command. The command runner and path stat are **injected
fixtures**. It does not connect to a real Kitty instance.

The source contract prevents QML integration or changes to the existing
checkpoint database, and preserves all existing M1/M2 tests.

## Limitations and next gates

1. Read-only inventory is not a saved Kitty session. It doesn't capture
   working directories, shell history, zellij panes, processes, or session
   launch recipes. Replaying terminal commands must never be automatic.
2. Numeric Kitty IDs can be reused or disappear. A future authenticated
   host-window correlation must verify the exact OS window association in
   the live compositor without relying solely on app name, title, PID or
   order. Until then, no MOVE or RESTORE action may be planned.
3. The user has many other apps; do not build a Kitty-only MACHINE.
   This is the **first application-specific adapter using the universal
   registry**. Browser, editor and other terminal adapters should expose
   equivalent bounded projections with app-specific permissions.
4. Kitty remote control is off by default. Turning it on, even only over a
   socket, widens attack surface. Any experiment requires operator consent,
   an isolated/disposable Kitty instance and ideally a command-restricted
   remote-control policy. Do not change the live user's Kitty settings
   implicitly.
5. The actual `kitten` CLI output and target socket behavior must be
   tested against the user's installed version in an approved isolated
   environment before declaring compatibility.
6. Only after that, design narrow, authenticated endpoint ownership,
   one-shot consent, read-only host correlation, private-data retention
   policy, separate REVIVE and RESTORE planners, and durable recovery
   journals/rollback.

## Operator-facing meaning

- **REVIVE:** keep running terminals and their existing contents; identify
  already-correct windows, then recover only safe missing elements.
- **RESTORE:** protect current work and reconstruct a selected checkpoint
  where the application supports it. No silent shell command execution.
- Exact session equality requires verification of more than Kitty window
  and tab counts.
- The normal UI stays simple. No CLI operation or confusing technical
  candidate selection is exposed by this milestone.

## Rollback and ownership

Revert the focused draft PR if needed. Since no live reads or local writes
were performed, local state requires no rollback. Before further changes,
review the latest Syntagma `AGENTS.md`, open GitHub PRs and Hospital
ownership. Operator retains final merge and activation authority.
