# 🏥💜 Universal Connections // C4b Silverblue protected /opt proposal

PATIENT // The-Post-Apollo-Project  
ROOM // C4b signed SELinux-confined Silverblue fake-service verification  
ASSIGNMENT // Synthetic-only security design evidence for the C3b/C3c owner  
SOURCE // [C3b owner request #1532](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1532)  
STATUS // CANDIDATE ONLY · NOT C3b POLICY · NOT ORIGIN AUTHENTICATION · PRODUCTION HOLD

## IMPLEMENTATION // Verified source evidence versus proposed policy

The real [offline Fedora Silverblue 44 VM run #42500764517](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42500764517) proved the literal link `/opt -> var/opt` resolving to `/var/opt`. Both `/var` and `/var/opt` were UID 0, mode 0755, genuine nonsymlink directories. Original C3b failed solely at the deliberately strict `C3C_UNPROTECTED_DIRECTORY` rejection of the `/opt` symlink. The signed immutable fake host, composed SELinux policy, confined runtime and negative file-access test passed; the rollback stage was never reached.

This small **C4b-only experiment** defines `opt_link_profile_candidate.py`, a pure function of a **synthetic snapshot**, and an adversarial suite `test_connections_c4b_opt_profile_candidate.py`. It models a possible future owner-approved Silverblue profile but cannot authorize anything. It is never staged into the guest, never imported by C3b, never allowed to change the signed service, and never called to override C3b's failed origin verdict.

The candidate requires:
1. An explicit offline Silverblue 44 test-only profile, the exact Fedora Silverblue OSTree ref, booted OSTree marker, Fedora release 44 and no network interfaces.
2. Exactly `/opt -> var/opt`, resolving to `/var/opt`; the link itself must be root-owned with root group, a genuine symlink and a stable positive device/inode identity across two snapshots. Nominal symlink mode 0777 is treated as *link mode*, never as the target directory's mode.
3. Two matching snapshots of every guarded real directory: `/`, `/var`, `/var/opt`, physical venv parents under `/var/opt`, and the logical venv parents under `/opt`. Every directory must be root-owned, nonsymlink, a genuine directory and not group/other writable.
4. No missing, additional, swapped or malformed evidence fields. All five grant/authentication flags remain `false`, even for a coherent candidate.

The adversarial tests reject altered link text, alternate absolute/relative targets, redirected resolved paths, changed inode, wrong UID/GID, unsafe/writable or symlinked ancestor directories, missing/extra paths, changed directory facts and wrong OS/profile/network context.

## HOW TO USE

Static tests run during the C4b GitHub Actions **preflight**, before any VM startup. The model is not installed on any computer or called from the real C4b guest. It does **not** make the existing real VM pass. A C3b/C3c owner would need to review the complete threat model and then separately design any live OS-probe changes with actual source-of-truth checks, TOCTOU protections and original Fedora Cloud compatibility.

## VERIFY

- [ ] Exact-head new synthetic adversarial tests pass CI.
- [ ] Existing C3b/C3c adversarial tests and source contracts remain unchanged and pass.
- [ ] Production Connections deny-only settings and signed package guards remain unchanged.
- [ ] C3b/C3c security owner explicitly accepts or rejects this candidate, with a separate branch/PR for any authorized implementation.
- [ ] Real C4b signed guest origin and second-boot rollback pass after authorized integration.

## WATCH OUT FOR

**This is a model, not an OS attestation.** Fields such as `fedora_release`, `ostree_ref` and `opt_before` can be fabricated by a caller. The candidate must NEVER be made a decision source for D-Bus, service start, credentials, permissions or API access. A future approved OS probe must obtain the facts independently from the guest under a strict disposable CI opt-in, and validate path components and both snapshots. Root remains inside the trust boundary.

The original C3b owner explicitly hardened *all* symlinked parent directories in C3c. No implicit policy-owner takeover is authorized by this experiment. CI will continue to fail at the existing strict C3b gate until that owner chooses a separate compatible design. No workstation edits or production activation are permitted.

## CHECKLIST / NEXT / DECISIONS

- [x] Preserve actual Silverblue path evidence in GitHub #1532.
- [x] Isolate a pure, deny-only C4b candidate and adverse tests.
- [ ] Exact-head static CI and dedicated signed-VM result.
- [ ] C3b/C3c owner decision and any separately authorized policy work.
- [ ] Full C4b origin identity and rollback proof.
- [ ] Operator final technical acceptance.

DECISION // Keep candidate-only PR draft and unmerged while C3b owner review is unresolved. No production credentials, app authorization, fake OS evidence or SELinux weakening.
