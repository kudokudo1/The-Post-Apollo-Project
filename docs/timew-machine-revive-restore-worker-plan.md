# MACHINE // REVIVE + RESTORE // durable worker plan

> **Owner:** Post-Apollo TimeW/MACHINE, The-Post-Apollo-Project
> **Planning baseline:** October 24, 2026, `main` `da9222636a3c35ba6c5c7c2c66dc4575d6d9e55c`
> **Status:** Design direction approved for bounded repository development. Individual implementation phases, data-access permissions, app launches, desktop mutation, live activation, production merging and local file edits require their own review/authorization.
> **Authority:** Operator final. Follow `Meta-Apollo-Logos-Syntagma/AGENTS.md` and relevant Hospital protocols. GitHub is technical truth. Do not assume this conversation is a live Hospital assignment or that any worker has inherited an assignment.

## The product, in plain language

The operator wants to **save a working desktop and return to it without understanding window IDs, "eligible candidates", confirmation phrases or compositor internals**.

There are **two distinct recovery modes**. They share an inventory, identity and application-session foundation, but have different policies:

| | REVIVE | RESTORE |
| --- | --- | --- |
| Intent | Continue/reconstitute the *current* working session after disruption | Return toward one explicitly selected *saved checkpoint* |
| Preferred treatment of live work | Keep current windows, tabs and unsaved activity intact; make the smallest repair | First protect the current state/alternate timeline, then reconstruct the saved session within previewed scope |
| Already in place | Leave untouched and report no action needed | Leave untouched and report no action needed |
| Missing apps/windows | Reopen safely recoverable parts only as appropriate | Reconstruct missing saved apps/windows where adapter support and consent allow |
| Extra work since snapshot | Preserve | Never silently destroy; offer keep/branch/review conflicts |
| Unknown identity/state | Report uncertainty; do not guess, close, overwrite, kill or reset | Report uncertainty; do not guess, close, overwrite, kill or reset |
| Storage and semantics | Continuity/revive snapshot, potentially latest authorized session | Explicit historical checkpoint/timeline and selected recovery scope |

**Do not collapse REVIVE and RESTORE into one button, algorithm or semantics.** A common planner may supply facts, but mode-specific policies decide actions. Neither mode promises exact application RAM, volatile browser form state or unsaved files without real native support. Filesystem rollback requires a separate real snapshot backend and separate authority.

The operator currently keeps approximately **17 Brave browser windows** and **3–4 Kitty windows**. The same app ID across many windows is normal, not a failure. Identity matching must operate per **window, session and inner tab**, not merely app ID. This includes distinguishing multiple Brave profiles/windows and Kitty windows/tabs/splits, and rebuilding missing sessions where actually supported.

## Verified source as of the baseline

- `services/time/MachineSwayRead.py` reads Sway outputs/workspaces/tree on demand; the saved projection currently retains **`app_id`, `workspace`, `floating`** per window, without persistent per-window identity.
- `services/time/MachineCheckpointModel.py` and `MachineCheckpointStore.py` use strict v1 metadata-only documents. `machine.db` stores UUID records and labels. Current CLI supports `save`, `list`, `load`, **not rename**.
- `services/time/MachineWindowResolver.py` groups windows by app ID and requires one saved and one live instance to produce a move candidate. Duplicate Brave/Kitty instances become `AMBIGUOUS APP INSTANCES` even where counts and positions could match.
- `services/time/MachineWindowMovePilot.py`, `MachineMoveJournal.py`, `MachineMoveApproval.py` and reconciliation implement guarded *single-window isolated* tests; no general live recovery.
- `widgets/TimeW.qml` includes M1o review and M1p exact-phrase rehearsal. These are non-operative. The operator explicitly found the technical controls and jargon too complex.
- M1m's real move test ran in a **disposable headless stock Sway CI session**, not the operator's production SwayFX.
- The operator reports **seven saved checkpoints surviving a desktop reset** and a working CHECK INTERRUPTS control reporting no unresolved moves. Do not claim that a full OS reboot was tested unless separately clarified.

Never edit, replace, drop, reinterpret or migrate those seven existing checkpoints as a side effect of developing v2. Do not treat any existing v1 record as if it contains browser tab state, terminal session state, or a stable window ID. Keep v1 readable and recoverable. Do not copy real private session data into GitHub, CI artifacts, errors or chat logs.

## Required user-facing outcomes

