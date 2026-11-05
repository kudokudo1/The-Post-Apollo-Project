# Social PHONE P14 // Name the exact missing installer tools

> **STATE //** GitHub-only diagnostic correction, not host package setup or verified HFP.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation; P14 embedded installer diagnosis
> **STAFF //** External Hospital-compatible DOC; not verified Hospital-registered.
> **OPERATOR EVIDENCE //** Nov 5, 2026 screenshot following merge of P13 PR #1317: PHONE states “Neither PackageKit (pkcon) nor Polkit with DNF5 is available” and no terminal appears, although the UI still shows SET UP CALLING. No live Fedora inspection was available to determine which executable is missing.

## IMPLEMENTATION

The combined P13 error results whenever neither `pkcon` nor the complete `pkexec`+`dnf5` pair can be found using a strictly allowlisted system-binary resolution. It **does not establish** all three are absent. The screenshot exposed a knowledge gap: the helper discarded the outcome of each lookup.

This patch preserves the **one** existing SET UP CALLING button and installer handoff, and makes its failure diagnostic precise.

1. `services/phone/PhoneCallingSetupHandoff.py` returns a `missingTools` array of bounded enum identifiers, never paths, environment variables, system commands, package-manager output, or private device data. IDs: `FOOT`, `PYTHON3`, `INSTALLER_HELPER` for the terminal stage; `PKCON`, `PKEXEC`, `DNF5` for the OS package backend. These are **executable/helper discovery results within the PHONE process**, not proof the corresponding Fedora RPMs are absent.
2. When `TERMINAL_UNAVAILABLE`, the report includes the exact required stage components not found. When `PACKAGE_MANAGER_UNAVAILABLE`, it includes each unresolvable member of the two supported native paths. Other results default to an empty array.
3. `PhonePane.qml` validates all report fields, including missing-tool type, enum allowlist, uniqueness, length and applicability, before rendering a plain text name list inside DEVICE. It tells the user that either `pkcon` **or both** `pkexec` and DNF5 are required. No extra button or terminal instruction. The missing list is cleared on new checks and when the pane opens.
4. The actual install action remains unchanged: exact user-clicked `ofono`, embedded foot stage, PackageKit preference, or explicit Polkit/DNF5 native authorization. No fallback to a window beneath Social, no blind executable discovery outside approved OS paths, and no silent retries.

**Root blocker remains unknown** until this updated code is deployed and the user clicks SET UP CALLING. If the host truly lacks both package authorization routes, an OS package-management owner must provide an approved installer mechanism separately. A widget cannot securely bootstrap its own privileged installer when none exists, and this PR does not attempt that.

## HOW TO USE

After authorized review, merge and deployment, return to **Social → PHONE → DEVICE → CALLS ON PC → SET UP CALLING**. If the installer cannot start, read its new `Not available to PHONE: ...` names. For example, reporting `PackageKit (pkcon), Polkit (pkexec)` while omitting `DNF5` means DNF5 was recognized, but both supported authorization routes are incomplete. Nothing is installed until a separate supported native transaction is explicitly approved.

The existing CHECK AGAIN and status flow continues once a package transaction actually completes.

## VERIFY

- Expanded `tests/phone/test_phone_calling_setup_handoff.py` to enforce the exact `missingTools` shape, bounded enums, absence of filesystem paths, exact missing backend cases, successful-stage empty list, and the existing fail-closed prerequisites.
- Expanded `tests/messaging/test_social_phone_calling_setup.py` to require sanitized UI validation and missing-tool copy, without showing host error output.
- Existing `.github/workflows/social-phone-one-action-setup.yml` runs both tests and all PHONE regressions. Exact-head CI is pending at PR creation.

Synthetic GitHub tests are not evidence that oFono, PackageKit, DNF5, Polkit or any host authentication capability is actually present on the user's Fedora desktop.

## WATCH OUT FOR

- **Do not infer package absence from failed executable discovery.** The running Quickshell process may have a different PATH, or an executable may be installed in an unsupported directory. A real read-only host inspection would distinguish these without installing anything.
- No part of this patch installs packages, starts a service, reloads Quickshell, changes Bluetooth pairing, modifies per-phone audio, grants access to phone content, or bypasses OS authorization. It is a report-format correction.
- Missing package-management infrastructure needs separate local host owner approval, not a third arbitrary privilege escalation fallback. Fedora oFono HFP readiness, D-Bus access, WirePlumber routing, and real incoming/outgoing non-emergency test calls remain independent.
- This PR does not solve the underlying missing package-management dependency. It produces actionable evidence for the next approved repair and stops the loop of guessing which dependency is missing.

## CHECKLIST

- [x] Recheck Syntagma AGENTS/Hospital rules, current `main`, merged P13 PR #1317, and active PHONE work.
- [x] Read actual Fedora installer tool allowlist and related tests.
- [x] Preserve fixed verified installer choices and user authorization.
- [x] Return the exact missing executable IDs only, with no private paths or errors.
- [x] Render precise in-menu explanation from those IDs.
- [x] Extend tests, durable recovery contract, and index.
- [ ] Exact-head CI, mergeability and reviewer verification.
- [ ] Operator-authorized merge and separate live Fedora deployment.
- [ ] Read actual missing tool names in the deployed menu.
- [ ] If necessary, approved OS-package-owner remediation and native installer acceptance.
- [ ] Functional oFono/BlueZ/WirePlumber HFP call verification and operator acceptance.

## NEXT

Review CI and diff. Once deployed, capture the new missing-tool names rather than reinstalling oFono or changing the paired iPhone. If all available native installer backends are unsupported, hand off the precise observed deficiency to the system package owner. Do not make unapproved desktop changes.

## DECISIONS

Keep one PHONE setup action, no unsafe privileged bootstrap and no irrelevant Settings page. Treat GitHub as source truth, Hospital as ownership continuity, and operator as final authority. GitHub-only draft; recovery: close PR or revert its bounded commits after any authorized merge. No live Hospital registration claimed.
