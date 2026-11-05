# Social PHONE P10 // Post-install call readiness stays in the existing menu

> **STATE //** Repository review candidate, not live Fedora/HFP verification.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation, P10 post-install UX
> **STAFF //** External Hospital-compatible DOC, not verified live-registered.
> **OPERATOR CONTINUITY //** 2026-11-04 "continue" after P9's native Fedora oFono setup handoff. Prior PR #1292 was verified merged to `main`.

## IMPLEMENTATION

The merged P9 GUI handoff had a lifecycle gap: after an oFono installation, pressing **CHECK AGAIN** changes the diagnostic away from `PACKAGE_NOT_INSTALLED`, and the *only* contextual button disappeared. This left the user without a way to recheck whether the oFono service, BlueFerry call control, and HFP connection progressed. The prior UI also showed generic "HFP status" values.

This change is restricted to `PhonePane.qml`, its existing tests, and a durable contract:

1. **One persistent control, not another menu:** `SET UP CALLING` appears only while oFono is verified absent. After a native graphical-installer request it becomes `CHECK AGAIN`. After any successful package-status transition, the **same** control remains `CHECK AGAIN` for service/call-status follow-up; if the package still isn't installed it becomes `RETRY SETUP`. No second setup button or new permission screen.
2. **Read-only recheck only:** Subsequent CHECK AGAIN calls existing `PhoneCallPrerequisites.py --check` and `PhoneAudioControls.py --status`. No package install, user service restart, WirePlumber changes or Bluetooth actions. The user still explicitly clicks the separate **CALLS ON PC** control to request BlueFerry's call preference.
3. **Explain the actual backend state in one line:** `SERVICE_STOPPED`, `SERVICE_FAILED`, `SERVICE_MASKED`, `DBUS_NAME_MISSING` and other existing prerequisites remain distinguishable. If oFono is active and BlueFerry can be read, the UI reports when calls are OFF, `SEARCHING`, `CONNECTING`, `BLUEZ_CONFLICT`, or `READY`. BlueFerry's `READY` is only a provider report of hands-free *call control*, not proof that speaker and microphone audio work. A real non-emergency call is required to verify that.
4. **Correct contextual copy:** Native Fedora package-manager approval text only appears during missing-package setup, not during subsequent service/HFP checks. No permanent warning rail or terminal steps.

The diagnosis uses existing bounded outputs from BlueFerry and oFono. No new host probe or private phone content collection.

## HOW TO USE

After reviewed/merged and separately deployed: **Social → PHONE → CONNECT PHONE → DEVICE → CALLS ON PC**. If oFono is absent, **SET UP CALLING** requests the native Fedora software installer. After user-approved installation, press **CHECK AGAIN** at the same spot. PHONE continues reporting whether oFono is stopped, D-Bus inaccessible, the iPhone HFP link searching/connecting, BlueZ in conflict, or the BlueFerry backend reports call control ready. Rechecking never enables calling by itself. Where hands-free support is verified by the owning host team, the separate **CALLS ON PC** toggle requests the saved user preference.

## VERIFY

- Extended `tests/messaging/test_social_phone_calling_setup.py` checks that Check Again stays visible after the package is no longer missing, invokes only existing read-only probes, uses Retry Setup if installation remains absent, and keeps one primary Connect Phone and one contextual calling setup action.
- Tests assert explicit states for stopped/failed services and searching/connecting/ready/BlueZ-conflict provider reports, without making a host mutation or claiming live microphone/audio verification.
- The existing `.github/workflows/social-phone-one-action-setup.yml` picks up changes to the existing PHONE UI and tests, alongside all prior launcher/Stage/call controls.

CI is synthetic and source-based. No actual Fedora software manager, oFono, WirePlumber, BlueZ, BlueFerry session, iPhone call or audio device was inspected or changed in this work.

## WATCH OUT FOR

- This milestone **does not** start a stopped oFono service, install packages, configure system D-Bus policy, switch WirePlumber's HFP backend, or disable a conflicting BlueZ HFP plugin. Those alter live host system state and belong to the OS audio owner after explicit operator/user approval.
- `READY` is BlueFerry's status, not independent HFP hardware proof. A test call with microphone/speaker feedback is required for final acceptance. Emergency calls stay on the iPhone.
- A user may still lack a graphical Fedora package manager; the previously merged P9 conditional GUI handoff reports this rather than silently installing via terminal.
- Local BlueFerry paired-phone configuration and per-user audio choices are not bundled into Post-Apollo defaults or a second device database.
- Shared Social routing, Identity Center, Account Broker and Weather Station Stage Director are unchanged. Real SMS/iMessage/contacts integration remains a separate Gate A authorization/owner task.
- If a dependency cannot be verified, the menu explains the limitation; it does not claim a connected phone or make a speculative fix.

## CHECKLIST

- [x] Recheck current `main`, merged P9, Syntagma AGENTS/Hospital protocols and concurrent PR ownership.
- [x] Review current BlueFerry upstream HFP state and calls prerequisites.
- [x] Preserve the in-menu Check Again control beyond package installation.
- [x] Translate existing read-only oFono and BlueFerry states to honest explanations.
- [x] Keep one contextual setup control and separate explicit Calls on PC toggle.
- [x] Extend tests and index recovery contract.
- [ ] Verify exact PR-head CI and mergeability.
- [ ] Phone/Social and OS audio owner review plus operator-authorized merge.
- [ ] Authorized live Fedora package/service, BlueFerry/HFP, actual call and UI visual verification.
- [ ] Final operator acceptance.

## NEXT

Review CI and merge only with required authorization. After deployed, test the same-button CHECK AGAIN following native package approval. For any persistent stopped oFono, D-Bus issue, BlueZ HFP conflict, or WirePlumber routing mismatch, coordinate a separately scoped, opt-in host setup with the audio owner instead of silently running privileged commands. Verify actual call control and audio independently.

## DECISIONS

Keep users inside Social PHONE. The existing contextual calling setup button and Calls on PC toggle suffice; no extra settings dashboard. BlueFerry remains owner of phone/audio preferences; production phone content access remains under its separate trust boundary. This work is a GitHub-only draft implementation, not a local host mutation, merge, or live Hospital registration. Recovery is closing the PR or reverting bounded changes after later authorized merge. Final DONE belongs to the operator.