1. User can SAVE the desktop; optionally name/rename saved checkpoints later. Avoid long timestamp strings as primary display labels. Keep underlying UUID and timestamp as secondary metadata. **Names and button art deferred until functionally sound.**
2. On REVIVE or RESTORE, classify each item as **ALREADY IN PLACE**, **NEEDS MOVING**, **NEEDS OPENING**, **NEEDS ATTENTION** or **NOT RECOVERABLE**. A completely matching layout should say `LAYOUT MATCHES`; **`EXACT SESSION MATCH` requires verification of window *and* internal session identity/state**. Layout count equality alone never proves tab/session identity.
3. Reuse existing unique windows and tabs where confidently identified, even with 17 Brave windows and multiple Kitty windows. **Never create duplicate windows/tabs to compensate for uncertainty**.
4. Missing apps/windows can eventually be launched/reconstructed from saved per-app session descriptions with explicit narrowly scoped consent. App open != window state restored != volatile process memory revived; show these distinctions.
5. REVIVE preferentially preserves live work. RESTORE must preserve the current state first and make conflicts/branching explicit. No silent close, overwrite, auto-rerun of arbitrary commands or forced browser-profile reuse.
6. Core workflow understandable without engineering language: **SAVE → choose REVIVE or RESTORE → inspect meaningful changes → CONFIRM**. No typed challenge phrase for ordinary use. Internals stay in an ADVANCED panel. Satisfy safety with contextual, action-scoped confirmation rather than burdensome syntax.

## Identity and reconciliation architecture

Separate four identifiers, with explicit confidence:

- **Checkpoint-local window key:** unique within saved snapshot; not guaranteed stable across sessions.
- **Ephemeral compositor con_id:** valid only after a fresh Sway read; never persisted or considered a durable identity.
- **Application instance/session key:** must come from an authorized, app-specific adapter if supported (e.g., browser profile+window correlation or Kitty managed session); do not fabricate one from title/order/PID.
- **Inner-session item key:** tabs, splits, tab groups, pinned/active state, layouts or startup descriptors, subject to adapter capability and permission.

Start with a **read-only multiset inventory comparison** from v1 fields so duplicate app windows are counted correctly. A matching collection of Brave windows across workspaces may be reported `LAYOUT COUNTS MATCH // SESSION IDENTITY UNVERIFIED`. It is **not** permission to identify individual windows, reposition them, reopen anything or claim exact session equality.

Future v2 should be **versioned and opt-in**, with explicit capabilities and redactions, not a silent migration of `machine.db` v1. Evaluate a sidecar/session catalog keyed by checkpoint UUID and per-window local IDs. Preserve absent/denied/unsupported as distinct states. Use deterministic, explainable matching with scores/evidence and an *unknown* outcome, not arbitrary best guesses.

### Browser adapter track (requires separate owner coordination / consent)

Investigate Brave's supported profile/session/extension interfaces and whether they can enumerate **per-window/tab** IDs, profile identity, tab order, pinned tabs, groups and active tab *locally*; ascertain whether window identity is stable across crashes and restarts. Use browser-supported restore/open APIs where possible. Avoid CDP debug ports by default, never scrape encrypted profile data, cookies, passwords, private/incognito content or browser history without explicit permission. A tab's URL is private. Do not assume recently closed or browser-session restore can reconstruct an arbitrary historical checkpoint; do not promise restoration of unsaved forms.

### Kitty adapter track (requires separate consent)

Investigate Kitty's supported session save/restore and remote-control APIs, independent OS windows vs Kitty tabs/splits, layouts, launch descriptors and working directories. Avoid recording terminal buffers, passwords, environment secrets or automatically rerunning commands/scripts. Restoring a shell/layout differs from reviving a running process. Respect existing Kitty/zellij setups and live controls. Do not launch or kill instances during an identity-only milestone.

### Desktop/backend and snapshot track

Sway/SwayFX: capture monitor/workspace/window geometry where available, window identity correlation only when verified, focus as a separately previewed suggestion. Recheck immediately before each authorized action. The existing before-state SQLite operations journal is separate from saved checkpoints. Crash/uncertain records require review; never auto-retry or auto-Undo.

True filesystem history and app memory restoration are distinct future tracks requiring dedicated snapshot interfaces, storage/security budgets, exclusions, rollback and explicit authority. Do not use Git or filesystem snapshots as a magical substitute for app sessions.

## Milestone order and acceptance gates

