# HI-FI // SERVICE & DIAGNOSTICS PANEL

**STATUS:** PROPOSAL / NOT IMPLEMENTED
**DATE:** 2026-10-22
**OWNER / DOMAIN:** Post-Apollo Hi-Fi media widget and media-controller service
**ENTRY POINT:** `widgets/MediaDeckW.qml`, proposed secondary `SERVICE // DIAGNOSTICS` mode
**CONTEXT:** Radio Browser directory and guarded per-station MPD playback were implemented in PRs #458 and #491. The operator had to inspect source files, restart the user controller service, and use the CLI to diagnose `UNKNOWN_SOURCE` and `PLAYBACK_UNAVAILABLE`. These administrative checks should be available from Hi-Fi itself, without granting hidden or automatic playback authority.

## Goal

Provide a dedicated troubleshooting area for ordinary listeners and advanced users. Show real backend state, translate raw error codes into useful explanations, and offer controlled recovery. Keep normal playback hardware uncluttered; diagnostics should be a secondary view reached from the control bay.

## Proposed UI

- Header: **HI-FI // DIAGNOSTICS**, following current Post-Apollo universal menu grammar and established measurements/components. Do not invent geometry, header colors, button styles, or glows before comparing live implementations.
- Four initial read-only indicators: **Media controller**, **MPD backend**, **Radio Browser discovery**, **Stream relay**. Each must show actual known/unknown/unavailable status rather than inferring healthy from module visibility.
- Later expand source-specific sections for **local MPD**, **MPRIS** (explicit selected player only), **YouTube catalog** (catalog-only unless independently authorized), and radio network/format failures.
- A small, bounded diagnostic history can retain recent failures with timestamps, source, short description, and recovery result. Establish privacy and retention rules first.

## Six candidate controls

| Control | Intended action | Boundaries |
|---|---|---|
| **CHECK STATUS** | Read existing health, sources and snapshot observations; report component availability and age | Read-only, no auto-restart |
| **TEST STATION** | Safely diagnose the selected radio station's stream readiness without starting audible playback | Separate discovery from playback; reuse approved relay validations; no arbitrary URL requests, no MPD queue mutation |
| **VIEW LOGS** | Display bounded, recent, relevant media-controller or MPD errors | No unbounded journal dump; redact station tokens, filesystem secrets, API keys, and private URLs |
| **COPY REPORT** | Generate a concise, user-shareable, sanitized report with versions, statuses, errors and timestamps | Explicit user copy; never export raw tokens or credential-bearing URLs |
| **RECONNECT** | Retry a failed controller connection or refresh/rediscover sources | Bounded retry with visible outcome; must not reset queue or steal playback ownership |
| **RESTART SERVICE** | Explicitly request restart of `post-apollo-media-controller.service` | High-impact, requires confirmation and an authorized, narrowly scoped control surface; restarting invalidates ephemeral radio relay URLs and controller ownership. Never restart Quickshell/MPD as a side effect |

These are *proposed* UI actions, not operational buttons. Determine whether each can use existing AppControl/Hospital or service-control mechanisms instead of adding a privileged helper. A restart must not be exposed as an unguarded command.

## Error interpretation

| Backend / observation | User-facing explanation | Suggested next action |
|---|---|---|
| `UNKNOWN_SOURCE` | Running controller doesn't recognize this source; source registry may be stale | Compare active service and deployed code, then offer confirmed service restart |
| `PLAYBACK_UNAVAILABLE` | Selected source isn't currently permitted to load, or guarded radio relay isn't registered | Inspect `sources` capability and relay availability; avoid blaming the station without evidence |
| `BACKEND_OFFLINE` | MPD backend isn't responding | Check MPD status; no automatic daemon restart |
| `STREAM_DNS_BLOCKED` | Stream destination failed public-address safety validation | Report blocked station; never bypass DNS restriction |
| `STREAM_HTTP` / `STREAM_FORMAT` | Stream endpoint didn't return an accepted direct MP3 response | Explain stream-format/redirect limitation; offer another station |
| Controller connection failure | UI can't contact Unix-socket controller service | Show service status, local controller version, and recovery choices |
| Genuine stale observation | Latest MPD observation expired | Report age/source; don't present old playback information as live |

