# Social PHONE P8b // Explain oFono readiness inside Calls on PC

> **STATE //** Repository-only review candidate. This is a **read-only diagnostic**, not an oFono installation or HFP enablement.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation; external Hospital-compatible DOC, not live registered.
> **SOURCE //** Operator acknowledged the proposal on 2026-11-04 to explain why oFono was not ready using PHONE controls, not terminal instructions. Earlier Calls button fix PR #1283 is merged.

## IMPLEMENTATION

`PhoneCallPrerequisites.py` checks only three existing host facts **after a real click** on an unavailable Calls on PC setting: `rpm -q` oFono package presence, `systemctl show` unit load/active states, and (if running) an optional `org.ofono` system D-Bus name-owner check. All arguments are fixed, no shell, no DBus activation or provider RPC, no local writes. Its entire output is a strict small enum/boolean report, never the actual host output, identifiers, phone data, logs or private errors.

`PhonePane.qml` retains one Calls on PC button. Its unsupported/available branches and existing `PhoneAudioControls.py` action remain intact. When enabling is blocked because the previously observed oFonoActive was false, clicking the same button triggers this diagnostic, then shows a specific explanation: absent package/service, stopped/failed/masked/starting service, missing system D-Bus owner, or running oFono with HFP/WirePlumber still unverified. The result explicitly does **not** assert a working call path.

No install/repair button, login, terminal instructions, new phone store, pairing reset, global default, or production phone access is introduced.

## HOW TO USE

After authorized merge and deployment: **Social → PHONE → CONNECT PHONE → DEVICE → CALLS ON PC**. If the system reports unavailable hands-free calling, click the existing Calls control. The text below it explains the observed prerequisite. A future system-audio owner may implement an approved in-menu setup action, but this PR does not activate services.

## VERIFY

The dedicated PHONE workflow now compiles `PhoneCallPrerequisites.py` and runs `test_phone_call_prerequisites.py` plus existing UI and backend tests. Synthetic cases cover package absent versus unit missing, stopped/failed/masked states, active unit with/without D-Bus, no auto-run, redacted outputs, exact read-only commands, and a fail-closed HFP verification statement. Existing UI tests check the same on-click path, no extra button, and unchanged media controls.

Actual operator Fedora package, service, DBus, HFP, WirePlumber and phone state remain uninspected. A CI success will prove only code/fixture behavior, not actual call readiness.

## WATCH OUT FOR

`rpm -q` is Fedora-specific; absence of an rpm query is **UNKNOWN**, never proof of an absent package. A missing service unit is not always proof the package is uninstalled. System D-Bus name presence also does not establish working HFP microphone/speaker routing. `hfpVerified=false` means this diagnostic has **not independently verified** HFP, rather than conclusively declaring the real device incapable of calling.

The existing backend call-enable guard still blocks mutation when oFono is inactive; no service startup, package install, WirePlumber modification, Bluetooth re-pairing, protected content read, or merge is performed in this work.

## CHECKLIST

- [x] Recheck Syntagma rules, current GitHub main, merged PR #1283 and open owner conflicts
- [x] Inspect current Calls guard and BlueFerry local service logic
- [x] Add explicit read-only oFono package/unit/bus diagnosis
- [x] Display meaningful outcomes from the same Calls button
- [x] Add synthetic and QML-source regression tests; extend workflow
- [ ] Verify exact-head CI, PR diff and mergeability
- [ ] Social/Phone and OS audio owner review, operator merge approval
- [ ] Authorized live Fedora click test and actual HFP verification
- [ ] Final operator acceptance

## NEXT

Review the draft and CI, then test the same Calls button on Fedora after authorized deployment. If oFono is genuinely absent/stopped, obtain a separate approved audio-owner host setup; do not silently install or restart services. Then verify WirePlumber/BlueZ HFP with a normal non-emergency call.

## DECISIONS

Keep the menu-first interaction and no default device/audio configuration for other users. The diagnostic is read-only and user-initiated; actual system changes remain operator-approved and owner-scoped. Recovery is closing this draft or reverting its bounded commits if merged. GitHub is technical source of truth and Hospital final acceptance remains with the operator.
