# Social PHONE // Cross-provider observation projection P2 v0

> **STATE //** REPOSITORY-ONLY REVIEW CANDIDATE. No actual trusted phone link, authenticated device, message/contacts permission, or live operator acceptance.
>
> **PATIENT //** kudokudo1/The-Post-Apollo-Project
>
> **SCOPE //** Pure fail-closed provider status projector, offline tests, and dedicated CI. Existing Phone probes, Social QML, Identity Center, Account Broker, messaging router, Bluetooth services, and Fedora files are unchanged.
>
> **OWNERSHIP //** Isolated Phone Bridge read-only observation lane. Identity/security Gate A, device/line authority, and shared Social UI changes remain with their owners.

## Mechanism

The new services/phone/PhoneProviderObservation.py function project(blueferry, kdeconnect) performs NO provider query. It accepts only the exact-schema, already-redacted outputs of existing BlueFerryReadiness.py and the opt-in KdeConnectDbusProbe.py and returns a diagnostic-only combined view.

- BLUEFERRY: Bounded MAP/PBAP *backend self-report* states, never a verified device, authorization, SMS/iMessage distinction, HFP, or FaceTime connection.
- KDECONNECT: Bounded paired/reachable device and locally loaded SMS/Contacts/Telephony plugin counts only. KDE Connect also supports iOS, so Android platform remains UNVERIFIED. Local plugins do not prove mobile permissions.
- Malformed fields, unexpected private data, invalid counts, and forged permission/transport/identity assertions cause ONLY that provider to become UNAVAILABLE. No inputs are echoed to output.
- All results contain trustedPhoneLink=UNVERIFIED, person/device/line/organization bindings=UNVERIFIED, routeEligible=false and contentAccessEnabled=false. Provider activity cannot grant permissions.

The projector does not start BlueFerry or KDE Connect, trigger D-Bus, read phone content, poll, send SMS, or change any phone/host state. It is not called from live Social yet. **Opening Social must not silently launch the KDE diagnostic**, which remains separately opt-in.

## Trust boundary

The existing TrustedPhoneGrantFixture.py and SerializedPhoneHostFixture.py are in-memory synthetic models, not a privileged authorization or revocation service. These observations can be forged by any local caller and MUST NEVER be promoted to CapabilityPolicy authorization=VERIFIED or interpreted as permissions.

The upstream Identity Center trusted-host integration handoff remains decisive: [social-phone-identity-host-integration-handoff-p1-v0.md](./social-phone-identity-host-integration-handoff-p1-v0.md).

Gate A requires owner/operator approval of authenticated session, trusted device + phone-line binding, per-operation consent, independent personal and organization grants, host process/IPC isolation, same-UID D-Bus threat model, protected content projections, and authoritative revoke-before-release ordering.

## Offline verification

Run the new synthetic checks and regression coverage:

    python3 -m unittest discover -s tests/phone -p 'test_phone_provider_observation.py' -v
    python3 -m unittest discover -s tests/phone -p 'test_blueferry_readiness.py' -v
    python3 -m unittest discover -s tests/phone -p 'test_kdeconnect_dbus_probe.py' -v

GitHub CI: .github/workflows/social-phone-provider-observation.yml. Fixture data only; no phone, live session, Quickshell rendering, or real Bluetooth endpoint verified.

## Continuity and recovery

This is a bounded step toward a unified PHONE connection status, NOT the trusted connection manager itself. The safe follow-up is a Gate A owner decision, then disposable separate-process host validation and later separately authorized device and Social UI acceptance. Android LAN and iPhone Bluetooth remain separate platform/provider paths. Bluetooth fallback remains opt-in per capability. No production activation, local machine modification, message read/send, contact sync, or PR merge is part of this change.

Review the draft PR and CI before acceptance. Close the draft branch or revert its merge commit if later landed; there is no local-host rollback. Operator retains final DONE.
