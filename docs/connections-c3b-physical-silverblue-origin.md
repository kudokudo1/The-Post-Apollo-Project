# 🏥💜 Connections // C3b/C3c physical Silverblue origin profile

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · C3b/C3c OS-origin protected service
STAFF ROLE // Nurse 2 · NRS-2 (external Hospital-compatible)
ASSIGNMENT // Narrow physical-path test-only response to C4b issue #1532
STATE // DRAFT · CI ONLY · NO C4B RUNTIME INTEGRATION · PRODUCTION HOLD

## IMPLEMENTATION
The original default Fedora Cloud `--verify-disposable` path and `/opt/postapollo-c2o-venv/bin/python3` constant remain unchanged. The alternative `--verify-disposable-physical` is exclusively for an offline, real Fedora 44 Silverblue C4b guest, not a production policy switch. It requires `GITHUB_ACTIONS=true`, the existing C3b guest marker, an additional C4b guest marker, root execution, an exact test-only on-guest C4b fixture file, OSTree boot marker, Fedora 44 release, the original Silverblue branch ref from `ostree admin status`, and only the loopback network interface.

When this opt-in is explicitly selected, C3b requires exactly `/var/opt/postapollo-c2o-venv/bin/python3` in the running process argv, never the `/opt` alias. The protected ancestor list is the original /usr tree plus the genuine `/var`, `/var/opt` and physical venv parents; every directory must be root-owned, non-symlink, nonsubject-to-group/other writes and consistent across snapshots around D-Bus observation. Directory device/inode/mode/owner/group are checked before and after. The original D-Bus, SELinux, PID, UID, cgroup, NoNewPrivileges, files and all five denied authorization bits remain unchanged.

This PR deliberately does not touch the C4b guest scripts, the RPM, production Connections broker or the synthetic candidate PR #1545. C4b worker must choose the matching physical interpreter in its own signed fake-service testing and keep genuine two-boot rollback acceptance.

## HOW TO USE
Existing Fedora Cloud: `C3bOriginCheck.py --verify-disposable` (unchanged).
C4b opt-in inside its disposable signed offline Silverblue VM only: pass `POST_APOLLO_C4B_TEST_GUEST=1` alongside existing C3b disposable variables, and invoke `C3bOriginCheck.py --verify-disposable-physical` after its signed, confined service uses the exact physical interpreter path. This is a CI experiment, **not** a command to run on the operator desktop.

## VERIFY
- [ ] Exact-head source parser and adversarial C3b tests.
- [ ] Existing Fedora 44 enforcing C2r guest full regression.
- [ ] C4b owner implements physical-path runtime transition separately.
- [ ] Actual C4b signed Silverblue guest pass for C3b origin with both real rollback boots.
- [ ] Independent security review and operator acceptance.

## WATCH OUT FOR
This is not proof of a signed/installed production host, release authority, human approval, credential access or API capability. Guest marker files and environment are disposable fixture controls, not real-world authentication. Refuse any attempt to pass self-reported path facts from a client, accept arbitrary symlinks, bypass the strict original default, or count a first boot as completed rollback.

## CHECKLIST
- [x] Read current default C3b, actual C4b runtime and verified path facts.
- [x] Record security-side preferred physical-path design in issue #1532.
- [x] Add isolated test-only physical argv and directory guard with prior/after snapshots.
- [x] Add synthetic rejection tests and CLI refusal test.
- [ ] Confirm exact-head CI and repair proven issues.
- [ ] C4b owner integration and full VM rollback success.
- [ ] Operator final acceptance.

## NEXT
Wait for exact-head C2r test results. Coordinate the separate C4b-owned runtime modifications; do not alter their active PR #1545. Recheck current `main` and ownership before follow-on edits.

## DECISIONS
Physical /var/opt interpreter path is the preferred narrow test profile. No blanket /opt symlink exception approved. All production service auth, credentials, API grants, workstation installation and key custody remain disabled.
