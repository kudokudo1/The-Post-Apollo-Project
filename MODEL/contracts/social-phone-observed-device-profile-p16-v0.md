# Social PHONE P16 // Observed active iPhone profile and Bluetooth name

**STATUS:** GitHub-only bounded implementation. Live Fedora/BlueFerry version, PHONE rendering and user acceptance unverified.

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`
**ROOM:** Social Phone Bridge continuation, device identity milestone P16 (Hospital-compatible, no verified live Room/Assignment).
**STAFF:** External DOC-compatible ChatGPT worker, limited to PHONE read-only observation and its tests; not a registered live Hospital staff assignment.
**BASE:** Main was rechecked at `1c1d05db5654720cd11431005fe49f550f9c66de` with no open PHONE colliding PR.

## IMPLEMENTATION

The existing **CONNECT PHONE** action now also invokes `services/phone/PhoneDeviceObservation.py --inspect` for the current BlueFerry profile. This is a read-only, content-free *device observation*, not a connection or permission grant.

1. Obtain the opaque UUIDv4 `phone_profile_id` from the *already-running* BlueFerry daemon via its unique D-Bus owner, require expected API v2 and typed booleans.
2. Read only the matching private owner-only BlueFerry configuration's UUID + MAC *inside* the helper. No MAC, configuration value, BlueZ object path or raw D-Bus payload crosses into PHONE.
3. Match that configured address to BlueZ `org.bluez.Device1` on the already-running system bus and read its paired/connected booleans and bounded `Alias`. Only this exact pairing yields a human-friendly device name. Return observed Bluetooth status separately from unverified Social content access.
4. Present `IPHONE // <device name>` with an accurate *Bluetooth device* state, including paired/offline and profile-only fallbacks. Keep the existing PHONE controls, Stage Director, BlueFerry setup, messages/contact placeholders and per-phone audio preferences untouched.
5. Refresh on the same Connect Phone action and after staged setup exits. Clear stale observations when PHONE is reopened.

The design intentionally uses BlueFerry's provider-owned **opaque profile ID**, rather than a raw Bluetooth address or local Social identity label. BlueFerry upstream `src/blueferry/daemon.py` exposes the ID in `GetStatus` and `config.py` defines its UUIDv4 format. No new phone registry or signed account/device ownership is inferred.

## HOW TO USE

After operator merge and separately authorized deployment: Social → PHONE → CONNECT PHONE → DEVICE. PHONE will show the configured iPhone's Bluetooth alias if the backend profile, private configuration, and BlueZ paired device all match; otherwise it reports a clearly limited state. Existing "OPEN IPHONE" and CALLS ON PC flows remain unchanged.

## VERIFY

- New offline `tests/phone/test_phone_device_observation.py` simulates matched/incorrect profiles, paired vs connected devices, unsupported backend shapes, invalid aliases and fail-closed behavior.
- New `tests/messaging/test_social_phone_device_observation.py` checks only the intended CONNECT PHONE wiring, QML output validation, plain-text name display and unchanged locked chat.
- The existing PHONE workflow compiles and executes both tests alongside prior suites.
- CI, real BlueZ/BlueFerry bus observations and actual Quickshell rendering remain separate evidence gates.

## WATCH OUT FOR

The user's physical iPhone audio works according to operator report, but a physical Bluetooth link is not a Social message/contact authorization, a verified caller/device account binding or HFP readiness. Never display `CONNECTED` as Social data ready. The helper does not read contacts/messages, write pairing configuration, start services, enable Bluetooth or change audio. Upstream BlueFerry's GetStatus may itself migrate legacy profile identifiers, which is provider-owned behavior and outside this helper's control.

Some BlueFerry builds may not report `phone_profile_id`; then the observation fails closed instead of guessing. A human-readable BlueZ Alias is **not proof of phone ownership or user/organization membership**.

## CHECKLIST

- [x] Recheck Syntagma AGENTS, Hospital/working policies, main HEAD, current open PR ownership
- [x] Inspect BlueFerry's actual profile ID and source API
- [x] Build a read-only exact-profile/device name observer
- [x] Wire it into the existing one-button PHONE flow
- [x] Write offline and UI source tests
- [ ] Exact-head GitHub CI
- [ ] Operator review/merge
- [ ] Separately approved live Fedora/Quickshell verification

## NEXT

**P17:** If the operator accepts the observed-device display, add optional local-friendly labels and a scoped device chooser using BlueFerry's IDs, coordinating active-profile switching and native pairing with the provider. Do not imply two simultaneously active BlueFerry phones when upstream supports only a selected profile.

**Data bridge:** In parallel, get explicit Identity/Account Broker owner acceptance of the trusted host and revocation model before allowing BlueFerry `ListThreads`, `ListContacts`, or sends to populate Social. The existing PHONE chat stays intentionally disabled until that separate end-to-end permission/owner gate passes.

**oFono:** Continue the separately scoped interactive Fedora installer and later HFP/PC audio verification. Do not change existing working A2DP routing as part of this PR.

## DECISIONS

One visible PHONE workspace and one primary connect action, provider-specific identity under a neutral display, network-first per capability, no automatic pairing, no raw MAC in QML, no duplicate phone database, no false data-access claim. No local machine modifications, merges or activation under this assignment. Close draft PR to abandon; revert only its bounded commit if merged later. Operator owns final acceptance.
