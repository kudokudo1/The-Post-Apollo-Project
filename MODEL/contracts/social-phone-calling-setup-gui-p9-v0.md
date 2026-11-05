# Social PHONE P9 // Guided graphical oFono setup handoff

> **STATE //** GitHub repository review candidate; neither a completed installation nor a verified live HFP connection.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **ROOM / ASSIGNMENT //** Social Phone Bridge continuation, one contextual UI handoff to existing system package manager after missing-oFono diagnosis.
>
> **STAFF //** External Hospital-compatible DOC, no verified live Hospital Room registration.
>
> **OPERATOR INTENT //** 2026-11-04: "not installed" diagnostic, then "okay" to guided **Set up calling support** inside Social PHONE. User prefers menu controls over terminal commands, without adding a security dashboard or silently changing their Fedora audio setup.

## IMPLEMENTATION

The previously merged P8b flow distinguishes a missing oFono package from stopped, failed, masked or active services. When an explicit Calls on PC click reports **PACKAGE_NOT_INSTALLED**, one contextual **SET UP CALLING** button appears inside the existing PHONE DEVICE audio section. No extra settings screen or new primary Connect Phone action.

The new `services/phone/PhoneCallingSetupHandoff.py --open-ofono` provides a narrow, non-installing GUI handoff:

1. Rechecks *fresh* local `PhoneCallPrerequisites.diagnose()` evidence, requiring schema, read-only execution, missing **oFono** RPM and absent system service unit, and no content or HFP permissions.
2. Confirms the local operating system reports Fedora. It never assumes every Post-Apollo user runs Fedora.
3. Uses only an allowlisted graphical package manager: the installed `gnome-software --details-pkg=ofono`, or `gpk-install-package-name ofono` if available. Both use fixed arguments and an absolute resolved executable. There is no shell, root command, package transaction, service start, Bluetooth change, app data collection, or automatic installation.
4. The graphical package manager is the authority for package selection, dependency review, any OS authentication and final approval by the **user**. The helper reports **GUI_OPEN_REQUESTED**, not "installed" or "connected". No personal Post-Apollo installer, account/device database, or global default.
5. Once requested, **the same button becomes CHECK AGAIN**. That runs fresh read-only prerequisites and the existing BlueFerry audio status; if still missing, the menu shows the real state. If the package appears installed, the UI transitions to the next **service/HFP verification** status. This does not install packages or start services itself.
6. Where no supported graphical package manager is present, the menu says so clearly. It does not fall back to a terminal installer or silently run a privileged command.

**This is intentionally a first owner-bounded GUI handoff, not the full HFP bootstrap.** Configuring and starting oFono, system D-Bus policy, WirePlumber/BlueZ HFP roles, and verifying the microphone/speakers still require authorized OS-audio and Phone Bridge owner review. A user pressing the in-menu control later must approve all actual OS changes in their native package manager.

## HOW TO USE

After authorized review, merge and deployment:

- Open **Social → PHONE → CONNECT PHONE → DEVICE**, then click **CALLS ON PC**.
- If the diagnostic confirms oFono is not installed, click the contextual **SET UP CALLING** action.
- Fedora's graphical software manager is requested for the exact **ofono** package. Choose to install there only if you agree with the native install details and system authentication prompt.
- Return to PHONE and click **CHECK AGAIN**. Social does not claim completion until the package and later HFP/call state are separately checked.
- If installation is unavailable or the service remains stopped, PHONE explains the blocker; do **not** re-pair the iPhone or reset its working media connection.

No terminal commands are required for this UI handoff when an appropriate graphical package manager is installed. The action does not run for unsupported systems.

## VERIFY

- `tests/phone/test_phone_calling_setup_handoff.py`: exact Fedora package proof, allowlisted graphical executable/args, status-only receipt, no automatic install, GUI fallback, redacted errors, stale/tampered evidence rejection, unsupported host, explicit CLI flag.
- `tests/messaging/test_social_phone_calling_setup.py`: contextual single button, dual-action label, no auto-start on menu opening, strict result contract, same contact/feed and Stage Director, no false package-install/HFP result.
- Existing Phone/audio/prerequisite regressions continue via `.github/workflows/social-phone-one-action-setup.yml`.
- This GitHub code has not been run on Fedora with a real graphical package manager. CI tests use fake launchers and cannot certify window focus, package availability or a working HFP call.

Current public source checks (2026-11-04): Fedora provides the [oFono RPM](https://packages.fedoraproject.org/pkgs/ofono/ofono/); GNOME Software supports [`--details-pkg`](https://man.archlinux.org/man/extra/gnome-software/gnome-software.1.en); native desktop package managers own consent and authorization. Some software centers may not index a system-service RPM as an application; this is a known host compatibility limit, not authority to auto-install.

## WATCH OUT FOR

- **Do not interpret GUI_OPEN_REQUESTED as GUI visibly opened, package installed, service started, call preference enabled or a working Bluetooth HFP path.** The helper cannot inspect the future package manager result. CHECK AGAIN is necessary.
- A graphical manager might not be installed on custom Fedora/Sway systems, or might not expose the non-GUI oFono package. In this case, report GUI_UNAVAILABLE or let the package-manager UI show its own failure; further integration belongs to the system software owner.
- oFono package installation is system-level and may require explicit Polkit/admin approval. The user must review that in the native tool. An operator "okay" to a GitHub code milestone is NOT blanket approval for this worker to install software on the current Fedora host.
- oFono package presence does not configure oFono/BlueZ/WirePlumber HFP. The existing BlueFerry `calls enable` guard and unverified-phone-link policy remain separate. Audio (A2DP), calls (HFP), contacts (PBAP), messages (MAP) and FaceTime must never be conflated.
- The user's saved BlueFerry iPhone and per-phone audio settings are not distributed as defaults or touched. A new install chooses its own device and only sees capabilities of supported local providers.
- Shared Social routing, Identity Center, Account Broker and Weather Stage Director are untouched. No live Fedora configuration edits, package installs, service start/restart, paired-device modifications, merge or deployment by this GitHub worker.

## CHECKLIST

- [x] Recheck Syntagma canonical AGENTS/Hospital permissions; current GitHub `main` and active PR collisions.
- [x] Verify merged prior oFono diagnosis and PHONE menu action.
- [x] Confirm Fedora oFono availability and graphical package manager mechanisms.
- [x] Implement one contextual in-menu native GUI handoff for a genuinely missing package.
- [x] Keep per-device status, HFP and Social content permissions fail closed.
- [x] Add unit and UI regression tests and CI workflow.
- [ ] Verify exact PR-head CI and mergeability.
- [ ] Shared Social + system audio owner review and operator-authorized merge.
- [ ] Authorized live Fedora GUI package-details/prompt test with no automatic install.
- [ ] OS audio owner implements approved service/HFP readiness and tests a non-emergency phone call.
- [ ] Final operator acceptance.

## NEXT

Review CI. After an approved deploy, use the PHONE UI to open Fedora package manager, approve the ofono package only when desired, then CHECK AGAIN. If the service still needs configuration, pursue a separate bounded host-audio assignment under owner approval, not a silent bootstrap in this PR.

## DECISIONS

One menu control, contextually shown, with native OS consent; no terminal commands demanded of ordinary users and no default personal pairing shipped to other installations. This work is a GitHub-only, reviewable proposal. Close the draft for rollback; if subsequently merged, revert the bounded commits. Operator remains final authority.
