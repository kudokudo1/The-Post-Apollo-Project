# Social PHONE P7 // Saved BlueFerry lifecycle, no repeated pairing, and calls-only audio boundary

> **STATE //** GitHub review candidate. Read-only lifecycle and existing-client launcher change, NOT authenticated Social phone content access.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation, P7
> **STAFF //** External Hospital-compatible DOC, not verified attached to a live Hospital Room/Assignment.
> **USER EVIDENCE //** 2026-11-04: After Stage Director terminal placement, the iPhone granted notification/contact permissions and notification audio was heard on Fedora. The setup terminal then closed and Social still did not show a connected phone. The operator wants calls only on the PC, not all iPhone playback.

## IMPLEMENTATION

**Root distinction:** BlueFerry already persists its own pairing/configuration and has an independent user backend; Social P3-P6 intentionally checked metadata and never implemented the authenticated content bridge. A closed terminal does NOT mean pairing was lost, and sound over Bluetooth does NOT prove MAP/PBAP sessions, authorization or a long-lived Social connection. No new Post-Apollo phone registry is needed.

1. New `services/phone/PhoneSavedBridgeState.py` performs read-only inspection of existing `BlueFerryReadiness.readiness()` and `systemctl --user is-enabled blueferry.service`. Returns only a bounded schema: configuration file present/absent, background service state, user-unit startup state, and existing MAP/PBAP *backend self-reports*. It never opens `local.env`, reads a Bluetooth address, starts/restarts a service, forces a reconnect, or grants access. File presence is an indicator of BlueFerry's configuration file, **not proof of a currently paired/connected iPhone**.
2. The existing **CONNECT PHONE** action now also requests this lifecycle check. DEVICE shows local configuration, whether the backend is active and whether its user unit starts with the session. It clearly distinguishes backend reports from the still-unverified Social link. No more buttons are required and DETAILS remains optional.
3. `PhoneNativeSetupLaunch.py` GUI clients are unchanged. In its CLI/terminal fallback, if `~/.config/blueferry/local.env` exists, it now launches the regular BlueFerry **TUI** (`blueferry tui`) instead of `blueferry pair-setup` and a destructive re-pair prompt. When the config file is absent, the existing explicit setup wizard remains available. When checking config fails, the **safer TUI** is selected rather than guessing that re-pair is necessary. These are direct literal argv commands, no shell. The staged foot terminal and its exact app-id still work.
4. When the staged terminal visibly exits, PHONE transitions to a finished state and refreshes saved-bridge status instead of waiting until a timeout and reporting stage failure. Closing setup explicitly also refreshes the local status. This inspection is **not** a connection authorization or write to BlueFerry.
5. The contextual iPhone action label becomes **OPEN IPHONE** when a local BlueFerry configuration file exists; otherwise **SET UP IPHONE**. The original single CONNECT PHONE is unchanged. Android uses its prior provider path.

## HOW TO USE

After reviewed merge and authorized deployment, **Social → PHONE → CONNECT PHONE** reads both the provider observation and the saved BlueFerry lifecycle. If the config file exists, choose **OPEN IPHONE** to reach BlueFerry's existing client and connection/reconnect UI; **do not run the pairing wizard again simply to repair a service or Social status**. When it closes, the saved-configuration/service report refreshes. If the service is inactive, the report explains that re-pairing is not the solution; the host service's startup and BlueFerry diagnostics should be inspected independently by the authorized desktop operator.

If a read-only status is needed from an operator terminal, **without changing the system**:

```bash
systemctl --user is-active blueferry.service
systemctl --user is-enabled blueferry.service
blueferry doctor
blueferry audio
blueferry calls
```

These may report device identifiers or other operational diagnostics in the terminal; **never paste full private output into a public GitHub issue** without redacting it.

## CALLS ONLY / AUDIO ROUTING (SEPARATE HOST OWNER DECISION)

BlueFerry's documented controls already separate:
- **A2DP media and ordinary phone playback:** `blueferry audio phone` selects the iPhone speaker, remembers this choice per phone in BlueFerry's `settings.json`, and does not change hands-free calling. `blueferry audio auto` reverses the explicit remembered route.
- **HFP phone calls:** `blueferry calls enable` opts in to experimental oFono call control. The preference is saved and requires oFono running, appropriate system D-Bus access, WirePlumber's HFP backend set to oFono, and Bluetooth HFP availability. It may entail WirePlumber rule changes and service restarts. `blueferry calls disable` turns it off.

