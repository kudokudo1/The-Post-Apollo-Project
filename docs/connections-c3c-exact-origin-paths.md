# 🏥💜 Universal Connections // C3c exact execution and protected ancestry

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · protected-host evidence hardening  
STAFF ROLE // Nurse 2 (NRS-2), externally Hospital-compatible; no live registration verified  
ASSIGNMENT // Apply C3b's independent post-merge audit findings to exact interpreter/cgroup identity and test path ancestry  
BASE // `bffafcb4ac404ef22f5413d6c06db7c851b4c18c`  
PERMISSIONS // GitHub branch, isolated Fedora CI, tests and handoff only; no workstation or production actuation

## IMPLEMENTATION

C3b PR #1433 and C2z PR #1425 are merged. The independent Nurse 2 C3b post-merge audit at https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1433#issuecomment-6711327773 passed the narrow disposable VM consistency claim and identified three hardening gaps: a prefix-based Python argv check, a suffix-based cgroup path check, and incomplete protected parent-directory/package provenance.

C3c addresses the **first two** with an exact expected interpreter argv element (`/opt/postapollo-c2o-venv/bin/python3`) and exact systemd cgroup (`/system.slice/postapollo-connections-status.service`), with both systemd and kernel process entries required to agree. It also tests ownership, safe mode, directory type and absence of symlinks along static test-fixture parent paths under `/`, `/usr` and `/opt`.

Changes remain within `tests/connections/c3b_origin/C3bOriginCheck.py`, its existing adversarial suite, and this handoff. No C2y/C2z Silverblue scripts, C2r guest drivers, status service unit, QML/broker production code, credentials or real permissions are changed.

C3c preserves every C3b `hostAuthenticated=false`, `credentialPresent=false`, `grantActive=false`, `canApprove=false`, and `canUseApi=false` result. Its passing observation is still named `C3B_OS_ORIGIN_COHERENT_TEST_ONLY` because there is no new application trust root or privilege. Distinct refusal statuses `C3C_DIRECTORIES_MISMATCH` and `C3C_UNPROTECTED_DIRECTORY` identify directory-chain evidence failures.

## HOW TO USE

No desktop action. The existing C2r disposable Fedora guest workflow automatically exercises C3c when its C3b origin fixture source or tests change. CPU++ SETTINGS → CONNECTIONS remains read-only/unverified.

## VERIFY

Require:

- [ ] Exact branch HEAD passes all existing C3b/C3c adversarial tests.
- [ ] Real official hash-pinned Fedora 44 guest boots with SELinux Enforcing.
- [ ] Existing confined service, negative SELinux file denial, D-Bus permission policy and root-owned test unit still pass.
- [ ] Strict interpreter and cgroup identity match actual guest OS records.
- [ ] Parent directories are root-owned, not group/other-writable, real directories and not symlinks.
- [ ] C2r serial includes the unchanged `C3B_PASS` marker (now backed by stricter C3c checks).
- [ ] Prior C2s bundle rollback is not weakened or counted as an origin proof.
- [ ] Independent review and operator acceptance.

## WATCH OUT FOR

Exact argv, cgroup and ancestor path checks in a test VM are **not cryptographically trusted executable identity**. The Python interpreter can still be a symlink to an OS-managed binary; checking the parent directory chain does not verify a package signature or ensure a deployment cannot be replaced by a privileged adversary. This is not a proof of immutable package provenance, actual per-app caller attestation, operator consent or authorization. Future signed package / digest verification must be separately scoped and reviewed before any production trust decisions.

A coherent disposable Fedora Cloud fixture is also not evidence of completing the successor-owned Silverblue C2y/C2z two-reboot recovery requirement.

## CHECKLIST

- [x] Recheck Syntagma protocols and live GitHub main/PR ownership.
- [x] Verify C3b independent review and merged source contents.
- [x] Add exact argv and cgroup checks.
- [x] Require protected ancestor directory evidence and add adversarial tests.
- [ ] Exact-HEAD GitHub CI and real Fedora guest evidence.
- [ ] Independent review and operator merge decision.
- [ ] Signed/package-level provenance and authenticated caller/consent remain future gates.

## NEXT

Verify exact-head CI. Resolve any concrete Fedora guest/fixture discrepancy with narrow evidence-supported corrections, without relaxing SELinux or read-only permissions. Follow on separately with signed OS-package provenance and controlled package updates. Preserve C2z successor ownership.

## DECISIONS

Draft review only. No merge authorization, local machine changes, real credentials, active production service, real NASA or Proton calls, operator consent, or permission grants.
