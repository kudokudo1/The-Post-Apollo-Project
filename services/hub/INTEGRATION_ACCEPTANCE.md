# 🏥💜 ApolloHubW // B11 Integration and Desktop Acceptance

**Checkpoint:** October 22, 2026. **Authority:** operator controls local activation and acceptance. **Technical source of truth:** `kudokudo1/The-Post-Apollo-Project` GitHub `main`. Hospital ownership/assignment state is not inferred from this document.

This is a **verification/handoff** artifact, not a new backend or authorization to change the live desktop. All ten original module IDs are implemented as source-level views; a UI being mounted and CI passing **do not** establish that Fedora/Quickshell has accepted it.

## IMPLEMENTATION // Current source inventory

| Module ID | User-facing area (default) | Source owner/data path | UI at Oct 22 | Desktop evidence |
| --- | --- | --- | --- | --- |
| `weather` | Dashboard / Overview | Existing WeatherService → shared live bridge | Connected | Operator-reported Weather PASS |
| `cpu` | Console / Quick | Existing SystemTelemetry → systemSnapshot | Connected | No explicit B2 live PASS recorded here |
| `network` | Console / Quick | Existing Networking + Network dock bitrate → networkSnapshot | Connected | Live screenshot showed Wi-Fi and bitrate; disconnect/reconnect acceptance still open |
| `media` | Media / Player | Existing Hi-Fi controller + selected MPRIS → mediaSnapshot | Connected | Operator-reported B4 PASS |
| `uptime` | Dashboard / Overview | One read-only /proc/uptime source → uptimeSnapshot | Connected | Snapshot visible in supplied desktop image; persistence/advancement acceptance open |
| `apps` | Console / Quick | Quickshell DesktopEntries → appsSnapshot | Connected | Operator-reported catalog PASS after Qt list fix; app launch behavior not independently accepted |
| `todo` | Dashboard / Overview | ApolloHubTodoStore singleton → separate atomic local JSON | Connected | Create/save/restart/delete acceptance open |
| `notes` | Dashboard / Overview | ApolloHubNotesStore singleton → separate atomic local JSON | Connected | Explicit Save/restart/revision acceptance open |
| `calendar` | Dashboard / Overview | Shared live bridge clock → calendarSnapshot | Connected | Month navigation/midnight acceptance open; no event source |
| `time` | Dashboard / Overview; Media / Player | One existing tile 1-second timer → pure TimePolicy | Connected | Time formatting/12–24/midnight acceptance open |

**Default mode positions may differ from the operator's customized layout.** The `ApolloHubW` window receives one shared `liveBridge`; the To-do and Notes mini-widgets use the existing registered singletons rather than putting their files into the layout JSON. The Apps mini may request `DesktopEntry.execute()` only after an explicit row click. Hub media observation does not grant transport controls.

**Important distinction:** A screenshot of a populated tile is useful partial evidence, not a successful full lifecycle/disconnection/save test. Never treat a user-reported PASS for one module as acceptance for unrelated modules.

## HOW TO USE // Desktop smoke checklist

Use the **existing ApolloHub dock on the running system after the operator has synced and restarted**, not the standalone preview for service checks. Do not reset or remove personal data. Tick each item only after it has been observed on the local runtime.

