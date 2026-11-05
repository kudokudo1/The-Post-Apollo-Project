# Social PHONE P13 // PackageKit-optional in-panel oFono installation

> **STATE //** GitHub-only review candidate, not a live Fedora package transaction, phone connection, or completed HFP setup.
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
> **ROOM //** Social Phone Bridge continuation / P13 installer fallback
> **STAFF //** External Hospital-compatible DOC; live Hospital Room registration and OS-package-owner assignment not verified.
> **EVIDENCE //** Operator November 5, 2026 screenshot after P12 (#1300) merged: PHONE shows **“The embedded installer needs foot, Python and PackageKit available on this desktop. No external window was opened or package installed.”** The blank lower panel means no installer was staged. This proves some required executable/helper was unavailable, but not which one. The desktop was not inspected by this worker.

## IMPLEMENTATION

Previous P11/P12 logic refused the entire installer unless `foot`, Python, and PackageKit `pkcon` were all installed. On a lean Fedora/Sway desktop, PackageKit CLI is optional; a working terminal, Python, and DNF5/Polkit may already exist. This PR eliminates **pkcon as a hard prerequisite**, without returning to the broken GNOME Software app-details page.

After the existing user-initiated `Social → PHONE → DEVICE → Calls on PC → Set Up Calling` click:

1. `PhoneCallingSetupHandoff.py` rechecks the exact Fedora oFono package absence, a missing system unit, and the installed executable prerequisites. It accepts either installed PackageKit `pkcon`, **or both** `pkexec` and `dnf5`; it still requires `foot`, Python, and the fixed installer script. It opens only the existing installer-tagged foot window, not an external GUI fallback. It does not directly call DNF/Polkit or install a package.
2. `PhoneOfonoInstallSession.py --interactive-ofono` requires an actual TTY and one explicit action. It prefers PackageKit's normal `pkcon install ofono` when available. If `pkcon` is **absent**, it uses `pkexec /usr/bin/dnf5 --setopt=assumeyes=False --setopt=defaultyes=False install ofono` (using only resolved OS-owned executable directories). **Polkit manages authorization**, and DNF5 shows a transaction review with explicit interactive no-by-default confirmation. No shell, sudo, `-y`, credential capture, background install, service start, or Bluetooth change.
3. If PackageKit fails or the user declines its prompt, there is **no automatic retry** with elevated DNF5. The session prints a neutral result and stays open for review. Successful installer return codes are still **not** proof the package is installed or HFP works; the existing read-only RPM/service and BlueFerry checks remain required.
4. PHONE distinguishes `TERMINAL_UNAVAILABLE` (foot/Python/helper unavailable) from `PACKAGE_MANAGER_UNAVAILABLE` (neither PackageKit nor Polkit+DNF5). Both appear as plain text in the existing DEVICE pane, with no external window.
5. P12's lower terminal bay, exact Sway window identity, compositor cutout, preserved user input and the pinned Return to PHONE control remain unchanged. The user's iPhone pairing, BlueFerry media choices, Social trust status and shared settings remain untouched.

## HOW TO USE

After authorized merge and separate runtime deployment: **Social → PHONE → CONNECT PHONE → DEVICE → CALLS ON PC → SET UP CALLING**. The existing lower terminal should show PackageKit, or Polkit authorization followed by a DNF5 transaction if PackageKit CLI is absent. Inspect the package and dependencies and explicitly approve or decline. On completion press Enter; PHONE then rechecks the actual oFono package/service status. Rechecking is not an install request.

There is no new permanent Settings page, terminal command that the user must type, or global installation default for other users. Every computer checks its own available Fedora installer backend. If both native approaches are missing, the menu says so rather than making another dead window.

## VERIFY

- `tests/phone/test_phone_calling_setup_handoff.py` covers embedded DNF5 availability when `pkcon` is absent, distinct missing-terminal versus missing-backend results, trusted executable locations, explicit click and lack of external fallback.
- `tests/phone/test_phone_ofono_install_session.py` covers TTY gate, exact `ofono` package and argv, PackageKit preference, no automatic root DNF retry on PackageKit failure, native Polkit/DNF5 confirmation with assumeyes/defaultyes forced false, no fake success, no leaked private errors.
- `tests/messaging/test_social_phone_calling_setup.py` covers the same contextual button, sanitized result contract, distinct errors, existing PHONE/Stage cutout and absence of automatic phone/audio changes.
- Existing Social PHONE workflow runs all tests. Exact-head CI and mergeability must be independently verified.

**No live Fedora tools, actual PackageKit client, DNF5 config, Polkit agent, Sway window geometry, iPhone HFP, or package installation has been inspected or changed.** GitHub CI uses mocked commands and does not certify live authorization or install success.

## WATCH OUT FOR

- The current screenshot does **not** prove `pkcon` specifically is absent. It could be missing foot, Python on the expected PATH, or the installer helper script. This implementation accepts an alternate when available and reports the two categories separately, but a live read-only probe is needed for certainty.
- `pkexec` may present a graphical or embedded textual authentication prompt. A Polkit agent, suitable permission, configured Fedora repository, and interactive terminal are necessary for successful installation. No attempt to bypass authorization is permitted.
- DNF5 may have user-specific or system configuration. The explicit options force `assumeyes=False` and `defaultyes=False` for this transaction; no `-y` or auto-grant is allowed. The user still reviews the actual requested operation.
- Neither installed oFono nor a completed package transaction proves the service is active, D-Bus HFP works, WirePlumber routes the microphone, or a call can be placed. Those remain separate OS-audio owner, operator-approved verification steps.
- No merge, local Fedora file modifications, software installations, service start, Quickshell reload, Bluetooth reset, phone content access or production activation by this worker. Actual future installation is user-initiated within the deployed UI and subject to native authorization.
- The PackageKit and DNF5 paths are **alternatives**, not a fall-through after failed/cancelled install. No global personal-phone settings are copied between users.

## CHECKLIST

- [x] Recheck current `main`, merged P12 #1300, live screenshot and active PHONE PR ownership.
- [x] Verify upstream Fedora DNF5 interactive/install semantics and Polkit authorization.
- [x] Remove PackageKit as mandatory when native Polkit+DNF5 exists.
- [x] Preserve single exact-package interactive stage and no external installer windows.
- [x] Provide exact missing-terminal versus missing-package-manager feedback.
- [x] Add unit/QML tests and durable handoff.
- [ ] Exact-head CI and mergeability verification.
- [ ] Phone/Social, OS-package owner and operator review and authorized merge.
- [ ] After separately authorized deployment, test the actual embedded terminal and native user confirmation, then package status.
- [ ] OS-audio owner verifies oFono/BlueZ/WirePlumber HFP and a non-emergency call.
- [ ] Operator final acceptance.

## NEXT

Review CI, then deploy only with operator authorization. Confirm the lower PHONE terminal can open and whether PackageKit or DNF5/Polkit was actually selected. Any missing backend remains a separately scoped system package task requiring explicit approval. Do not silently add packages or re-pair the phone.

## DECISIONS

One in-panel installer, two supported Fedora backends, **no automatic approval**. Never mistake provider status for authenticated phone content access. GitHub is technical source of truth; worker is external Hospital-compatible DOC, not live-registered. Recovery is closing draft PR or reverting bounded commits if later merged; operator has final authority and acceptance.
