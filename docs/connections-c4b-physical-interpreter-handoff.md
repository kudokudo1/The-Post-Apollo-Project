# 🏥💜 C4b // Signed physical-interpreter relocation, disposable Silverblue 44

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · C4b signed confined fake service / real Silverblue  
STAFF ROLE // External Hospital-compatible DOC (not live registered)  
ASSIGNMENT // C4b-owned test-only host, venv and client physical-path relocation  
SECURITY OWNER // C3b/C3c Nurse 2; separate [PR #1548](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1548)  
DESIGN AUTHORITY // [NRS-2 disposition on issue #1532](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1532#issuecomment-6724751852)  
PRODUCTION // HOLD

## IMPLEMENTATION // Separate C4b changes

Original official Fedora Silverblue 44 real VM [run #42500764517](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42500764517) showed `/opt -> var/opt`, with `/var` and `/var/opt` root-owned mode 0755 real directories. After successfully composing the signed SELinux policy, labeling immutable host and starting a confined fake status service, C3b rejected the symlinked `/opt` ancestor under its deliberate security invariant. The security owner selected **physical venv/interpreter relocation**, rather than a symlink exception, in issue #1532.

This C4b-only branch makes these narrow changes:

1. In a disposable GitHub Actions runner, `prepare_physical_status_host.py` creates an **ephemeral** copy of the C2r fake status host with *only* its first shebang replaced: `#!/opt/postapollo-c2o-venv/bin/python3` becomes `#!/var/opt/postapollo-c2o-venv/bin/python3`. The original source bytes after the first line remain identical. It refuses any unexpected original header and any output outside `RUNNER_TEMP`, requires `GITHUB_ACTIONS=true` and a C4b opt-in, and creates the output exclusively.
2. The C4b workflow overlays that single staged file at the source host path **only inside its disposable Fedora 44 Docker signing container**, using a read-only nested bind mount. It reuses the unchanged C3d builder and unchanged C3d RPM spec, systemd unit and D-Bus policy. A new ephemeral disposable signer signs the resulting three-file RPM before offline staging. No version-controlled C2r/C3d source, signer root or production file changes.
3. The C4b guest creates its networkless Python venv under the physical `/var/opt/postapollo-c2o-venv` directory and runs test clients from `/var/opt/c4b`. It checks that the exact signed host shebang refers to the **physical** interpreter before starting the service, retains SELinux Enforcing, signed RPM ownership, D-Bus denial, dedicated service account, exact systemd unit and negative file-access gate, and cleans all physical test files before the second reboot.
4. C4b asks the independently maintained C3b probe to use `--verify-disposable-physical` with `POST_APOLLO_C4B_TEST_GUEST=1`, alongside the original disposable guest flag. The new C3b profile is **NOT part of this PR**; its owner is implementing and testing it separately in [#1548](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1548). Until that source lands, the signed guest cannot pass the exact origin check, and C4b cannot reach rollback.

## HOW TO USE

No workstation commands, production service installation or credential setup. Review the [C3b owner disposition](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1532#issuecomment-6724751852), [C3b PR #1548](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1548) and this C4b draft. After the independently verified C3b physical verifier lands in `main`, rebase/refresh the C4b PR source, rerun its entire exact-head offline Silverblue dual-boot CI, and retain all original preproduction gates.

## VERIFY

- [ ] C4b source/adversarial tests prove only the signed shebang changed and original C3d signer/script unchanged.
- [ ] Disposable C4b signing container produces a real signed RPM with the physical shebang, and C4a signature/payload/integrity checks pass.
- [ ] Real booted Silverblue 44 C4b guest executes the physical venv and host while SELinux enforcing, its negative dummy file denial passes, and the independent **C3b physical** OS service-origin probe verifies PID/UID/systemd/cgroup/argv/SELinux/NoNewPrivileges and real protected `/var` ancestry.
- [ ] Read-only/unauthorized caller checks, explicit service stop, test-user/venv cleanup pass.
- [ ] **Second real Silverblue reboot / RPM-OSTree rollback** removes all three signed RPMs, custom SELinux policy, test keyrings, service executable and accounts. No production activation.
- [ ] Independent security owner reviews exact final integration and operator accepts technical milestone.

## WATCH OUT FOR

**This is an integration branch, not an accepted runtime.** C3b/C3c source and original default Fedora Cloud test behavior are owned by Nurse 2; the C4b branch must not edit or import unmerged C3b code. A signed package build passing is not proof of service execution or origin. Never use a systemd `ExecStart` drop-in to override the signed unit, never alter immutable `/usr`, do not remount or make `/opt` writable and never weaken SELinux, signature or D-Bus checks. The C3b source may still change during owner review; C4b must target the finally accepted selector.

## CHECKLIST / NEXT / DECISIONS

- [x] Identify exact `/opt` symlink blocker from genuine Silverblue VM.
- [x] Secure owner disposition selects physical relocation.
- [x] Implement C4b-owned runtime/fixture relocation without editing C3b/C3d source.
- [ ] Exact-head signed-container/CI verification.
- [ ] Merge/accept C3b owner PR separately only after its gates.
- [ ] Complete Silverblue C4b identity/rollback and regressions, then authorized merge.
- [ ] Operator final technical acceptance.

DECISIONS // C4b PR remains draft pending technical evidence and owner dependency. PR #1545's synthetic symlink candidate remains separate, not an origin authority. No production credentials, key enrollment, host changes, service activation or expanded role.
