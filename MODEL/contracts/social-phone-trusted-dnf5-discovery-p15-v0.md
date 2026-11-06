# Social PHONE P15 // Trusted Fedora DNF5 executable discovery

**State:** GitHub-only review candidate, not live Fedora/HFP verification.

**Patient:** kudokudo1/The-Post-Apollo-Project.
**Room:** Social Phone Bridge continuation, P15 DNF5 discovery.
**Staff:** External Hospital-compatible DOC. No live Hospital Room registration verified.
**Evidence:** On Nov 6, 2026, PHONE reported missing PKCON and DNF5, but not PKEXEC. User authorized the next investigation. PR #1319 is merged, and no colliding open PHONE PR was found.

## IMPLEMENTATION

Fedora's official Switch to DNF5 plan and the upstream DNF5 migration reference establish that newer Fedora installations normally provide both the dnf5 command and the standard dnf symlink pointing to dnf5. The previously merged PHONE code looked up only the literal dnf5 name in Quickshell's inherited executable search path. That can create a false negative when the desktop's PATH omits the OS system binary directory.

The new services/phone/PhoneInstallCommandDiscovery.py:
- Checks the inherited PATH and then explicitly the Fedora OS bin directories /usr/bin and /bin.
- Accepts a candidate only if it is absolute, has the expected filename, and resolves inside these trusted OS directories. Untrusted PATH shadows are skipped.
- Accepts the dnf command ONLY when its canonical target is exactly dnf5 in the trusted OS directory. Explicitly refuses dnf4/dnf-3, arbitrary wrappers, and user-directory executables.
- Provides the same lookup for the preflight PhoneCallingSetupHandoff.py and actual interactive PhoneOfonoInstallSession.py. This avoids contradictory preflight and transaction decisions.

The package request is unchanged: PackageKit first, or user-authorized Polkit with the verified DNF5 binary, restricted to ofono with assumeyes and defaultyes disabled. No install on view open, shell invocation, extra buttons, audio changes or private device data.

## HOW TO USE

After owner/operator review, merge and authorized deployment, use Social -> PHONE -> DEVICE -> Calls on PC -> Set Up Calling. If a genuine trusted DNF5 executable was previously missed because of the inherited PATH, PHONE should now be able to stage its existing in-panel installer. The user must review and explicitly approve the native package transaction. If it still reports missing DNF5, obtain an owner-approved read-only host executable inventory rather than add further speculative installer backends.

## VERIFY

New tests/phone/test_phone_install_command_discovery.py checks restricted PATH, trusted directory fallback, untrusted PATH shadowing, valid dnf-to-dnf5 link, rejected DNF3/DNF4 links and failed resolver. Existing handoff and interactive session tests now cover the same validated alias. Existing PHONE workflow adds the new helper and tests and retains previous phone/audio/staging regressions.

Exact-head CI and mergeability verification pending PR creation. These are synthetic tests and are NOT evidence of a running package manager or a successful Polkit prompt on the operator's Fedora system.

## WATCH OUT FOR

The screenshot does not prove dnf5 is installed. The earlier error could reflect a truly absent executable. Do not silently substitute DNF4; transaction history and state differ, and the CLI options may be incompatible. A green CI check cannot verify actual Fedora package installation, oFono activation, Bluetooth HFP, microphone/speakers, or protected message/contact grants.

No local Fedora writes, package installation, Quickshell reload, Sway window manipulation, service restart, Bluetooth changes, PR merge or production activation by this worker. The system audio and package owners remain responsible for real host setup with explicit operator approval.

## CHECKLIST

- [x] Recheck Syntagma rules, current main, ownership and merged PR #1319.
- [x] Verify Fedora DNF5 alias behavior from Fedora and upstream documentation.
- [x] Use trusted OS directories when desktop PATH is restricted.
- [x] Accept only a genuine DNF5 alias, not DNF4.
- [x] Unify preflight and interactive installer discovery.
- [x] Add test coverage and workflow.
- [ ] Exact-head CI and PR mergeability.
- [ ] Operator-authorized merge and separately approved live deployment.
- [ ] Live package-tool identification, Polkit prompt, oFono and HFP verification.
- [ ] Final operator acceptance.

## NEXT

Run CI. After review and deployment, test the same PHONE button and observe whether DNF5 is recognized. If absent, do not guess: inspect the actual host's trusted OS executables under the package owner's approval. Then separately verify service readiness and a normal non-emergency call.

## DECISIONS

One existing PHONE setup control, Fedora OS-native package approval, no arbitrary privileged bootstrap and no global user-device settings. Repository only. GitHub is technical truth; Hospital coordinates but live attachment is unverified. Recovery is closing the draft PR or reverting its bounded commits after an authorized merge. Operator has final authority.
