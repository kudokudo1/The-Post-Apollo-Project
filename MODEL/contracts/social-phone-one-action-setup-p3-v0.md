# Social PHONE // One-action setup entry P3 v0

> **STATE //** REPOSITORY FEATURE BRANCH / REVIEW CANDIDATE. The visible CONNECT PHONE action performs an explicit **read-only check**; it is NOT a live phone connection, pairing, consent, or access-grant flow. Operator acceptance and live Quickshell validation still pending.
>
> **PATIENT //** kudokudo1/The-Post-Apollo-Project
>
> **ROOM / ASSIGNMENT //** Social Phone Bridge continuation, first bounded Social PHONE setup entry and no activation. Browser worker: DOC, OPEN AI // CHATGPT, external Hospital-compatible, no verified Hospital registration.
>
> **UX DECISION SOURCE //** [One-step onboarding Gate A decision](./social-phone-simple-onboarding-gatea-v0.md), separate draft PR #1238 at implementation time. Do not treat a draft architectural document as a merged production grant service.

## IMPLEMENTATION

Inside the existing Social PHONE pane, **CONNECT PHONE** is now the obvious primary action. Only after that click, the UI invokes `python3 services/phone/PhoneSetupReadiness.py --check`. The script reads existing BlueFerry readiness and opt-in KDE Connect local metadata through the existing read-only probes and the merged fail-closed `PhoneProviderObservation.project` helper. It outputs only a strict, sanitized `post-apollo.phone.setup-check.v0` JSON result.

A bridge may be reported but the UI explicitly states that this **does not link a phone or enable messages, calls or contacts**. The actual sign-in, device identity, line and permission proofs do not exist yet. The resulting report always includes `trustedPhoneLink=UNVERIFIED`, `routeEligible=false` and `contentAccessEnabled=false`. An input/source failure is provider-local and redacted.

The UI removes the unused PERMISSIONS main tab to reduce clutter, retains device/calls/messages/contacts, hides old low-level readiness behind **DETAILS**, and requires explicit action before running even the KDE Connect diagnostic. Existing Social routing and window/component ownership remain untouched: AppSelector.qml, MessagingW.qml, identity services, message routing and account brokers were not changed.

## HOW TO USE

After an authorized merge and deployment (NOT performed here), select **Social -> PHONE -> DEVICE -> CONNECT PHONE**. The first-stage button checks already-running and already-paired provider readiness without requesting permission or changing a link. A concise provider status is displayed and the button can be pressed again to recheck. For technical diagnostics, open DETAILS and optionally REFRESH READINESS. The existing platform pairing/settings remain external. A future assigned integration must replace this diagnostic-only phase with a real OS-native guided connection.

No additional Post-Apollo password, security control panel or per-message approval has been introduced.

## VERIFY

Synthetic and static checks:

    python3 -m unittest discover -s tests/phone -p 'test_phone_setup_readiness.py' -v
    python3 -m unittest discover -s tests/messaging -p 'test_social_phone_connect_flow.py' -v
    python3 -m unittest discover -s tests/phone -p 'test_phone_provider_observation.py' -v
    python3 -m unittest discover -s tests/messaging -p 'test_social_phone_menu_readonly.py' -v

The dedicated workflow is `.github/workflows/social-phone-one-action-setup.yml`; the pre-existing phone menu workflow also executes for PhonePane edits. No real phone, Fedora runtime, focus/geometry, OS pairing or permission test has occurred in this branch. CI success is narrower than live acceptance.

## WATCH OUT FOR

- The currently visible button is a **setup diagnostic precursor**, not a functional phone pairing/authorization flow. The text tells the user this before they click.
- iPhone Bluetooth MAP/PBAP status is only BlueFerry's self-report; KDE plugin counts do not authenticate an Android phone, a SIM line or a permitted SMS route.
- Existing audio observed on Fedora is separate from Social call controls. FaceTime remains unsupported in this path.
- Identity Center Gate A and Account Broker device/line/organization ownership remain unresolved cross-owner work. Do NOT extend this branch into a real message subscriber, access-grant host, KDE pairing, Bluetooth config or shared Social router.
- Details text may need viewport/geometry adjustments during live Quickshell review. A draft build cannot certify visual correctness.
- If a user closes/reopens the pane while a previous check is running, stale output is ignored unless the pane is in its current CHECKING phase; no phone content is ever staged.
- No local machine changes, service changes or PR merge are performed by this work.

## CHECKLIST

- [x] Reacquire current main, PhonePane, Syntagma rules, shared ownership, and open PR collisions.
- [x] Keep one obvious Connect Phone action, no per-operation security UI, no auto-diagnostic on menu open.
- [x] Reuse read-only provider probes and strict redacting projector.
- [x] Preserve no content grants, phone auto-pairing or data exposure.
- [x] Add synthetic and QML-source regression checks and a dedicated workflow.
- [ ] Verify exact-head CI success and new PR mergeability.
- [ ] Owner/operator review and authorized merge.
- [ ] Runtime geometry and real phone acceptance after separately authorized deployment.
- [ ] Trusted host/device/line/organization Gate A acceptance and actual OS-native connect workflow.

## NEXT

Review the draft and obtain shared Social UI owner review. Assign Identity Center/security and Account Broker owners for the behind-the-scenes signed session, verified device/line, grant and revocation boundary. After those gates, implement one actual CONNECT PHONE connection flow without additional user-visible authentication theater; verify with one authorized iPhone and Android device.

## DECISIONS

Operator-selected UX: single primary action, minimal prompts, diagnostics collapsed, existing Social window, network-first when capability proves available, Bluetooth only with actual user consent, no personal/LLC/nonprofit cross-leakage. No new security window, privilege bypass, live connection claim or merge permission implied. Final acceptance remains with the operator. Recovery is branch/PR close or commit revert; no host rollback needed.