Together, after prerequisites are verified and operator authorizes that host change, these can approximate **calls to computer, other iPhone audio to phone** without parsing each sound sample. Do not claim that every notification tone is guaranteed to follow a distinct stream. This P7 milestone deliberately does **not** execute these state-changing commands, install oFono, modify WirePlumber or add a premature Calls Only toggle. A future accepted audio-owner assignment should implement one small user-initiated switch with prerequisite diagnostics, clear failure/recovery states and actual call tests. Native BlueFerry HFP is experimental; FaceTime is not supported, and emergency calls belong on the phone.

Verified current upstream docs (2026-11-04):
- BlueFerry pairing and local state: https://github.com/erikwb/blueferry/blob/main/docs/en/user/pairing.md
- User service with `ConditionPathExists`: https://github.com/erikwb/blueferry/blob/main/systemd/blueferry.service
- Phone A2DP media routing: https://github.com/erikwb/blueferry/blob/main/docs/en/user/phone-audio.md
- oFono/HFP calls setup: https://github.com/erikwb/blueferry/blob/main/docs/en/user/calls.md
- Persistent Classic reconnect: https://github.com/erikwb/blueferry/blob/main/docs/en/user/reconnect.md

## VERIFY

- `tests/phone/test_phone_saved_bridge_state.py`: independent saved/backend/startup states, backend reports versus unverified Social link, strict/empty outputs, no private data or writes.
- `tests/phone/test_phone_native_setup_launch.py`: configured CLI opens TUI, unconfigured launches wizard, unknown config state avoids forced pairing, GUI precedence and foot staging preserved.
- `tests/messaging/test_social_phone_saved_lifecycle.py`: single primary action, conditional OPEN IPHONE, saved-state information, read-only result checks and stage-exit refresh.
- Existing setup and Stage Director regressions remain in `.github/workflows/social-phone-one-action-setup.yml`.

CI does not see the actual user's `local.env`, user service state, BlueFerry connection, oFono/WirePlumber or phone. No live BlueFerry data or system files were inspected or changed by this worker.

## WATCH OUT FOR

- An existing `local.env` can coexist with a stopped or disabled backend. Conversely, a configured Bluetooth bond may exist with missing/incomplete BlueFerry config. These are not equivalent to a Social connection.
- BlueFerry's own setup says its backend automatically starts after successful pairing and reconnects on normal interruptions. Until the live `systemctl`/doctor state is observed, **do not assert why it is not currently connected**.
- Social's actual protected SMS/iMessage/contact pipeline still requires Gate A identity/device/line authorization and independent host acceptance. A reported MAP/PBAP boolean does not prove the person or permission.
- Configured BlueFerry TUI offers a safe normal client; it is not an automatic reconnect trigger. It can expose existing phone data inside its own native terminal, so only use it after the user selects OPEN IPHONE, not on menu opening.
- Calls-only audio is a **requested design** but is not yet activated. This is an OS audio-service integration with separate oFono/WirePlumber ownership. Unverified prerequisites should not result in a switch that promises working calls.
- No local machine modification, service enable/restart, Bluetooth forget, new saved identity database, full message synchronization, merge or production activation by this worker.

## CHECKLIST

- [x] Read current Syntagma rules, reconstruct merged P6 and current GitHub main/open PRs.
- [x] Verify upstream BlueFerry owns its configuration, daemon session and independent call/media routes.
- [x] Add read-only local saved-bridge and user-service startup observations.
- [x] Use regular TUI instead of re-pair wizard when BlueFerry config exists.
- [x] Refresh local status after staged client exits while preserving verified-only cutout.
- [x] Maintain one Connect Phone action and no new device database.
- [x] Record calls-only audio prerequisites and defer live host changes.
- [x] Add synthetic/status-source tests and CI workflow.
- [ ] Exact-head CI and mergeability.
- [ ] Operator/Phone owner review and separate merge authorization.
- [ ] Authorized Fedora runtime check of BlueFerry configuration, service, iPhone Classic/MAP/PBAP status and Stage lifecycle.
- [ ] Cross-owner oFono/WirePlumber calls-only controls and real call/notification test.
- [ ] Identity/Phone Bridge Gate A accepted actual Social message/contact integration.
- [ ] Final operator acceptance.

## NEXT

Review CI and safely deploy only when authorized. In live Fedora, check BlueFerry service startup and phone connection **without forgetting the configured iPhone**; correct only the verified missing dependency under operator approval. Then implement the optional single Calls Only audio choice with the audio owner, after verifying oFono and WirePlumber prerequisites. Continue authenticated Social phone content transport independently.

## DECISIONS

BlueFerry remains the owner of saved pairing and media-route preferences. Social shows the saved lifecycle but stores no duplicate phone identity. Existing configured phones open the normal client, not the initial pairing wizard. Phone audio modes must be separated at Bluetooth profile/service level, not sampled and filtered by each notification sound. Protected Social data and production permissions remain under their current owners. Final DONE belongs to operator acceptance.
