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

## C4b in-place D-Bus policy reload correction // November 9, 2026

[Initial boot-composed-policy candidate #1628 CI run #42623191236](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42623191236) **FAILED** during the genuine C4b **first** boot. The new `LOGIND_DBUS_RESPONSIVE_BEFORE_C4B_DENIALS`, denied name ownership checks and installed C3d policy-file provenance passed. But explicit start of the actual signed confined service failed with `C2O_STATUS_ONLY_START_FAILED: DBusError` at `EXPLICIT_SIGNED_FAKE_SERVICE_START_BEGIN`. No actual OSTree rollback command or second boot occurred. This proves removing the C4b runtime D-Bus restart **alone** was not sufficient: the new signed name policy was present on disk but could not be assumed effective in the currently running broker.

**Narrow correction on the same C4b draft branch:** invoke a bounded `systemctl reload dbus-broker.service` once after validating the signed policy and before the adversarial D-Bus clients or explicit service start. An in-place configuration reload is supported by dbus-broker and applies new policy without restarting its bus socket or discarding existing connections. Require **identical broker MainPID and kernel process-start ticks** before/after reload, as well as the identical `org.freedesktop.login1` D-Bus unique owner and responsive `ListInhibitors` calls on both sides. If reload is unsupported, returns failure, replaces the broker, or logind loses ownership/responsiveness, **fail immediately**: do not restart the bus, bypass inhibitors or grant production authority. Keep the existing negative ownership/method checks, C3b origin verification, SELinux Enforcing and original two-real-boot rollback gate.

**Next evidence required:** a new exact-head real official Fedora Silverblue 44 offline VM run must prove signed C3d service starts under the installed SELinux policy **and** `rpm-ostree rollback --reboot` completes genuine reboot/removal. Passing source contracts does not prove either. C2v diagnostic PR #1571 remains separate, and C4b owner controls only C4b runtime, test and recovery note here.

## C4b true running signed Python host measurement // November 9, 2026

The [real signed Silverblue C4b CI #42630365309](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42630365309) **passed** complete signed three-RPM first boot, active SELinux/C3b/negative service-client checks, the actual `rpm-ostree rollback --reboot`, and independent second real boot signed package/policy/keyring removal. [C4b #1628](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1628) merged at `527eabb8`. Neither that baseline nor the following measurement code grants production credentials.

**Next C4b-owned development seam requested by [DOC #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606):** observe the *actual* signed C3d Python service during the genuine disposable Fedora Silverblue 44 first boot, **after** the canonical C3b OS service/D-Bus origin checker accepts and **before** C4b stops it. This is CI-source instrumentation and a guest self-report, **not** independently authenticated remote attestation.

**Implementation:** C4b's already-owned signed policy prelayer gate retains an exact SHA-256-matched copy of the public C3d RPM under root-only mode-0700 `/var/lib/c4b-runtime-assets/`, mode 0600, after C4a's separately existing signature verification; this avoids changing C2v's common ISO or reboot controller. The guest then re-verifies that immutable RPM against the **already-enrolled disposable C4a isolated test keyring**, queries its signed RPM header's three SHA-256 file digests and exact file allowlist, compares actual root-owned on-disk script/unit/D-Bus files against them, and independently obtains the active kernel process-start tick, all UID/GID identities, NoNewPrivileges and SELinux domain. The D-Bus daemon itself supplies the unique owner PID and Unix UID via GetConnectionUnixProcessID/GetConnectionUnixUser, independently checked against the same live systemd MainPID. It compares the kernel /proc/PID/exe interpreter inode to the expected /opt-venv executable and hashes the executable separately from the original signed 0555 Python script. The exact `--read-only` invocation and PID/start stability are required across observation. Any failure aborts C4b *before* teardown or any rollback success.

**Output:** one bounded single-line `C4B_OBSERVED //` JSON measurement record, plus `C4B_PASS // SAME_C3B_SERVICE_SIGNED_RPM_SCRIPT_AND_INTERPRETER_OBSERVED` on complete success, both in the existing disposable guest test log. These contain signed-RPM and running-script hashes, interpreter SHA256, same kernel systemd and D-Bus PID/start/UID/GID, unit and enforced domain, but **no secret, no private key, no signer, no challenge nonce and no identity/credential authority**. All `signedGuestOriginAuthenticated`, `evidenceCryptographicallyAttested`, `hostAuthenticated`, `canApprove`, `credentialActionsEnabled` and `productionAuthority` fields remain **false**.

**Limitations:** the RPM test signer and isolated keyring are disposable self-generated fixtures; they are not independent production release or host-enrollment roots. A hash of the script *on disk* is not a guarantee of exact Python source loaded in RAM; command line bytes are mutable process memory. A plaintext serial/guest log cannot be cryptographically trusted as the actual guest's remote evidence. DOC remains responsible for future separately enrolled verifier challenges, signed evidence receipts and independently rollback-resistant nonce custody. The C3e-P source is **not modified or reproduced as an imported dependency**; this C4b guest observation is a separate bounded implementation on the real running service.

**Acceptance:** verify source contracts and exact-head full C4b KVM CI, including the new marker **and** existing second real boot and keyring/policy cleanup. Only then hand precise schema/measurement field evidence to DOC. No changes to C2v controllers, C3b origin source, C3e protected work, C5 user consent or production QML; no local workstation install or production activation. PR review, merge decision and operator acceptance remain separate.

## C4d bounded actual UART observation export // November 9, 2026

**Reason:** [C4c #1646](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1646) merged with a genuine [signed offline Silverblue 44 CI PASS #42638232336](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/42638232336). It emitted one actual `C4B_OBSERVED //` report from the verified signed running Python host in its guest-local runtime log, but the successful C2v host workflow did not print that raw guest UART record or retain the ephemeral serial file. Protected DOC [issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606) needs the **one actual observation** for C3e-U's separate diagnostic compatibility analysis, not another synthetic example.

**Owner-only mechanism:** C4d adds a small C4b CI source-side reader in `tests/connections/c4b_silverblue/capture_guest_observation.py`. It starts alongside the **unchanged** original C2v `boot_official_silverblue.sh` command, reads (never writes) the current disposable QEMU `$RUNNER_TEMP/c2v-silverblue-*/guest-serial.log` before C2v's preexisting cleanup removes it, and accepts only a bounded exact C4c `C4B_OBSERVED //` JSON record. Required string/boolean schema, script-vs-running SHA, same D-Bus/systemd PID, nonroot UID/GID, nonzero kernel start ticks, `selinux_enforcing=true`, and **all six production authority flags false** are checked. Duplicate identical UART relays collapse to one logical record; conflicting, forged, oversized, missing, altered and privilege-claiming records fail closed. The source-side synthetic tests include duplicate/symlink/missing/failed-lifecycle and live-append negatives. No guest process is started or authorized by the reader.

The original signed C4b guest control flow, C3b OS identity, C4a/C4b signer checks, network isolation, SELinux and `rpm-ostree rollback --reboot` remain completely unchanged. The C4b workflow writes a distinct `original-c2v-result` PASS/FAIL completion flag **only after** the original C2v command returns, then the reader checks both that PASS and the real guest's C3b origin, denied-client, signed C4c measurement-complete and second-boot rollback UART markers. Failure of either source rejects the entire job. On **complete PASS only**, `actions/upload-artifact@v4` uploads exactly one root-private captured `C4B_OBSERVED.txt` line, with a three-day retention, no guest console dump and no key material.

**Trust boundary:** This is a CI-source capture of **plaintext guest telemetry**. A malicious guest/controller may forge serial bytes; a matching schema or GitHub-hosted artifact does not cryptographically authenticate physical host origin, nor does it import the observation into C3e-Q/R/S trust. The C3e-U consumer must use independently supplied expected signer/package/identity pins; no automatically trusted production identity, anti-replay guarantee, signer enrollment, consent or credential permission results. All observations are deny-only.

**Verification:** Require the exact C4d CI source tests, complete actual official offline Fedora Silverblue 44 signed three-RPM boot, actual service measurement, genuine second reboot signed package/SELinux policy/keyring cleanup, and an inspectable **one-line** artifact on the exact PR head. If serial capture is unavailable or its markers disagree, the workflow fails even if the underlying C2v test returns 0. No modifications to shared C2v controller, C3b origin, C3e protected modules, C5, user workstation, or production QML. Draft/independent review and operator acceptance remain separate.
