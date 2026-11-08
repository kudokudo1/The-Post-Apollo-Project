# 🏥💜 Connections // C3b/C3c canonical Silverblue /opt origin (CI only)

PATIENT // The-Post-Apollo-Project
ROOM // C3b/C3c OS service-origin security
STAFF ROLE // Nurse 2 · NRS-2 (external Hospital-compatible; live registration unverified)
ASSIGNMENT // Resolve C4b /opt ancestry refusal without altering C3d's signed service
STATE // DRAFT · C3b SOURCE ONLY · PRODUCTION HOLD

## IMPLEMENTATION
The original strict Fedora Cloud `--verify-disposable` path remains unchanged: exact `/opt/postapollo-c2o-venv/bin/python3` argv and root-owned, nonwritable, genuine no-symlink `PROTECTED_DIRS`. The existing signed C3d service has a hardcoded `#!/opt/postapollo-c2o-venv/bin/python3` shebang, so merely relocating C4b's venv to `/var/opt` cannot change its kernel-interpreted process argv without a separate signed-package change.

A *separate* `--verify-disposable-silverblue-opt` probe accepts the original argv but permits exactly the observed official Silverblue `/opt` symlink inode, with **literal** target `var/opt` and resolved path `/var/opt`. It requires direct guest lstat/readlink evidence, root ownership/group, exact link metadata, root-owned and non-group/other-writable physical `/var`, `/var/opt`, and venv/bin ancestors, with no extra symbolic links. Captured link and directory device/inode/type/UID/GID/mode attributes must be identical across snapshots before and after the original D-Bus owner check. The logical /opt venv/bin directories remain strictly root-owned, nonsymlink, nonwritable; no other C3b path gains an exception.

**Opt-in guest boundary:** root-only; `GITHUB_ACTIONS=true`, existing C3b test flag, additional C4b flag, exact C4b guest marker, real OSTree boot marker, Fedora release 44, Silverblue branch reference in `ostree admin status`, and loopback-only network. These identify the disposable experiment; they are **not** production authentication. All original D-Bus, PID/UID, cgroup, SELinux, NoNewPrivileges, protected files and immutable false authorization fields remain mandatory.

No C3d signed host/script, C4b runtime, production Connections QML, credentials or workstation has been changed.

## HOW TO USE
Existing Fedora Cloud test: `C3bOriginCheck.py --verify-disposable` as before.
C4b offline real Silverblue test: pass the extra `POST_APOLLO_C4B_TEST_GUEST=1` and `--verify-disposable-silverblue-opt` ONLY inside the independently qualified C4b VM. C4b owner should continue using the existing signed /opt shebang, require actual full C3b origin PASS, all unauthorized action refusals, and real two-reboot rollback. Do not run this experimental verifier on the desktop.

## VERIFY
- [ ] Exact-head Python unit/security tests pass.
- [ ] Original C2r Fedora 44 enforcing guest still passes with default strict mode.
- [ ] Full C4b signed, confined offline Silverblue guest passes *original* signed host origin, exact canonical link and second real rollback reboot.
- [ ] Independent source/security review and operator acceptance.

## WATCH OUT FOR
The accepted link is deliberately one exact *test OS layout*, not an acceptance of arbitrary symlinks, user-supplied alleged device/inode facts, writable paths, altered shebangs or production credentials. Direct OS snapshots can still have a race in between reads; root compromise is outside this offline VM model. Do not treat this as a general no-TOCTOU guarantee or a live authentication token. Future production path trust requires a separate threat model and appropriate fd-pinned traversal. All grant flags remain false.

## CHECKLIST
- [x] Identify signed C3d shebang dependency and correct physical-relocation proposal.
- [x] Preserve original Fedora Cloud C3b no-symlink policy.
- [x] Add independent Silverblue-only opt-in and exact guest identity.
- [x] Require exact /opt target, trusted physical chain and two stable snapshots.
- [x] Add adversarial synthetic link/path/race/downgrade tests.
- [ ] C3b regression CI / source review.
- [ ] C4b owner guest integration and genuine two-reboot rollback.
- [ ] Operator final acceptance.

## NEXT / DECISIONS
Continue C3b exact-head CI; notify C4b worker that only its *invocation* needs opt-in, preserving the original signed C3d RPM. Keep C4b owner files separate. Source issue [#1532](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1532), prior synthetic candidate [#1545](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1545). Production HOLD until a separate real-host authorization milestone. No merge of failing C4b.
