# MACHINE M2c // Universal application adapter declarations

**State:** Safe schema architecture in a GitHub draft PR; not an active plugin
manager, application detector, data collector, session restorer or host backend.
**Priority:** app-independent foundation before implementing Brave, Firefox,
Chrome, Ghostty, VS Code, or other concrete application adapters.

## User requirement

MACHINE must not be a Brave-and-Kitty application. The operator uses numerous
Brave and Kitty instances but also wants Firefox, Chrome, other browsers,
Ghostty and other terminals, VS Code/editor project sessions, and additional
software as compatibility grows. It should be designed for future Linux
compositors, macOS and Windows backends without falsely claiming that
operating-system support already exists.

**REVIVE** continues the current working session with minimal disruption.
**RESTORE** reconstructs a selected older checkpoint while protecting the
current timeline. Both use the same window/session inventory and app-adapter
facts, but *different policy and execution planning*. Do not merge the modes.

## Architecture change

Old M2b `MachineSessionIdentityV2.py` admitted only `none`, `brave` and
`kitty`, then inferred valid inner-item kinds from those hardcoded names.
This forced source edits for every new application.

`services/time/MachineAdapterRegistry.py` replaces that special-case
logic with **explicit, validated, data-only adapter declarations**.
An adapter declaration contains only:

| Field | Meaning |
|---|---|
| `adapter_id` | Namespaced string, e.g., `browser.firefox`, `terminal.ghostty`, `editor.vscode` |
| `family` | Extensible category, e.g., browser, terminal, editor, office, media, custom |
| `app_ids` | Explicit application IDs the descriptor can describe; never guessed by names |
| `item_kinds` | Inner structural kinds, e.g., browser tab, terminal split, editor tab, document tab |
| `target_hosts` | Intended platforms: linux_wayland, linux_x11, windows, macos. **Not tested support** |
| `state` | Mandatory `schema_only`. Prevents confusing a declaration with running capability |

`build_registry(additional_manifests)` accepts newly declared families and
applications without changing the v2 validator. The validator now requires
each window's app ID to match its explicit descriptor, and validates its
inner items against that descriptor's declared kinds. A future app can
declare new inner types without changing the universal parser.
Duplicate adapter declarations, unsafe fields, malformed IDs,
wrong app/kind combinations and executable-looking declarations fail closed.

`none` remains a non-identifying fallback for any unknown application.
It can carry v1-style placement, never imaginary per-window session keys,
tabs or launch permissions.

Two old identifiers, `brave` and `kitty`, are preserved as **legacy
schema-only declarations** so existing M2b *synthetic proposals* still
parse. They are **not** actual installed or working adapters.

`list_schema_capabilities()` deliberately advertises
`installed_adapter_count=0`, `live_capture_supported=false` and
`live_reopen_supported=false`. These are proposal definitions, not
certifications of application support.

## Layers of compatibility

1. **Generic host/layout inventory:** The existing v1 Sway projection can
   count placement for applications with no adapter. No tab/window identity
   is inferred from matching app IDs.
2. **Application-family schema:** An adapter declaration specifies whether
   an app has tabs, splits, editor documents, media slots or custom items.
   This PR adds that extensible structure using synthetic data only.
3. **Actual app integration:** Future reviewed adapters must prove their
   identity mechanisms, permissions, stable IDs, opt-in capture, missing-window
   reopens, failure modes and cross-restart behavior. Not implemented here.
4. **Host backend:** SwayFX/Wayland first; X11, macOS and Windows need
   separate tested host APIs and permissions. Merely listing a host as a
   target cannot establish support.

An adapter can support identity but not reopening, or a project list but not
unsaved document data. Unsupported, denied, partial, reported and
not-requested remain distinct. Any `reported` information remains an
**unverified claim** until a future trusted integration checks it.

## Example synthetic catalog

For tests, describe separate Brave and Kitty legacy instances plus:
`browser.firefox`, `browser.chrome`, `terminal.ghostty`,
`editor.vscode`, `editor.zed`, `office.libreoffice`, and an invented
`future.custom_app`. This deliberately exercises multiple app families,
future editor contents and app IDs, rather than shipping a whitelist of
supposedly supported live applications.

Other future browser declarations might cover Edge, Opera, Vivaldi, Mullvad
Browser and Chromium derivatives; terminal declarations might cover WezTerm,
Alacritty, Foot and others; editors might include VSCodium, Cursor and
JetBrains products. Real APIs must be audited independently. No hardcoded
browser profile scraping, shell commands or PID correlation are introduced.

## Privacy and recovery boundaries

No network access, dynamic imports, installation, background polling,
browser tabs, document titles/paths, terminal buffers, URLs, commands,
passwords or profile content. The registry contains only safe schema fields
and accepts no executable hook or command.

Version 1 `machine.db` is **unchanged**; the seven operator-reported saves
are not read, migrated or rewritten by this code. M2b's proposed v2 records
are still not written to disk. Existing TimeW.qml remains unchanged.

M1k's isolated single-window pilot is also unchanged and is *not* connected
to this registry. No execution is authorized by parsed identities.

## Next milestones

- **M2c follow-up:** inspect actual installed integration components in
  repository and audit supported, permissioned browser, terminal and editor
  APIs against their target versions, with a source/capability matrix.
- **M2d:** separately approved, narrow opt-in read-only adapter, beginning
  with a safe fixture-backed interface. Do not collect actual browser tab
  URLs or terminal commands without explicit operator permission.
- **M2e onward:** two policy planners, REVIVE and RESTORE, using confidence
  and scoped consent; fall back to v1 aggregate layout when identity is
  unavailable; refuse destructive/duplicating guesses.
- **UI:** keep ordinary SAVE / REVIVE / RESTORE understandable; internal
  adapter status and typed technical controls belong in Advanced. Friendly
  checkpoint names are deferred as requested.

## Verification and handoff

Run `tests/timew/test_machine_adapter_registry.py`,
`tests/timew/test_machine_adapter_registry_contract.py`,
`tests/timew/test_machine_session_identity_v2.py` and all TimeW foundation
tests. The fixtures cover 29 mixed windows, the 17-Brave/4-Kitty baseline,
unknown fallback, custom future families, wrong-app and wrong-tab rejection,
platform targeting, strict schema-only declarations and v1 compatibility.

Follow `docs/timew-machine-revive-restore-worker-plan.md`, current
`Meta-Apollo-Logos-Syntagma/AGENTS.md`, GitHub PR status and Hospital
ownership checks. No PR merge, local worktree write, live activation or
application data access without the required authorization.