Treat any unmapped error generically but retain its sanitized code in the report. Do not treat successfully loading, queuing, or connecting as evidence of audible output.

## Reuse existing implementation

Relevant files to inspect before implementation:

- `widgets/MediaDeckW.qml`, `widgets/MediaDeckBrowserControls.qml`: Hi-Fi UI and control bay
- `services/media/HeadlessMediaController.qml`: QML-to-existing-controller bridge
- `scripts/media/media_controller.py`, `scripts/media/media_controller_cli.py`: controller protocol and `health`, `sources`, `snapshot`, `audio_evidence` commands
- `scripts/media/media_controller_server.py`, `ops/systemd/user/post-apollo-media-controller.service`: user-service lifecycle
- `scripts/media/radio_browser_catalog.py`, `scripts/media/radio_stream_relay.py`: directory and guarded radio stream behavior
- `scripts/media/HEADLESS-CONTROLLER.md`, `scripts/media/RADIO-BROWSER-DIRECTORY.md`: current user-service contracts
- Existing Post-Apollo AppControl, ActionButton and status/notification components, plus canonical Syntagma rules

No new polling process, parallel media-controller, global keyboard ownership, hidden network permissions, or service restart should be introduced solely for this interface.

## Suggested implementation order

- [ ] Inventory existing Hi-Fi diagnostics/status surfaces, AppControl service actions, ownership and current GitHub `main`
- [ ] Build a **read-only** diagnostics mode using existing `health`/`sources`/`snapshot`/audio observations
- [ ] Map error codes to clear explanations with reliable unavailable/unknown states
- [ ] Add bounded **CHECK STATUS** and sanitized **COPY REPORT**
- [ ] Add safe, bounded **VIEW LOGS** with documented log source/permissions and redaction
- [ ] Design **TEST STATION** with explicit network budget, no autoplay, no queue changes, no unrestricted URL fetch
- [ ] Add **RECONNECT** if existing bridge supports safe retry without disrupting playback
- [ ] Reuse or propose a privileged **RESTART SERVICE** action behind confirmation and explicit operator approval, preserving remote/session safety
- [ ] Test offline/stale controller, stale source registry, MPD down, unsafe DNS, stream-format failure, service restart during loaded radio, and unrelated-player ownership
- [ ] Run source tests/CI, then controlled Quickshell runtime acceptance with operator
- [ ] Operator decides final placement, geometry, history retention, and whether any service action should be available to ordinary users

## Decisions and exclusions

**Agreed direction:** A permanent secondary Hi-Fi diagnostics mode is useful. Six action candidates and four initial status indicators form the design starting point. Error translation and report export are priorities.

**Not decided:** Exact view layout, whether all six actions ship, service-control authorization route, diagnostic history retention, and scope of background health checks.

**Not authorized by this document:** Implementing UI, modifying shared system services, granting systemd powers, restarting audio/Quickshell, merging other workers' work, or bypassing stream security checks.

## Handoff / acceptance

Future worker: read `Meta-Apollo-Logos-Syntagma/AGENTS.md` and relevant Hospital protocol before accepting work. Inspect current repository state and assignment ownership; this document is a **plan**, not a live Hospital Assignment. Preserve separate Media, AppControl, MPD, MPRIS and Hub ownership. Report major boundaries in the canonical seven-section Hospital form: IMPLEMENTATION, HOW TO USE, VERIFY, WATCH OUT FOR, CHECKLIST, NEXT, DECISIONS.

**Runtime evidence needed:** actual media status responses, user-confirmed controls, a verified safe recovery path, and sanitized logs/reports. User's final acceptance is required before marking implemented functionality DONE.
