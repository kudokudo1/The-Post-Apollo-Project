# Social PHONE P8a // Calls on PC should always respond to a click

> **STATE //** GitHub repository bugfix candidate, no live Fedora changes.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **ROOM //** Social Phone Bridge continuation / audio controls
>
> **STAFF //** External Hospital-compatible DOC; live Room attachment not verified.

## OBSERVED

Operator screenshot on 2026-11-04: PHONE DEVICE shows an active BlueFerry media route with **CALLS ON PC: OFF**. The control appears but cannot be clicked; the nearby copy says oFono is not ready.

Technical cause: the PHONE `ActionButton.interactive` expression required `ofonoActive === true` or `callsEnabled === true` as well as known call status. Missing oFono disabled the button **before** its existing `onTriggered` handler could report `CALLS_PREREQUISITES_MISSING`. The standard `ActionButton` does not emit `triggered` while noninteractive.

## IMPLEMENTATION

Keep **CALLS ON PC** interactive except while a phone-audio request is in progress or the Stage Director setup terminal occupies the bay. On click:
- Active BlueFerry/call status and oFono ready: retain the existing, explicitly user-triggered call preference mutation through `PhoneAudioControls.py`.
- oFono not active: show a concrete inline missing-hands-free-service message. **No call preference or media route is changed.**
- BlueFerry doesn't report a supported `callsEnabled` boolean: show a separate unsupported-provider message; no mutation.
- Audio state unavailable: show a status-unavailable message; no mutation.

The `changePhoneAudio` handler checks the backend state and only runs an actual host action after it has the required data. The backend still refuses call enable without oFono and verifies the saved provider preference. Media IPHONE / COMPUTER / AUTO controls are unchanged. No new menu, permissions prompt, login or terminal command is introduced.

## HOW TO USE

After review, merge and authorized runtime deployment, open **Social → PHONE → CONNECT PHONE → DEVICE** and click **CALLS ON PC: OFF**. If oFono isn't ready, the button now explains why rather than acting dead. Once the host hands-free prerequisites are configured under the audio owner's separate authority, the same button can enable the call preference.

**Clickability is not equivalent to working HFP calling.** A working call still requires oFono, appropriate system D-Bus access, WirePlumber HFP ownership and compatible BlueZ configuration. Do not silently install or restart those services.

## VERIFY

The existing `tests/messaging/test_social_phone_audio_controls.py` now checks that the actual Calls button does not disable itself on oFono, unknown call support or an unavailable readiness state, and that the handler still fails closed with meaningful feedback. Existing `tests/phone/test_phone_audio_controls.py` covers rejection of an oFono-less enable action before any host mutation. The existing Social PHONE workflow covers both files.

No live phone, Bluetooth, Sway, oFono or WirePlumber action was performed by this branch.

## WATCH OUT FOR

This patch fixes user interaction, **not** missing oFono/HFP host support. The actual operator desktop presently reports oFono unavailable via the menu. Do not infer that the provider's call feature can be enabled or that incoming-call audio works. The preview does not alter pairing, message/contact scopes, audio routing or default settings for other Post-Apollo users.

## CHECKLIST

- [x] Recheck current main, merged P8 PR #1278, no colliding PHONE/Social PR.
- [x] Inspect the screenshot, PHONE's action guard, and `ActionButton` event semantics.
- [x] Make call control clickable while preserving fail-closed backend action.
- [x] Distinguish missing oFono, unsupported calls, and unavailable status in-menu.
- [x] Add regression test for screenshot's exact disabled-button cause.
- [ ] Verify exact-head CI and PR mergeability.
- [ ] Operator/shared Social owner review and merge authorization.
- [ ] Authorized live click/feedback test and separately scoped HFP prerequisites.
- [ ] Final operator acceptance.

## NEXT

Review this bounded PR and its CI, then test the click on the real PHONE menu. If it shows oFono missing, open a separate OS-audio-owner task to configure hands-free prerequisites through an approved UI-driven workflow. Do not treat the diagnostic fix as a call-service installation.

## DECISIONS

Only a user-requested click can attempt a call preference change. The same button must explain why it cannot perform a change instead of disappearing or going inert. The operator remains final authority; no local machine changes, system service activation or PR merge by this worker. Recovery is closing the draft PR or reverting the bounded QML/test change if merged later.
