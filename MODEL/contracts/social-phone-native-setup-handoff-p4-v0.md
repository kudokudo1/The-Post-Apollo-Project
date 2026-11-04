# Social PHONE // User-Initiated Native Setup Handoff P4 v0

> **STATE //** REVIEW CANDIDATE. Implements a real user-initiated request to open an **installed phone provider's own pairing UI**, NOT a full Post-Apollo phone link. No OS service configuration, pairing transaction, phone content, credentials, or authenticated Social grant is performed by this patch.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **ROOM / ASSIGNMENT //** Social Phone Bridge continuation / simple one-action setup. External Hospital-compatible DOC, not verified as a registered live Room or Session.
>
> **DECISION //** Preserve [operator-selected minimal setup](./social-phone-simple-onboarding-gatea-v0.md): one primary CONNECT PHONE action; a platform choice only where needed; native phone-side consent; no Post-Apollo security dashboard.

## IMPLEMENTATION

`Social → PHONE → DEVICE → CONNECT PHONE` still performs the existing **explicit, read-only** BlueFerry/KDE Connect check. After that action, and only while the DEVICE section is open, two compact choices appear: **SET UP IPHONE** and **SET UP ANDROID**. Both reuse the same PHONE pane and hide technical status under DETAILS. No second permanent Post-Apollo page is introduced.

The new `services/phone/PhoneNativeSetupLaunch.py` is a one-shot **allowlisted external GUI launcher**, invoked only on a selected platform, using an exact `--open iphone|android` argument. It checks installed executable paths and launches:
- iPhone: installed `blueferry-gtk`, or `blueferry-qt` as fallback (including when launching the first fails). Both are BlueFerry's existing graphical pairing clients.
- Android: installed `kdeconnect-app`, KDE Connect's existing pairing application on Fedora.

The launcher uses a fixed argv with **no shell, identifiers, phone numbers, passwords, provider commands, installed packages or configuration changes**. The launched native client and the phone remain responsible for their own pairing/code confirmation and permission prompts. A native GUI process may launch its own backend by design after the user explicitly requests it; we do **not** activate that backend on menu open. A missing or failing client gives a sanitized error in the pane, not an install/reset command.

The helper's `OPEN_REQUESTED` means only that a process was started, not that a window appeared or a phone was connected. Its result always keeps `trustedPhoneLink=UNVERIFIED`, `routeEligible=false` and `contentAccessEnabled=false`. The Social message/contact/call integrations remain locked until a separately owned and verified backend is implemented. The last code change in this PR does not pair any real phone itself.

## HOW TO USE

**After separately approved merge and deployment:**

1. In Social, open PHONE → DEVICE and press CONNECT PHONE to check the existing setup.
2. If pairing is needed, choose SET UP IPHONE or SET UP ANDROID. The installed native setup app is requested. Follow its ordinary device pairing approval on the phone. If your phone is already paired, you may not need to repeat pairing.
3. Return to PHONE → DEVICE and press CONNECT PHONE again to refresh provider status.

If a native setup client is missing, Social shows a concise unavailable state and makes no changes. Do not add more mandatory Post-Apollo password/permission screens to fix this; a setup app installation is a separately approved local-machine operation.

**This does not yet bring iMessage/SMS/contacts into Social.** BlueFerry and KDE Connect are third-party/native clients and may implement these features themselves, but Social still lacks the authorized content bridge.

## VERIFY

```bash
python3 -m unittest discover -s tests/phone -p 'test_phone_native_setup_launch.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_social_phone_native_setup_handoff.py' -v
python3 -m unittest discover -s tests/phone -p 'test_phone_setup_readiness.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_social_phone_connect_flow.py' -v
python3 -m unittest discover -s tests/messaging -p 'test_social_phone_menu_readonly.py' -v
```

The existing `.github/workflows/social-phone-one-action-setup.yml` is extended to test the new helper and UI contract. Other PHONE regressions remain in their existing workflows. Unit tests use injected fake launcher callbacks; **no CI test launches a real GUI, BlueFerry, KDE Connect, Bluetooth or a phone.**

Upstream provider references, checked 2026-11-04:
- BlueFerry pairing/GUI clients: https://github.com/erikwb/blueferry
- KDE Connect pairing via its own app: https://userbase.kde.org/KDEConnect/en
- Fedora KDE Connect package file list (kdeconnect-app): https://packages.fedoraproject.org/pkgs/kde-connect/kde-connect/fedora-45.html

## WATCH OUT FOR

- This is a **native GUI handoff**, not embedded pairing or a verified Post-Apollo phone session. It does not bypass OS consent. BlueFerry/KDE Connect can themselves access content according to the phone-side grants; this patch does not expose their content to Social.
- It temporarily opens a native provider app for pairing. That is not another permanent Social window. A future owned integration can embed a provider setup protocol when supported and security-reviewed.
- The currently reported BlueFerry MAP/PBAP states and KDE plugin counts are non-authoritative. Do not turn them into verified person/device/line or organization rights.
- Local machine mutation, service activation, installing missing clients, phone permission changes, and runtime Quickshell deployment were **not done** by this worker. The user explicitly choosing SET UP IPHONE/ANDROID later is the only path that requests opening the native app.
- When both clients are installed, the user chooses the phone platform once. Android/iPhone support remains capability-specific; do not infer FaceTime, carrier call control or full iMessage history from pairing.
- Gate A still requires Identity Center/security and Account Broker approval of a trusted host/phone-line/organization-grant boundary before Social can receive protected content. Personal/LLC/nonprofit information cannot inherit permissions from a local label.
- Quickshell geometry/focus and actual native window opening on the Fedora machine are unverified until approved runtime inspection.

## CHECKLIST

- [x] Reconstruct current main, earlier P3 Phone entry and no colliding open PHONE PR.
- [x] Implement fixed allowlisted native setup client launcher and sanitized output.
- [x] Wire only two contextual platform choices after CONNECT PHONE, preserving the existing Social pane.
- [x] Add fail-closed and UI-source tests, extend CI.
- [ ] Check exact-head CI and mergeability.
- [ ] Integration-owner/operator review and separately authorized merge.
- [ ] Test installed desktop clients and phone prompt behavior in live Fedora.
- [ ] Identity/Phone Bridge owner Gate A and actual scoped Social content pipeline.
- [ ] Final operator acceptance.

## NEXT

After reviewing this bounded PR, verify native pairing in the live desktop and coordinate the actual Phone Bridge host and content projection with the owning Identity/Account teams. Keep one user-visible connection flow with normal phone prompts, not a new security-control panel.

## DECISIONS

Operator-selected architecture stays **network-first by capability, explicit Bluetooth fallback**, with distinct iPhone/Android providers, one Social workspace and minimally visible permissions. No automatic pairing, service restart, local install, real-message access, organization grant, merge or production activation authorized by this implementation. For recovery, close the draft or revert its merged commit if later accepted; no host rollback is required from the GitHub changes.