- **M2a (start here):** pure read-only *multi-instance layout inventory* and tests for 17 Brave + 4 Kitty. Classify already-positioned counts, missing counts, extras and uncertain per-app identity; no execution, browser contents, database writes or QML changes. Preserve all M1 tests.
- **M2b:** versioned v2 identity/capability **proposal** with parser + strict tests, read-only sidecar plan; migration strategy with v1 compatibility/rollback tests. Do not collect real private data yet.
- **M2c:** app-adapter capability audit and consent design for Brave and Kitty. Synthetic adapter data first, app owners consulted. Distinguish unknown, disabled, unsupported, partial and verified.
- **M2d:** v2 opt-in local session capture for a narrow app/scope, with owner-only storage, data redaction, bounded retention, explicit saves. Verify preservation of v1 and absence of new background polling.
- **M2e:** shared reconciliation facts + two distinct pure planners: REVIVE minimally repairs current context, RESTORE reconstructs selected historical checkpoint while preserving current timeline. Synthetic scenario matrix includes missing, extra, already-matching, duplicated, uncertain, disconnected outputs and profile collisions.
- **M2f:** guarded app-specific reopen/restore of recoverable window/tab/layout state, only after explicit per-action permission, durable journal/recovery plan and isolated test. Never blindly rerun terminal commands or overwrite browser state.
- **M2g:** operator-accepted simple SAVE/REVIVE/RESTORE workflow; existing technical M1 review buttons move to ADVANCED after safe replacement. Name/rename checkpoint UI and clearer summaries can be implemented as a separate bounded UI milestone.
- **M2h:** opt-in live SwayFX acceptance, crash-recovery, restart/no-op, privacy/security and rollback checks. **No automatic production activation or PR merge.**

Order within independent app tracks may run concurrently under separate documented ownership. Avoid building overlapping collectors, live control surfaces or competing journal writers.

## M2a strict examples

Example: 17 saved Brave windows and 17 live Brave windows distributed across the same workspaces, plus four Kitty windows similarly distributed. Result: `layout_counts_match=true`, `session_identity_verified=false`, `safe_actions=[]`. It must **not** report 21 invalid candidates.

If 2 Brave windows are missing and one extra Brave window is on another workspace, report exact **aggregate counts** with no fabricated per-window pairing. A missing app becomes `NEEDS OPENING (NOT YET SUPPORTED)`, not `INVALID CANDIDATE`.

If source and destination have the same number of windows but in different workspaces, report aggregate placement differences, **not** a provably safe per-window move until a stable identity match exists.

## Gates and handoff for any succeeding worker

1. Read this document, current `AGENTS.md`, relevant Hospital protocols, current `main`, open PRs, tests and any claimed assignment/owner. Confirm no other worker owns the target files.
2. Preserve the seven v1 checkpoints and explicit SAVE behavior. Do not rewrite the SQLite store/schema or modify local files without operator approval.
3. Keep new features dormant/read-only until source contracts, synthetic tests and dedicated review are accepted. No use of the operator's actual browser tabs, paths or local windows during tests without explicit consent.
4. Run the relevant `tests/timew/` suites and dedicated `.github/workflows/timew-foundation.yml`. Document tested commit SHA, PR mergeability, and the difference between CI and live acceptance.
5. Do not merge or activate production without authorization. Keep each workstream in its own focused draft PR and give rollback/checkpoint instructions.
6. At meaningful boundaries report **IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT, DECISIONS**.

### Known unresolved design decisions

- What qualifies as a REVIVE source if no explicit saved checkpoint is selected (last consented session snapshot vs on-demand capture)?
- Exact browser restore/correlation API per version/profile, including the operator's privacy limits and incognito policy.
- Whether Kitty adapter may capture working directories and launch recipes, and how to obtain meaningful session IDs across restarts.
- Whether RESTORE should always branch the live session and what the protected backup implementation is; branch/merge controls are not yet built.
- Whether app-specific session data should be encrypted locally at rest, its retention period and key handling.
- Which launch/startup actions are safe without individually inspecting commands.
- How and when to rename checkpoints; no rename implementation exists in the verified v1 store.
- Exact language and visual styles for user-facing buttons, deferred by operator.

**Near-term acceptance:** M2a read-only duplicate-window inventory with 17 Brave and four Kitty tests, merged only with operator approval. Everything else above is roadmap, not a claim of completed functionality.


## M2c update // Cross-application compatibility (2026-10-24)

**Operator-approved direction:** Brave and Kitty are the initial stress cases,
**not the list of supported applications**. Universal compatibility is a core
constraint: browsers (including Firefox/Chrome/Edge/Opera/Mullvad), terminals
(including Ghostty/WezTerm/Foot), editors and IDEs (including VS Code, Zed,
JetBrains), file managers, office, media and other families.

The M2b parser's hardcoded Brave/Kitty adapter types are being replaced in a
separate draft PR by a data-only manifest registry. See
`docs/timew-machine-m2c-universal-adapters.md`. Registry declaration is
**not** evidence of installed/usable integration. Every app's live identity,
tab/session recovery, data permission and launch capability must pass separate
verification. Linux Wayland, Linux X11, macOS and Windows require distinct
host adapters; listing them as targets never means they are supported.