- [ ] **Shared shell & navigation:** Open/close Hub repeatedly. Tab/Shift+Tab switch modes; arrows work outside input fields; typing in Notes, To-do and mode-name fields keeps normal editing keys. Closing Hub leaves other widgets and Quickshell responsive.
- [ ] **Weather:** Temperature/condition and AQI, if available, match the Weather dock; missing/stale values are marked unknown rather than invented. Existing operator PASS is recorded above.
- [ ] **CPU++:** Visit Console / Quick and open CPU. Values agree with CPU++; refreshing uses the existing sampler, with `--` for unknown data. Reopening/reselecting does not spawn a second sampler.
- [ ] **Network:** Wi-Fi/Ethernet and active SSID agree with the Network dock; link speed is a *link estimate*, not measured Internet speed; disconnect/reconnect is reactive; unknown signal and speed stay `--`; `INTERNET UNVERIFIED` remains distinct.
- [ ] **Media:** Pause/resume and externally select an MPRIS player; Hub reflects the chosen player without taking over playback. Close/reopen Hi-Fi without false-playing state or Quickshell stutter. Existing operator PASS is recorded above.
- [ ] **Uptime:** Visible days/hours/minutes match approximate time since OS boot, progress normally, and **do not reset when the Hub closes/reopens**. A procfs read error must not appear as zero uptime.
- [ ] **Apps:** Installed names/icons appear (operator catalog PASS). No app launches when opening/searching/navigating. Operator may click one known benign application explicitly and verify the launch feedback; the Hub should not report window appearance as confirmed without evidence.
- [ ] **To-do:** Using an intentionally disposable checklist item, create, complete, rename, reopen Hub, and verify display. After a user-authorized Quickshell restart verify persistence, then use confirmed deletion. Do not corrupt or overwrite the real personal data file to test failure paths.
- [ ] **Notes:** Create a disposable titled note; edit multiline text and explicitly SAVE; reopen and inspect. Verify no autosave merely from typing, no silent overwrite from a stale revision, confirmation before deletion, and survival across a user-authorized restart. Preserve drafts on save failure. Do not manipulate an actual notes file for fault injection.
- [ ] **Calendar:** Current local date and highlighted day are correct. Navigate previous/next months, test Today and Sunday/Monday starts if controls are available, including leap February and adjacent-month days. Do not display `0 APPOINTMENTS` without an event service.
- [ ] **Time:** Clock increments every second while visible, 12/24-hour toggle changes formatting only, UTC offset is valid for the user's locale, reopening is current, and the local date changes correctly across midnight.
- [ ] **Layout persistence and privacy:** Rearranging/resizing tiles must never overwrite To-do/Notes files. The Hub store, To-do, Notes, network bridge and Media deck remain separated. Unavailable adapters display an honest unavailable state, not a clean zero.

**Safety:** The live data source and user-authored To-do/Notes data are different risk classes. Do not force network disconnections, corrupt persistence files, kill services, or change system time as part of a routine acceptance run. Destructive fault injection requires a separate isolated fixture and operator authorization.

## VERIFY // Automated evidence (source only)

GitHub workflows to inspect on the revision actually deployed:

| Workflow | Contract scope |
| --- | --- |
| `apollo-hub-foundation.yml` | Hub layout, keyboard, and all ten mini-widget source bindings |
| `apollo-hub-live-bridge.yml` | Shared Weather, CPU++, Network, Media, Uptime, Apps observations |
| `apollo-hub-todo.yml` | Task schema and atomic local store boundaries |
| `apollo-hub-notes.yml` | Notes schema/revisions, explicit-save store |
| `apollo-hub-calendar.yml` | Civil month grid, DST, and no-events contract |
| `apollo-hub-time.yml` | Time formatting, DST, fractional offsets and existing tick ownership |

No workflow above proves `FileView` actually saved data on the user's Fedora installation, MPRIS reacts live, Wayland focus works, or the user has pulled the latest `main`.

## WATCH OUT FOR

1. **Preview is not the live shell.** `apollo_hub_click_preview.qml` does not inject `apolloHubLive`, so the service-backed tiles can be unavailable there by design. See `tests/hub/README.md`.
2. **Single-writer storage:** To-do and Notes stores use separate `Quickshell.dataDir` JSON files, asynchronous atomic saves, and explicit user actions. An in-progress save is not confirmation; a failed save must not silently replace a previous confirmed document.
3. **UI ownership:** Widget/layout/focus refinements belong to the active UI worker. Backend owners should not patch appearance or construct new source instances to fix visual symptoms.
4. **No fabricated connectivity:** Network local-link success is never proof of working internet. Calendar event count is unknown because no event provider is connected. MPD/MPRIS state is not proof of audible output.

## CHECKLIST // Stage gate

- [x] Original ten module backend/source foundations exist.
- [x] Original ten module UI/view implementations exist on GitHub main.
- [x] Shared-shell bridges and singleton stores are represented in source.
- [x] Historical standalone-preview instructions reconciled with live-shell integration.
- [ ] Confirm relevant CI workflows at the **exact SHA** being deployed.
- [ ] User sync and local Quickshell runtime acceptance for each unaccepted item above.
- [ ] Independent verification of the resulting operator acceptance evidence.

## NEXT

Have the UI and verification chats use this checklist as the cross-module acceptance ledger, marking **each** checked behavior with the observed result and version. Backend continuation should be driven by a **specific failing runtime behavior**, not by creating an eleventh backend without need. Possible future functionality (events, application workflows, expandable modules, TimeW tools) requires its own scoped design decision.

## DECISIONS

- **No local operation authorized or performed by this document.**
- **No additional timer, command, file store, event sync, or UI component** required for B11.
- **No Hospital assignment/ownership transfer implied.** The operator remains final acceptance authority.
- Preserve all existing per-module contracts in `services/hub` and use GitHub as technical truth.
