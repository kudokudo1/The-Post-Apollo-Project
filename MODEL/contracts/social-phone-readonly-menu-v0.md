# Social PHONE // Read-only widget entry and BlueFerry readiness v0

> **STATE //** REVIEW CANDIDATE, NOT ACTIVATED OR OPERATOR-ACCEPTED.
> **PATIENT //** kudokudo1/The-Post-Apollo-Project
> **SOURCE //** Operator request 2026-11-04 after BlueFerry v0.9.1 Linux pairing and observed iPhone call audio on Fedora Silverblue.
> **SCOPE //** New PHONE button, companion pane within existing Social window, read-only local backend/service readiness. No paired-phone content access, message/contacts/call bridge, account/link writes or local runtime changes.
> **OWNERSHIP //** Social selector/controller is a shared integration seam, proposed changes are in an isolated draft PR pending integration-owner review. Identity Center and messaging router are unchanged.
> **RELATED //** [network-first architecture](social-phone-bridge-network-first-adr-v0.md) and [capability policy](social-phone-capability-policy-v0.md).

## Mechanism

- The existing AppSelector gains an always-visible PHONE footer above USER // SETTINGS. It is not a new service index or account/family row.
- PHONE opens PhonePane in the existing Social FloatingWindow's contact/chat workspace. It closes on provider switch, Escape or Social close, and is exclusive with USER // SETTINGS.
- A manual REFRESH READINESS button and initial pane opening run a local Python probe using **only** rpm -q, systemctl is-active and bluetoothctl show, plus a local.env existence check. The probe never reads its contents or emits Bluetooth MACs, names, credentials, messages, contacts, phone numbers or content.
- The pane shows DEVICE, CALLS, MESSAGES, CONTACTS and PERMISSIONS. Only DEVICE provides a diagnostic action. All other sections are truthful placeholders, not controls that touch phone content. BlueFerry backend service active does **not** prove the phone link, which stays UNVERIFIED.
- The QML schema gate refuses other probe modes and any reported content authorization. No background polling when closed, no user-service auto-start, and no automatic fallback route selection.

## Verification and rollout

Run offline from the repository root:

```bash
python3 -m unittest discover -s tests/phone -p 'test_blueferry_readiness.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_social_phone_menu_readonly.py' -v
```

A GitHub Actions workflow runs those tests for the PR. QML runtime and actual visual behavior still need deliberate operator review in a disposable or approved test runtime. **Do not automatically reload Quickshell**, start BlueFerry, change Bluetooth permissions, import/sync content, or activate the PR on the user's host.

## Deferred work

- Permission-scoped real connection and per-profile probe for iPhone, without inferring MAP/PBAP/ANCS from HFP call audio.
- Trusted person/phone/line/organization grants from Identity Center or an approved authority; local Social identity-N labels are not grants.
- Actual calls/messaging/contacts via appropriately owned adapters and explicit per-capability opt-ins; retain network-first/opt-in Bluetooth fallback policy.
- Proper runtime/appearance acceptance and Social integration-owner coordination before merge.