Preserve both recovery semantics: REVIVE repairs current work minimally;
RESTORE reconstructs selected historical work only after protecting the
current timeline. Unknown apps retain the basic v1 layout-only fallback.
Do not fake exact session equality from matching app/window counts or
arbitrary UUIDs. Future workers must not implement a special-case switch for
Brave/Kitty instead of the registry, and must not access private app content
during this schema-only phase.

**Next gate after M2c registry:** audit actual browser, terminal and editor
interfaces and ownership, then present a capability/consent matrix. No
active capture, launch, migration, app command replay or live restore yet.


## M2c2 update // Evidence-based app integration audit (2026-10-24)

The universal adapter registry is **schema-only**. A source-backed audit now
resides in `docs/timew-machine-m2c2-application-capability-audit.md`, with
machine-readable, explicitly non-operative evidence in
`docs/timew-machine-m2c2-app-capability-evidence.json`. Its pure validator
`MachineAdapterEvidencePolicy.py` rejects any claim that documented vendor
APIs prove a live MACHINE integration or arbitrary-checkpoint restoration.

The audit distinguishes Chromium/Firefox browser APIs, Kitty session files,
WezTerm CLI, Ghostty Linux support, VS Code window/editor APIs, the existing
Proton-specific browser native messaging pilot and the generic Sway fallback.
No app-specific live reader has been installed or run. Do not reuse the
Proton extension without coordinating with its Notifications owner. Do not
automatically execute commands from terminal session files. Browser session
history is not the same as an arbitrary MACHINE checkpoint.

**M2d next gate:** operator-reviewed narrow permission boundary, disposable
integration test, per-app-instance correlation, private metadata exclusions,
fresh revalidation and nonduplicate behavior. No browser tabs, terminal
directories/commands or editor document paths may be read from the live
workstation until explicitly approved. Continue to preserve seven v1 saves
and keep REVIVE and RESTORE separate.


## M2d stage 1 // Synthetic host-to-app correlation (2026-10-24)

Bounded GitHub implementation: `MachineAdapterFixtureCorrelation.py`
and `docs/timew-machine-m2d-fixture-session-correlation.md` test a pure,
read-only, synthetic host/compositor window list against fabricated browser,
terminal and editor reports. A scoped opaque challenge and declared
adapter/application namespace are required to correlate windows, with
duplicate, cross-app and stale-scope claims rejected. The 23-window
synthetic case includes 17 Brave, four Kitty, Firefox and VS Code.

This tests *shape and failure handling only*. Fixture claims are untrusted,
do not establish restart-stable identity or exact matching, and cannot
read tabs, launch apps, move windows, change checkpoints or approve recovery.
Results never emit safe actions. A browser's live `windowId`, a host
`con_id`, an application title or matching counts must never substitute
for independently authenticated app-to-host correlation.

**M2d stage 2 remains unauthorized:** separate trusted transport,
app-scoped permission, origin/provenance, isolated replay/duplication tests,
opt-in privacy choices and only then consideration of owner-only v2 storage.
Coordinate with Notifications/Proton ownership; do not repurpose its
narrow browser extension. Preserve REVIVE current-work and RESTORE
historical-checkpoint semantics.


## M2d2 // Synthetic one-shot handshake policy (2026-10-26)

Stage 1's synthetic app/host correlation PR #793 is merged.
`services/time/MachineAdapterHandshakeTrial.py` now models the separate,
required **one-shot, scope-bound, expiring, cancelled/replay-safe handshake**
for 17 Brave + four Kitty + Firefox + VS Code + Ghostty test fixtures.
See `docs/timew-machine-m2d2-handshake-trial.md`.

**All flags and observations in the test harness are simulated**, including
the apparent user permission and source labels. The simulator **cannot**
authenticate real applications, verify SwayFX mapping, inspect sessions,
issue a usable permission token, save v2 sidecars or restore anything.
A successful synthetic echo still reports `real_app_identity_verified=false`,
`real_host_binding_verified=false`, `operator_consent_verified=false`
and `safe_actions=[]`.

**Next required decision:** design and obtain operator permission for one
isolated **real read-only authenticated app-to-host bridge**, including
per-application identity, extension/OS transport provenance, consent,
private-mode exclusion, duplicate-host handling, TTL/replay control and
a rollback plan. Coordinate with Notifications/Proton component owners.
Never enable general session access, native host installations or terminal
remote-control sockets based on this simulated passing test.
