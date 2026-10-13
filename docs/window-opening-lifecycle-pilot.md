# Syntagma // widget opening lifecycle: evidence and opt-in comparison

**Status:** Stage 1 experiment, NOT a universalized rule or a runtime-verified
migration. **Scope:** window presentation/mapping only. This document does
not redefine keyboard focus ownership, Main/Sub Mode navigation or the
Koinoikos compositor protocol. Based on current Post-Apollo source and
the operator's October 13, 2026 instruction to compare demonstrated needs.

## The question

Does an ordinary interactive layer-shell menu require its surface to remain
mapped while closed, or can it use `visible: menuOpen` without losing any
functionality, responsiveness, keyboard-focus recovery or reopen stability?

**Mapping is not the same as keeping QML state alive.** Hiding the native
surface does not necessarily destroy the QML object or reset its services.
Likewise, a permanently mapped window with a zero input region is not
necessarily the compositor's focused keyboard window.

## Existing opening strategies (before any migration)

| Widget | Existing presentation lifecycle | Evidence and legitimate difference | Stage 1 disposition |
| --- | --- | --- | --- |
| Git | Always mapped; on close `mask` has zero size | Source uses shared keyboard coordinator and a complex scene; no proven need for permanent mapping. Open triggers refreshes separately. | **A/B pilot:** keep permanent mapping by default; optionally unmap on close |
| Hospital | Always mapped; zero input mask on close | Many nested surfaces and refreshes, but those alone do not establish a mapping requirement. | **A/B pilot:** keep permanent mapping by default; optionally unmap on close |
| Notifications Hub | Always mapped; zero input mask on close | **Documented exception:** source records a native Qt/Quickshell second-open crash on repeated unmap/remap. | **Do not change** until crash history is reproduced/isolated |
| AppControl | `visible: menuOpen` | Complex widget working with visibility-based lifecycle; keeps ordinary QML state and initializes selected mode/input on open | Comparison reference; no changes |
| CPU++ | `visible: menuOpen` | Refreshes monitors/animates on open while using visibility lifecycle | Comparison reference; no changes |
| Weather | Window object always visible; zero-width/height when closed, with specialized terminal mouse mask | Terminal exclusion/mouse pass-through is a real function, but evidence for zero-size opening strategy as a requirement is incomplete | Audit after the first pair |
| Power | Persistent window containing **both the closed dock trigger and opened power menu**, interactive regions masked accordingly | Trigger must remain present when menu is closed in the current composition; this does not require all *separate* windows to stay mapped | Distinct composition, no change |
| Social | Permanent nonfocusable/fully masked controller plus a visible native `FloatingWindow` | Provides ordinary Sway move/resize and separate Discord/Vesktop window handoffs | Native-window adapter exception; no change |
| Media Deck | `visible: menuOpen` and no keyboard focus | Pointer-operated deck, naturally visibility-based | Comparison reference; no change |
| Incoming notification toast | Visible only with active notifications | Passive event surface, not a Main Mode menu | Outside this pilot |

**Source history:** Notifications carries an explicit crash comment;
Social explains its `FloatingWindow` choice; the other rationales are
inferences from current behavior, not proven original developer intent.

## Pilot configuration // Git and Hospital only

The initial experiment is **off by default**. Only the surface's
`visible` binding changes in opt-in mode. Mask, focus policy, input handlers,
geometry, services, loading/refresh, menu state and animations are unmodified.

| Mode | Git environment | Hospital environment | Effect |
| --- | --- | --- | --- |
| Existing baseline (default) | unset | unset | Both stay mapped; zero-size input mask when closed |
| Git only | `POST_APOLLO_GIT_VISIBILITY_PILOT=1` | unset | Git unmaps when closed; Hospital baseline |
| Hospital only | unset | `POST_APOLLO_HOSPITAL_VISIBILITY_PILOT=1` | Hospital unmaps when closed; Git baseline |
| Combined stress test | `...GIT_VISIBILITY_PILOT=1` | `...HOSPITAL_VISIBILITY_PILOT=1` | Both use visibility-controlled opening; try only after independent trials |

Anything other than the literal value `1` uses the original permanent
mapping. The options are read when the QML window is instantiated; change
them only via a **full Quickshell restart**, not a hot reload.

### Optional on-device trial

Run these from a local checkout containing this change, **after** its files
have been installed into the Quickshell configuration you actually launch.
The existing safe restart script is intentionally used because Qt sampled
glow destruction previously crashed during live QML hot reload:

```bash
# Baseline: both menus retain the current lifecycle.
scripts/restart_quickshell_safe.sh

# Git-only test; leave Hospital on the baseline.
POST_APOLLO_GIT_VISIBILITY_PILOT=1 scripts/restart_quickshell_safe.sh

# Hospital-only test; leave Git on the baseline.
POST_APOLLO_HOSPITAL_VISIBILITY_PILOT=1 scripts/restart_quickshell_safe.sh

# Restore existing mapping without editing any files:
scripts/restart_quickshell_safe.sh
```

If executing the script as a command is not permitted, use `bash
scripts/restart_quickshell_safe.sh`. The script forcibly stops the previous
Quickshell process; save any open widget edits or drafts before invoking it.

### What to record for each widget

1. After a fresh restart, open the menu, close it, and reopen it **at least
   ten times**, especially after using editors, selectors and navigation.
2. Check first key (Tab), later keys, keyboard focus acquisition, pointer
   re-entry, and Koinoikos `Super+~` directional focus handoff if enabled.
3. Open Git and Hospital together; click Kitty or another normal Sway app,
   type and paste, then return. **No focus lockout** is acceptable.
4. Check shader glow artifacts, unexpected animation resets, rendering
   errors, stale content, content refresh, size/placement changes or second-
   open crashes. Follow actual terminal logs.
5. Compare perceived first-frame response and first-successful-key latency.
   Do not attribute delays to the shared 120 ms **focus-release** timer:
   it is not a 120 ms pre-open wait. Git's data-refresh path is separate.
6. Perform baseline and opt-in runs after equivalent restarts; note date,
   whether the tested file actually matches GitHub, device/Qt version,
   and whether the difference reproduces on a second test.

**No shell access is available to this GitHub-only authoring workflow.**
GitHub CI checks source conditions and cannot measure Wayland seat focus,
Qt shader teardown or live opening speed.

## Decision gate (before selecting a universal default)

- If repeated visibility-controlled reopening retains function and stability
  and does not worsen focus, promote it as an ordinary-menu default candidate.
- If one widget breaks, capture the exact error, affected surface, and
  reproduction sequence; retain persistent mapping only where evidence
  justifies it.
- Do **not** remove Notifications' known crash workaround, Social's native
  Sway requirement, or Power's always-available trigger as a side effect.
- Test whether the two widgets' current *duplicate* focus requests can be
  consolidated in a **separate focus-ownership change** with its coordinator
  worker. Do not conflate that with presentation-lifecycle testing.
- Only after comparisons, discuss a reusable opening protocol with one
  common sequence and an explicit, evidence-backed presentation policy.

The proposed common sequence remains **request open → present surface →
acquire keyboard when appropriate → activate Qt input target → refresh
content independently**. Its implementation/default is **not yet approved**.
