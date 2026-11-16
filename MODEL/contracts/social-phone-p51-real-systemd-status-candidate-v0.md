# Social PHONE // P51 actual supervised status process observation

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Staff role:** external Hospital-compatible PHONE DOC; live Room/Assignment/Session not verified.  
**GitHub checkpoint:** P49 [#1977](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1977) and P50 [#1979](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1979) merged into `main` on November 16; exact P49/P50 files were read from main before creating a fresh P51 branch directly from `main`. Current owner work C4b Identity [#1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785) still OPEN (separately reported Fedora 44 Silverblue two-boot CI success), C3e-AC [#1978](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1978) OPEN with diagnostic marker intake, C5 actual consent not verified. Personal metadata-write issue [#1885](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1885) remains blocking.

## IMPLEMENTATION

1. `services/phone/PhonePersonalSystemdOriginP51.py` is a **read-only observation of a genuinely running systemd status-only candidate**. It uses a fixed OS `/usr/bin/systemctl --system show` on the PHONE unit, checks exact `MainPID`, `User`, `Group`, `ControlGroup`, `FragmentPath`, `LoadState`, `ActiveState`, and `SubState`; reads actual kernel `/proc/<PID>/stat`, `status`, `cgroup`, `cmdline` and executable symlink to ensure startticks, full real/effective/saved/fs UID/GID, no new privileges, zero effective capabilities, exact command line and supervised cgroup. It rechecks the second systemd snapshot and process startticks/cgroup to refuse replacement.
2. The candidate also verifies **root-owned, non-symlinked staged P47/P48/P49/P50 modules** (exact 0555 files, no hardlink), P49's inert systemd unit (exact 0644 source-copy match), explicit root-owned test marker and the service-owned 0700 runtime dir/0600 status socket. No keyring import or application state write, and no public PID, path or cryptographic source material.
3. `tests/phone/p51_real_systemd_status_guest.sh` runs **only as root in a disposable GitHub-hosted Linux runner**, refuses existing PHONE users, paths, units and markers, creates a dedicated service UID/GID, temporarily stages root-owned code and the non-enabled inert unit in `/run/systemd/system`, creates the explicit status test marker, starts a genuine systemd-supervised `python3 -I -B` P49 process, and verifies P51's actual runtime observation. The service-owned client obtains only `HOST_UNTRUSTED_STATUS_ONLY`; an external root client gets DENIED; changing staged source permission while running makes the observer refuse. CI stops the unit and verifies socket cleanup, then removes only resources it created (trap and exact paths). This test is not an RPM package installation, Fedora Silverblue boot, SELinux policy load, actual logind user seat or persistent release signer.
4. `tests/phone/test_phone_personal_systemd_origin_p51.py` adds malformed/duplicate `systemctl` response, wrong PID/unit/group/cgroup, nonzero capabilities, absent `NoNewPrivs`, tampered stat/credentials and no-public-authority tests. The dedicated P51 workflow also reruns real P47/P48/P49 and P44/P45 editor source regression.

## HOW TO USE

**No workstation operation.** The P51 script is a destructive-looking but deliberately guarded *disposable CI fixture*, never to be run on your Fedora computer. It is NOT a production installer and is not exported as a UI button or daemon auto-start. The source check does not read private contacts, notes or Secret Service. The real STATUS-only service is tested under a temporary dedicated OS identity on GitHub only.

## VERIFY

On P51 PR exact head, require the dedicated Linux systemd workflow to **really start an active unit** and inspect its MainPID, UID/GID, root-owned module bytes, cgroup, kernel executable, process flags, owner-only socket, and negative extra-user attempts. Verify removal and post-stop REFUSED. Other P47–P49 kernel/socket tests and Personal editor locked-state checks must continue passing. Independent Fedora/SELinux/OSTree install and two-boot rollback still unverified for PHONE.

## WATCH OUT FOR

**What P51 proves:** A root-installed *test source* and an actual process claimed by systemd have internally consistent live kernel observations on an ephemeral Ubuntu runner. This is meaningful physical process evidence but **not independent host authentication**. A malicious root or compromised signed image can forge or replace the service, code and unit. P51 does not verify signed RPM package origin, immutable OSTree deployment, true SELinux enforcing policy, current logind seat, pinned independent release root or rollback-resistant floor. It reuses the P49 STATUS-only service whose environment test switches and Python import order are not trust boundaries.

C4b Identity's genuine Silverblue CI progress does not authorize PHONE and its separate release key cannot be transplanted. C3e diagnostics remain non-authorizing, C3e external one-use challenge consumption/revoke/floor and C5 true per-Favorite/Note human approval bound to P41b `editHmac` still lack verified production producers. PHONE Secret Service collection isolation, provision/rotation/recovery/erase and host-controlled lease across P35 AES-GCM CAS/fsync/readback remain undelivered. **No status result from P51 authorizes a key or SAVE**, and P42 SAVE stays hard-disabled.

P51's observer is Python source executed by the test runner, not an independently enrolled native pre-execution loader. It cannot prevent compromised code imports or assert policy confinement; even its successful response is named `SYSTEMD_CANDIDATE_OBSERVED_NOT_AUTHENTICATED`. Do not convert its `systemdCandidateObserved` into `installedHostVerified`.

## CHECKLIST

- [x] Fresh mainline + Hospital/owner status review and scope verification.
- [x] PHONE-only actual read-only unit/MainPID/OS identity and staged-file observer.
- [x] Disposable systemd install/start/signed-off test identity/root-owned-source/deny/stop/cleanup plan and workflow.
- [x] Source/parser/permissions/capability mutation refusal tests.
- [ ] Exact P51 GitHub CI, independent review and integration handoff.
- [ ] Operator review/merge P51 to main, post-merge actual file verification.
- [ ] Real PHONE signed RPM/OSTree package and SELinux/logind/seat/rollback evidence, independently enrolled root.
- [ ] Genuine C3e one-use consume/revoke/rollback floor + C5 human PHONE action consent, nonforgeable protected key lease.
- [ ] Real encrypted P35 SAVE/readback and Quickshell UI, separately authorized machine activation and final acceptance.

## NEXT

**PHONE installed signed-package origin**, not another synthetic receipt: coordinate the exact C4b signed-boot and C3e independently pinned root review without changing their ownership, package PHONE's root-owned status-only service as a dedicated signed RPM, then run its own Fedora Silverblue layer/boot, systemd/SELinux/seat and rollback verification. Once C5 genuine PHONE per-action approval and the independent one-use issuer are available, implement the protected service's host-held authorization lease through P35, and connect actual Favorites/Notes saves and trusted UI readback.

## DECISIONS

P51 is additive, PHONE-only, test-status-only. No changes to local Fedora, Quickshell, private phone, contacts, keyring, production, or other workers' code. No merge/activation without operator authority. Final operator acceptance separate from CI.
