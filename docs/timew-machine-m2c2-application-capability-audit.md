# MACHINE // M2c2 // application adapter capability audit

**Date:** 2026-10-24 EDT / 2026-10-25 UTC.
**Owner:** TimeW/MACHINE, The-Post-Apollo-Project. Operator is final authority.
**Scope:** Read-only public API and existing repository source audit. Not a runtime
probe, installed-app audit, live capability claim, browser inspection, recovery
permission or new application adapter.

## Meaning of evidence

There are three different stages:

1. **Documented interface:** official API describes functions. This does not
   prove the operator's installed app/version can use them.
2. **Runtime verified:** a narrowly scoped, permissioned *isolated* test
   demonstrates a specific read or action against the right app instance.
   Nothing in this milestone meets that standard.
3. **Safe checkpoint reconstruction:** separately tested stable matching,
   nonduplication, privacy, reopen/undo semantics and user confirmation.
   Nothing in this milestone meets that standard either.

**Do not show "supported", "connected", "recoverable" or "exact session match"
because this document cites an API.** Registry declarations remain schema-only.

The sidecar, `services/time/MachineAdapterRegistry.py`, and existing v1
layout-only stores are unchanged. The audit JSON
`docs/timew-machine-m2c2-app-capability-evidence.json` is bounded by a pure
validator (`MachineAdapterEvidencePolicy.py`) which rejects attempts to
mark any entry as live verified, activated or arbitrary-checkpoint recoverable.

## Sources and findings

| Family / specific interface | What is documented | Why it is NOT yet arbitrary-point recovery |
| --- | --- | --- |
| Chromium extensions: Brave/Chrome-family candidate | `tabs` and `sessions` describe live tab/window metadata and recently closed restoration | Permissions are needed; live IDs are not checkpoint-stable IDs; `sessions.restore` targets the browser's closed-session history, not any MACHINE save |
| Firefox WebExtensions | `sessions` can restore recently closed tabs/windows, and Firefox exposes extension-scoped tab/window state | Closed session IDs differ from live tab IDs; Firefox/Chromium API support and private-window behavior require per-browser tests |
| Kitty | Native `save_as_session` and sessions support OS windows, tabs, splits/layouts and launch recipes; separate remote-control interface exists | Session files can contain commands and private directories; the documented `--use-foreground-process` option could rerun dangerous programs |
| WezTerm | `wezterm cli list --format json` reports windows/tabs/panes and workspace data | Output also contains titles and working-directory URIs; it is a live inventory, not a durable proof of same process after restart |
| Ghostty Linux | Official support for Linux Wayland and X11 | We have **not verified** a stable public session enumeration/rebuild API for Linux; Linux window presence alone proves nothing about tabs/splits recovery |
| VS Code | `window.restoreWindows`, `files.hotExit` and extension API `window.tabGroups` | VS Code's own recent window/dirty-buffer behavior is not an arbitrary MACHINE historical snapshot; extension UI data requires explicit authorization |
| Existing Post-Apollo Proton pilot | An opt-in native messaging/activeTab/scripting extension scoped to Proton, with a strict read-only local host | **Not a generic browser session extension**; reuse only trusted transport/security patterns after coordinating with Notifications ownership |
| Existing v1 Sway fallback | One-shot read-only output, workspace and app/window placement inventory | No stable individual window or inner-session ID; cannot reopen tabs or declare exact session match |

### Primary sources (vendor/owner documentation)

- Chromium tabs: https://developer.chrome.com/docs/extensions/reference/api/tabs
- Chromium sessions: https://developer.chrome.com/docs/extensions/reference/api/sessions
- Firefox sessions: https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/sessions
- Firefox closed-session identity: https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/sessions/Session
- Kitty sessions and command warning: https://sw.kovidgoyal.net/kitty/sessions/
- Kitty remote-control protocol: https://sw.kovidgoyal.net/kitty/rc_protocol/
- WezTerm list: https://wezterm.org/cli/cli/list.html
- WezTerm instance targeting: https://wezterm.org/cli/cli/index.html
- Ghostty Linux scope: https://ghostty.org/docs/linux
- VS Code window restoration: https://code.visualstudio.com/docs/editing/getting-started/userinterface
- VS Code hot exit: https://code.visualstudio.com/docs/editing/codebasics
- VS Code extension tab model: https://code.visualstudio.com/api/references/vscode-api

