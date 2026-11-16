# Social PHONE // P49 supervised status-only process launch, actual Linux test

**Patient** `kudokudo1/The-Post-Apollo-Project`  
**Worker** ChatGPT external Hospital-compatible DOC, PHONE source assignment; live Hospital Room/Assignment/Session unverified.  
**GitHub checkpoint** P45 #1957, P46 #1960, P47 #1963 and P48 #1966 all **merged into main on November 14, 2026**. Their exact files were independently re-fetched from `main` before P49. Fresh main-based P49 source branch; no dependent side-branch merge.  
**Owner dependency** PHONE issue #1885 OPEN; C4b Identity Silverblue [PR #1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785) OPEN; C3e and C5 separate protected assignments.

## IMPLEMENTATION

1. `services/phone/PhonePersonalStatusHostP49.py` provides a **real Linux process entry point** for the previously merged P47 STATUS-only Unix-socket endpoint with P48 actual `pidfd` and `/proc` peer checks. Its entry contract requires exactly `--private-status-dir <explicit absolute 0700 directory>`, the two CI-only environment switches `POST_APOLLO_PHONE_STATUS_CI_ONLY=1` and `POST_APOLLO_PHONE_STATUS_NO_SAVE=1`, same real/effective UID/GID and a non-symlinked private socket directory. It measures its own Linux kernel process through a local socketpair/P48 and hashes bounded neighboring P47/P48/P49 module files, refusing group/world-writable or unexpected hard-linked source. It rechecks those hashes before opening a listener. There are no keyring, vault, contact, provider, C5 or consent imports. It emits no personal data or stdout/stderr diagnostics. SIGTERM/SIGINT trigger orderly stop and safe inode-bound socket cleanup.

2. `services/phone/systemd/post-apollo-phone-personal-status-ci.service` is a **source-only, inert** hardened systemd unit. It has no `[Install]` section, requires an external explicit test-only marker and separately provisioned dedicated nonroot `postapollo-phone-status-ci` service identity, uses Python isolated mode `-I -B`, no new privileges, read-only protected filesystem/home/devices, AF_UNIX-only networking, drop-all capabilities and a private 0700 runtime directory. It is **not installed, enabled, started, packaged or registered** by this work. The source and test-only service gate are not authentic production enrollment.

3. `tests/phone/test_phone_personal_status_host_p49.py` actually launches a fresh Python `-I -B` process on an Ubuntu Linux GitHub runner, checks the native kernel socket status and strict authorization-false output, then sends SIGTERM and verifies silent clean exit and socket removal. Negative tests remove CI gates, introduce wrong arguments, corrupt private directory permissions or occupy the socket filename; in all cases no socket is overwritten or save authority exposed. Unit source checks forbid accidental enablement/secret access. Dedicated CI reruns real P47/P48 kernel tests and P45 mainline/locked editor checks.

## HOW TO USE

**No workstation action.** The new code is a GitHub review artifact, not a live Fedora daemon. The systemd file is an inert proposed test-unit source requiring a dedicated account and a test marker that are *not created* by this PR. Do not install, enable, copy into `/usr/lib/systemd`, start services or reload Quickshell without separate explicit operator approval and recovery plan.

## VERIFY

Run the dedicated P49 workflow on the exact PR head and inspect its actual Linux process/socket tests. Verify merged P45-P48 paths on `main` after any future merge. A successful detached Linux subprocess under a GitHub user is not a Fedora Silverblue installed RPM or authentic process/seat/SELinux evidence.

## WATCH OUT FOR

- Both CI-only environment switches are trivial to forge, **not permissions or identity credentials**. The test source hash roster is self-generated and **not signed or enrolled** by C4b/C3e. A same-UID process can still change or impersonate its own files. Actual installed runtime must independently attest root-owned RPM files and *all* Python module hashes, supervised systemd unit/PID, SELinux context, user seat, release and signer under externally controlled custody.
- P49 is the first explicit process entry point, but its STATUS response still says `HOST_UNTRUSTED_STATUS_ONLY` with `installedIdentityVerified=false`, `independentChallengeVerified=false`, `c5OneUseConsentVerified=false`, `keyReadAuthorized=false`, `personalSaveAuthorized=false`, `readbackTrusted=false` and `productionEnabled=false`.
- No Secret Service/keyring access or P35 Personal vault changes. The existing P42/P43 editor remains preview-only with SAVE disabled; genuine Favorites/Notes persistence is not yet available.
- C4b's latest contract reports a successful **actual Fedora Silverblue two-boot install/rollback CI test** on its source, but PR #1785 remains unmerged, independent owner/root/seat review and operator acceptance pending. C3e independently issued one-use challenge/replay authority and genuine signed C5 PHONE-specific human approval bound to P41b `editHmac` are missing. Treat #1885 as BLOCKING for production writes. No reuse of Identity Gateway's test signer as PHONE consent authority.

## CHECKLIST

- [x] Verify exact merged P45/P46/P47/P48 status and actual files on main.
- [x] Read Syntagma AGENTS and Hospital authority boundaries; inspect C4b installed test service contract.
- [x] Create main-based P49 explicit process runner and inert supervised systemd unit source.
- [x] Test real isolated child process, STATUS/denied framing, SIGTERM cleanup and failure gates.
- [ ] Verify exact-head GitHub workflow and independent review.
- [ ] Operator review/merge P49 to main.
- [ ] Owner C4b/Identity signed installed PHONE-relevant server origin, C3e independent one-use issuer and C5 genuine PHONE human-consent producer.
- [ ] Package/status-host install proof with distinct service identity, immutable module roster, SELinux/seat/rollback; then protected key custody and atomic P35 commit/readback.
- [ ] Connect true saved/readback interface to Social Favorites/Notes only after production trust/consent gates.

## NEXT

The next **implementation** is the separately authorized installed-host and trust-enrollment integration: obtain owner-produced genuine C4b/Identity signed release/source/SELinux/seat evidence and independent C3e/C5 credentials, build a PHONE installed service identity under a protected user/OS domain, make the host hold the one-use lease through encrypted CAS/fsync and readback, and finally connect actual native SAVE. Avoid adding a SAVE operation to P49's STATUS-only listener before those signatures and keys are enrolled.

## DECISIONS

P49 adds launchable *source and a real isolated subprocess test*, not an installed service or an authorization producer. No local Fedora, personal keyring, live Quickshell, private contact, external worker code, PR merge or production actuation. The operator remains final authority.
