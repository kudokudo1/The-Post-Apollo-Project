# 🏥💜 Universal Connections // C4b signed confined runtime on Silverblue

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · C4b signed confined runtime in Silverblue
STAFF ROLE // DOC, external Hospital-compatible; live Hospital registration not verified
ASSIGNMENT // Establish whether C4a's signed fake status-service RPM can be explicitly started under the C2r/C3b enforcing service-origin contract on genuine Fedora Silverblue 44
SOURCE BASE // main 30a11bf7ca75dc0d713bf059b52b6bfa19fb3440
AUTHORITY // GitHub-only disposable CI; no local writes, production activation, operator credentials or merge
OWNERSHIP // C4b test lane only; C3b/C3d source, production Connections QML/broker and other rooms remain independently owned

## IMPLEMENTATION

C4a (PR #1464, merged, exact-head CI green) established official Fedora Silverblue 44 ISO, ephemeral signed fake-service RPM verification, first real boot with package in /usr and rpmdb, and real rollback reboot removing the package. The service was intentionally never activated. C3d (PR #1451, merged) proved systemd/D-Bus/SELinux origin and signed RPM files for an explicitly started fake host in an ordinary mutable **Fedora Cloud** VM. C4b is a separate and more restrictive environment.

The C4b opt-in path stages existing C2r compiled custom SELinux policy, pinned dbus-next 0.2.3 wheel (SHA-256 58948f9aff9db08316734c0be2a120f6dc502124d9642f55e90ac82ffb16a18b), C3b origin probe, and existing read-only bus policy client on the existing offline seed ISO. C2t and C3d RPMs are signed in two disposable Fedora builders as before. No signer private keys or network are given to the VM.

Only the dedicated C4b GitHub workflow sets both C4A_SERVICE_RPM_DIR and C4B_RUNTIME_ASSETS_DIR. Normal C2v/C2x and C4a-only tests remain separate and must still pass. The guest copies only the test fixtures into /var, survives the normal C4a staged RPM layer and first real reboot, then:

1. Confirms C4a's signed test RPM file integrity, package ownership, SELinux Enforcing and no-network guest.
2. Installs existing C2r custom SELinux test policy in this disposable guest. It attempts to apply the actual SELinux executable entrypoint label to signed package-owned /usr on immutable Silverblue **without an overlay, remount, copy, permissive or untrusted fallback**. A refusal is a real test blocker, not permission to weaken OS protection.
3. Creates temporary service and test-reader Linux users, an offline pinned Python venv, and a world-readable nonsecret file labeled shadow_t as a negative SELinux control. These exist only in the VM.
4. Requires the signed service unit to be static and inactive before explicit start; reloads the isolated system D-Bus policy and refuses unauthorized name claims.
5. Explicitly starts only the fake read-only unit, verifies its exact Linux user, systemd status, kernel NoNewPrivileges, SELinux confined process domain, and actual denial of the world-readable negative control.
6. Reuses the unmodified C3b kernel/systemd/D-Bus owner/PID/UID/cgroup/executable-parent origin verifier. Requires the permitted read-only GetStatus for one test reader, denies approve/ownership requests, and denies the outsider.
7. Stops the service, verifies D-Bus name release, removes test principals, venv and SELinux module, and requires cleanup before allowing C2v's original rpm-ostree rollback/reboot.
8. After the real rollback reboot, requires signed fake service files absent, no service or name owner, no test users/modules/venv, then removes its /var scratch assets. The host requires explicit runtime markers **in addition to** C4a's exact source-backed two-boot success.

## HOW TO USE

No workstation commands. GitHub workflow: .github/workflows/connections-c4b-silverblue-confined-runtime.yml
Test-only source: tests/connections/c4b_silverblue/guest_confined_runtime.sh
Source contract: tests/connections/test_connections_c4b_silverblue_contract.py

## VERIFY

- [ ] Exact-head C4b shell syntax and deny-only tests.
- [ ] Two signed disposable RPM builders, independently built offline SELinux test module, pinned wheel, C3b origin and bus-policy probe staged without a private key.
- [ ] Real official Silverblue 44 image hash/installer, no-network guest, SELinux Enforcing, independently authorized pending layer and first real reboot.
- [ ] Immutable /usr signed test executable is successfully confined by the existing custom policy without a writable overlay or permissive fallback.
- [ ] Explicit fake service startup in confined domain; actual deny on world-readable shadow_t probe; kernel/systemd/bus process-origin coherence; reader can only GetStatus, outsider denied.
- [ ] Stop/release service, delete temporary policy/users/venv; actual signed RPM rollback and second reboot; verify all signed fake-service and test-state removal.
- [ ] Exact-head C2v/C2x/C4a regression CI unchanged.
- [ ] Independent technical/security review and operator decision.

## WATCH OUT FOR

**Known unverified seam:** immutable Silverblue /usr may refuse a newly installed SELinux entrypoint relabel; policy installation after OSTree composition may not authorize an executable transition. If it fails, diagnose using real CI. Do not use usroverlay, remount read-write, setenforce 0, broad allow rules, relabel arbitrary executables, or silently replace package provenance.

The package is signed by an ephemeral same-builder CI signer, **not** an independently trusted Post-Apollo production release authority. The original user and D-Bus group are test-only, not authenticated human intent or application caller identity. Even successful C4b would not authorize real installation, production service startup, API keys, credentials or provider calls. SELinux policy module is test-only; no use on the operator machine.

C4a PR #1464's independent audit/operator acceptance were not established by this worker. Its already verified merged test technical baseline is reusable, without silently declaring the prior assignment finally accepted.

## CHECKLIST

- [x] Inspect Syntagma and current GitHub branch/ownership; no C4b branch or PR at entry.
- [x] Create new isolated C4b branch.
- [x] Implement explicit opt-in test staging, guest runtime guard, host acceptance, dedicated CI and static contracts.
- [ ] Observe exact-head CI, diagnose/refine only evidence-supported failures.
- [ ] Independent review, operator acceptance; separate merge decision.
- [ ] Separate production trust and consent milestones.

## NEXT

Open draft PR and inspect the earliest C4b CI failure. If the Silverblue immutable entrypoint fails, retain enforcing/immutable guarantees, report the blocker and develop a separately authorized safe policy/OSTree compose strategy. Keep all privileged effects within disposable KVM guests.

## DECISIONS

Proposed C4b CI-only work accepted via operator "continue" after C4a technical results. GitHub-only test modifications; no local machine write, production activation, merge, credentials, provider traffic, security relaxation or ownership transfer.


## RECOVERY ADDENDUM // C4b runtime attribution, November 8, 2026

PR #1480 merged at commit d9e52f49abe8ffb7dc9343d9f04f1177e5574317 **without a passing C4b runtime VM test**. This is not a verified runtime acceptance. The exact-head CI [42453662818](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42453662818) passed the source contracts, isolated signed RPM builders, SELinux policy build, QEMU provisioning, pinned Python wheel, and official offline Silverblue installation. Its guest successfully booted C4a's signed fake status package, validating C4A_PASS // SIGNED_FAKE_SERVICE_BOOTED_FILES_OWNED_AND_INTACT. The additional C4b phase did not emit any C4B_PASS or C4B_FAIL in the available host log. After roughly 23 minutes of guest runtime, the host reported C2V_BLOCKED // SILVERBLUE_LAYER_REBOOT_ROLLBACK_RESULT= with no C4b rollback evidence.

**Unresolved:** There is insufficient evidence to attribute the silence specifically to SELinux policy loading, immutable /usr relabeling, systemd, D-Bus, guest serial writes, or another runtime command. Do not infer the cause from the presence of SELinux kernel messages or the final missing markers.

Recovery adds test-only, bounded C4b command execution, phase/stage markers in a guest-local /var/tmp log, an independent systemd-run observer that relays only disposable VM diagnostics to serial, and explicit host-side last-stage/result logs. The original signed package checks, no-network/SELinux Enforcing, exact pending-OSTree deployment, two real reboot checks, and production deny-only flags remain mandatory. Failure to load the custom policy or relabel immutable /usr is still a hard failure; neither may trigger an overlay/permissive fallback.

**Next verification:** Review the recovery PR's exact-head C4b CI, identify the first failing or timed-out stage, and make no further implementation decisions until that evidence is available. C4a/C2v/C2x regressions must pass again. No production activation, local installation, PR merge, or operator final acceptance is implied.


## RECOVERY ADDENDUM // C4b independent UART evidence, November 8, 2026

The next exact-head diagnostic run on PR #1491, [workflow 42471284668](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42471284668), PASSED source/security tests, KVM and all ephemeral package/policy builds, but the real Silverblue guest **powered off** after the detached worker and monitor had started. The monitor's first three pending-state polls were rejected. This occurred **before** any C4a first-boot or C4b runtime checks and no C4B_DIAG_MONITOR_FATAL was seen on the original ttyS0 serial stream. The log confirms an orderly systemd poweroff but does not identify the requester; the monitor is only one plausible source.

A second, C4b-only, independent QEMU serial port now writes directly to its own host-side file from guest /dev/ttyS1. That device is not used for the existing boot/status acceptance, SELinux, or reboot authority. C4b emits a test-only UART readiness marker, bounded early rejected-pending-state diagnostics, and on monitor failure the existing fatal monitor summary to **both** UARTs best-effort. When the VM fails, the host prints the second UART file separately. The C2v/C2x/C4a-only jobs receive no second UART and keep the original authoritative ttyS0 control path.

A missing second-UART diagnostic marker still cannot prove which systemd component initiated poweroff. If no marker is present, inspect the QEMU UART byte count and test-only guest serial presence before considering any further stage. Do not disable pending deployment guards, bypass network isolation, relax SELinux or call a guest success merely because a diagnostics file exists. Test-only logs contain no production credentials by design.


## RECOVERY ADDENDUM // C4b runtime failure after first real reboot

Merged PR #1491 (`2f10c494`) has a completed **FAILED** exact-head C4b VM run [42476705052](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42476705052). The C4b-only systemd shutdown witness confirmed that RPM-OSTree completed both local signed test package layers, the independent monitor observed the **exact** pending identities and idle transaction, and it requested the real first reboot with monitor exit 0. This eliminates the previous assumption that a still-pending transaction itself caused the shutdown.

The same secondary UART showed `C4B_DIAG_CONTROLLER_FATAL // C4B_RUNTIME_PHASE_FAILED_OR_TIMED_OUT_2` and `SCRIPT_EXIT_1` after the reboot. Therefore the booted C4b runtime gate returned error code 2 and the top-level test controller initiated fail-closed poweroff; that gate's specific reason and stage were lost because its detailed output was only relayed to the original ttyS0 stream and not included in the host's failure extraction. It remains **unproven** whether the actual failing operation was SELinux policy load, immutable /usr relabel, identity setup, systemd, or D-Bus.

The new C4b-only recovery branch adds a read-only bounded UART1 relay of the already-existing `/var/tmp/c4b-runtime-stage` and last 100 lines of `/var/tmp/c4b-runtime.log` when the controller's runtime phase fails. These artifacts are test-only and never authorize package installation, reboot or acceptance. Source tests require the exact UART markers. The original C2v/C2x/C4a and full real-VM requirements remain unchanged.

**Next:** inspect the exact full CI runtime failure line. Patch a demonstrated defect only; leave SELinux Enforcing, signed package integrity, original runtime origin check, no-network guest and two real boots mandatory. Merged #1491 is **not** C4b technical acceptance; no production activation is authorized.


## C4b COMPOSED POLICY CORRECTION // 2026-11-08

The merged PR #1503 exact-head [C4b VM run 42486693794](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42486693794) produced the **first definitive root-cause failure** after real first boot:

\`\`\`text
C4B_STAGE // phase=booted step=POLICY_LOAD_RETURNED
C4B_PASS // SELINUX_POLICY_LOADED_WITH_ENFORCING_KERNEL
C4B_STAGE // phase=booted step=SIGNED_IMMUTABLE_ENTRYPOINT_RELABEL_BEGIN
restorecon: Could not set context for /usr/libexec/post-apollo/connections-status-host: Read-only file system
C4B_FAIL // IMMUTABLE_USR_ENTRYPOINT_LABEL_REFUSED
\`\`\`

This is not a missing RPM or D-Bus issue. The service RPM was correctly signed and layered in an actual immutable Fedora Silverblue 44 OSTree boot, and the custom module loaded with SELinux enforcing. The bug is attempting to relabel immutable \`/usr\` *after* boot. The proper design is to provide the desired SELinux file context at **OSTree composition** time, before immutable boot, rather than to remount, create an unsigned copy, or permit a fallback context.

This recovery creates a **separate, test-only, disposable-key-signed C4b SELinux policy RPM**, without editing the C3d signed fake-host builder or weakening the C2r module. The C4b builder compiles the existing \`postapollo_connections.te\` and \`.fc\` sources into a \`.pp\`, builds a package with exactly one \`/usr/share/selinux/packages/targeted/postapollo_connections.pp\` payload and explicit bounded-purpose \`semodule\` install/uninstall scriptlets, and signs it with an ephemeral OpenPGP key. An independent isolated \`rpmkeys --dbpath\` keyring proves this test signer was not pre-trusted and validates the RPM signature and exact payload before layering.

The offline \`rpm-ostree install --cache-only\` stages **three** local RPMs in one transaction only when C4b is opted in: inert C2t, signed fake C3d service, and signed C4b policy. The authoritative pre-reboot pending-deployment parser checks all **three exact** local NEVRAs for C4b (two remain mandatory for C4a). On first real boot, C4b checks that both packages are owned by their expected RPMs, the module is loaded in enforcing mode, and the immutable signed executable already carries \`postapollo_connections_exec_t\`. The gate never invokes a runtime \`restorecon\` or \`semodule -i\` to correct a wrongly composed label.

The confined service and negative SELinux/D-Bus tests remain compulsory. After the signed service is stopped and disposable users/venv removed, the composed policy **must stay installed until real OSTree rollback**; runtime \`semodule -r\` would conceal whether rollback restored the previous policy. Following the second reboot, the signed service, policy RPM, context module, local keyring and runtime assets must all be absent before acceptance. This policy RPM is **test-only**, not a production package or release-signing process.

**Status:** The structural correction is proposed on a separate recovery branch. Its custom policy RPM spec/scriptlet behavior, label-on-compose result and rollback semantics are experimentally unverified until exact-head real Silverblue CI runs. If composition refuses the package/scriptlet or does not label the entrypoint, fail closed and record the precise test error. No \`usroverlay\`, SELinux permissive mode, unsigned executable replacement, or production activation is authorized.


## C4b first real composed-service test // C3b ancestor refusal, November 8

Exact-head [C4b workflow 42494902346](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42494902346) completed **FAILED**, but established the key technical milestone: a genuine Fedora Silverblue 44 boot contained the three exact test RPMs; the custom policy was installed at OSTree composition, the signed immutable executable was correctly labeled \`postapollo_connections_exec_t\`, the signed service started under \`postapollo_connections_t\` with SELinux enforcing, and the world-readable negative test file was denied. D-Bus unauthorized name ownership was refused. These are actual guest markers, not source-only assumptions.

The next gate emitted \`C3B_FAIL // C3C_UNPROTECTED_DIRECTORY\`, followed by \`C4B_FAIL // DBUS_SYSTEMD_PID_UID_SELINUX_ORIGIN_REJECTED\`. The imported C3b origin probe rejects one or more protected ancestor directories when they are non-root-owned, writable by group/other, not directories, or symlinks. The old log does **not** identify the offending path. We cannot legitimately weaken C3b's proof or declare C4b service-origin acceptance without identifying it.

This bounded follow-up changes **only the C4b test**: if the exact pinned staged C3b probe rejects origin, C4b reads the probe's authoritative \`PROTECTED_DIRS\` list and uses \`os.lstat\` to print the exact violating paths and their owner, mode, directory/symlink status to the guest-local runtime log. The preexisting independent UART1 failure relay captures that log. The diagnostic is read-only, has a strict timeout, does not mutate C3b code or directories, and always preserves the original fail-closed gate.

**Next:** inspect the specific offending ancestor after the next full CI VM run. Any correction must preserve the intended no-writable/no-symlink origin chain or be explicitly reconciled with the C3b owner. If no such correction is compatible with Silverblue, leave C4b blocked. The second real reboot/rollback remains unverified; production stays HOLD.


## C3b Silverblue /opt ownership boundary // exact path discovery

The [real C4b Silverblue run 42496902093](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42496902093) identified **one** precise post-start origin violation: `C3B_FAIL // C3C_UNPROTECTED_DIRECTORY`, and `C4B_DIAG_C3B_UNPROTECTED_DIRECTORY // path='/opt' uid=0 mode=0777 directory=False symlink=True`. A symbolic link always has nominal mode `0777` on Linux; this **does not establish** that the link target is writable or unsafe. The original C3c-protected origin policy rejects all such links, so legitimate Silverblue's ostree directory layout is incompatible. The signed composed immutable host, SELinux enforcing domain and dummy-file denial **passed**; C3b origin/rollback did **not**.

A strict cross-room blocker and proposed fail-closed alternatives are recorded in [C3b/C3c owner issue #1532](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1532). The C4b worker does **not** own or change the C3b checker or its adversarial tests without a specific owner decision. No removal/replacement of `/opt` or production host manipulation is allowed.

This additional **read-only test diagnostic** emits `C4B_DIAG_C3B_OPT_LINK` with the exact `os.readlink('/opt')` string and canonical resolution, plus bounded `C4B_DIAG_C3B_OPT_CHAIN` inode/owner/mode/type observations of `/var`, `/var/opt`, and the resolved target. It runs only **after C3b has failed**, relays into existing C4b diagnostic UART1, never changes evidence supplied to C3b, never authorizes a pass, and does not weaken the original root-owned real-directory requirement. The purpose is to give the C3b/C3c owner exact official Silverblue 44 VM facts before deciding whether a narrow special profile can be justified.

**Acceptance:** The current C4b gate remains red until the C3b owner resolves the documented policy compatibility and real C4b confirms full caller origin plus real second-boot rollback. Passing source tests or capturing a symlink target is not technical acceptance; production HOLD remains.

## C4b boot-composed D-Bus policy / logind rollback recovery candidate // November 9, 2026

**Source:** [C2v/C4b rollback failure #1568](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1568). The genuine full signed Silverblue guest on C2v draft diagnostic head `585fcecc` completed signed host origin/SELinux/negative-client/runtime cleanup but failed the *subsequent* `rpm-ostree rollback --reboot` with `error: Checking systemd inhibitor locks: Timeout was reached`. Read-only `org.freedesktop.login1.Manager.ListInhibitors` calls also timed out. Standard C2v/C2x and signed C4a two-reboot cases passed. The causal role of the C4b runtime `systemctl restart dbus-broker.service` is a **testable hypothesis**, not an established root cause.

**C4b-owned scoped change:** C3d's signed RPM already contains `/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf`, root-owned mode 0644 in the immutable deployment before the genuine first reboot. The system broker can load that installed policy during boot. Rather than unconditionally restarting the broker *mid-guest*, this C4b-only candidate (a) checks the actual installed policy is a non-symlink regular file belonging to the exact C3d signed RPM, owned by root:root mode 0644; (b) checks the already-running D-Bus broker; (c) checks the existing `org.freedesktop.login1` name owner and read-only `ListInhibitors` responsiveness before C4b denial tests and after runtime cleanup; and (d) keeps all actual forbidden name ownership, method denial, C3b MainPID/SELinux origin and service release tests. Failure of any new prerequisite is fatal, not an excuse to restart logind or bypass an inhibitor.

**Verification limits:** The source and its added adversarial static contract are not proof of a repaired rollback. The original C2v authoritative `rpm-ostree rollback --reboot` and its second *real* boot/policy-RPM/keyring-service-absence checks are unchanged by this branch. Passing a source test or first-boot logind check must never emit a full C4b rollback success claim. Only an exact-head, genuine three-signed-RPM/custom-SELinux offline Silverblue CI run proving the second boot and complete removal can do so.

**Ownership:** C4b runtime script, its source contract and this handoff document only. C2v diagnostic draft PR #1571, C3b origin checker, C3e-Q/R/S signed envelope, C5 consent and production connections QML remain untouched. Continue coordinating the separate real signed running-host observation on [issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606) after a verified full lifecycle. No local machine changes, live provider access, merge authorization or production grants.