### Relevant internal owner seams

- `integrations/proton/browser/manifest.json` and
  `manifest.firefox.json` declare `activeTab`, `nativeMessaging`,
  `scripting`, *not* broad `tabs` / `sessions` permissions.
- `integrations/proton/browser/proton_native_host.py` contains the existing
  bounded native frame/provenance pattern. It is explicitly a Proton-only
  handshake and cannot be silently repurposed for reading tabs.
- `services/notifications/BrowserSiteIdentity.js` handles display-only
  notification-origin labels, not individual browser window identity.
- Sway's read-only metadata path currently goes through
  `services/time/MachineSwayRead.py`; `MachineWindowMultiplicity.py`
  handles duplicate counts, not stable instance identification.

Coordinate with the Notifications/Proton companion worker before designing
another browser extension/host, including origin allowlists, consent and
identity handshakes. This audit **does not grant ownership** of their work.

## Concrete next permission gates (future worker)

**Browser-family pilot:** first isolate a fictional test extension that
enumerates one browser window's *non-sensitive* tab IDs/order/profile-scoped
opaque correlation under exact operator permission. Investigate whether
extension-local window tagging, browser-session events, and a secure native
message can maintain a stable association to Sway windows across restart.
Avoid URLs/page titles/history/incognito and live profile scraping. Prove
nonduplication. Chromium versus Firefox permissions and semantics must
be tested separately. Do not attach to Proton extension implicitly.

**Terminal-family pilot:** prefer a synthetic Kitty/WezTerm output adapter
that recognizes multiple OS windows versus internal tabs/panes without
recording working directories, command lines, titles or environment. Review
Kitty session-file behavior before any automatic capture or launch. Never
replay arbitrary commands. Test Ghostty separately rather than inventing
a session API because the program runs under Wayland.

**Editor-family pilot:** use fictional VS Code extension `tabGroups`
records, explicitly separating workspace identity, dirty tab metadata and
content. Investigate permitted local IPC/extension lifecycle without
scraping VS Code databases or reading unsaved documents. The presence of
native window restore is not a guarantee of historical checkpoint recovery.

**Host adapters:** SwayFX/Wayland is the first intended target. Linux X11,
Windows and macOS need separately owned, versioned host probes and safety
reviews. A platform target in the universal manifest is not certified
support for any host.

Each pilot first runs in a disposable isolated test session and returns
documented states: `not_requested`, `denied`, `unsupported`,
`partial` or `reported`, never fabricated `verified` identifiers.
Exact matching, active capability and recovery authorization require later
separate acceptance evidence and operator approval.

## User-facing behavior remains

- **REVIVE:** protect the currently active environment; only minimal
  verified repairs, preserving extra live windows and tabs.
- **RESTORE:** preserve/branch the current environment before attempting
  reconstruction toward the selected checkpoint. Never silently destroy
  recent work.
- Unknown app: basic Sway window layout inventory; do not invent tabs.
- Fully matching v1 layout: `LAYOUT COUNTS MATCH // SESSION IDENTITY UNVERIFIED`,
  not false "failed candidate" or "exactly identical desktop".

The normal interface should eventually be SAVE, REVIVE or RESTORE, review
meaningful changes, CONFIRM. Typed technical approval rehearsal controls
are deferred to Advanced once the working recovery path is accepted.

## VERIFY / HOLD

`python3 -B -I tests/timew/test_machine_adapter_evidence_audit.py`
validates the read-only JSON evidence catalog; TimeW foundation CI runs it.
No live binary execution is required. This audit is current as of its date,
not perpetual certification, and new application versions may differ.

**Do not:** install an extension, ask for debugger permissions, open browser
profiles, read Kitty/zellij command state, enable remote-control sockets,
launch apps, write local files, mutate checkpoints, perform recovery, merge
a PR or activate production without the necessary explicit authorization.
