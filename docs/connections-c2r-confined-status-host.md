# 🏥💜 Universal Connections // C2r custom SELinux domain experiment

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
ASSIGNMENT // Isolated minimal domain transition and denial proof, C2r  
STAFF ROLE // External Hospital-compatible Doctor (not registered in live Hospital)  
BASE // 250ba7cd91b0e344c4d6316a66c415fad02d06d7  
AUTHORITY // GitHub draft branch and disposable CI only, no operator workstation changes  

## IMPLEMENTATION

C2q PR #1331 merged; in its actual Fedora 44 kernel with SELinux Enforcing the test-only host started as `system_u:system_r:unconfined_service_t:s0`. That is a valid OS/service/D-Bus check but **not** service-specific SELinux isolation.

C2r introduces a **test-only** SELinux reference-policy module defining `postapollo_connections_t` and executable entrypoint `postapollo_connections_exec_t` using Fedora's standard `init_daemon_domain` interface. The policy source is under `tests/connections/c2r_selinux_domain/`. It has no permissive mode, blanket file management, keyring permissions or TCP/network grants. Its required Python-runtime, dynamic-library and D-Bus permissions will be validated by CI.

A separate Fedora 44 builder compiles the policy through the distribution's `selinux-policy-devel` Makefile. The resulting `.pp` is staged through cloud-init into an **offline** official SHA256-pinned Fedora 44 Cloud guest. C2r explicitly installs the module with `semodule -i` only inside the VM, relabels only the test service executable, and keeps SELinux in Enforcing mode.

The test runs the C2o status-only fake process with the existing C2n root-owned unit and D-Bus access policy. The service's SELinux process type must be exactly `postapollo_connections_t`, not `unconfined_service_t`. The test file `/var/lib/postapollo-c2r-ci-denied` contains only public dummy text with owner root and mode 0644 and is labeled `shadow_t` inside the VM. Its content is accessible under Unix DAC; the **service must receive an SELinux PermissionError reading it**, verified by an explicit journal marker before serving GetStatus. This is a negative capability check separate from the normal D-Bus status/denial tests.

## HOW TO USE

No UI change. CPU++ SETTINGS → CONNECTIONS remains the same read-only unverified host inspector. Nothing is installed, activated, authorized or modified on the operator's Fedora Silverblue desktop.

## VERIFY

A valid passing CI run must establish the *same* Fedora kernel is Enforcing, module compilation succeeds, module installation succeeds without permissive fallback, the service executable has `postapollo_connections_exec_t`, systemd starts it in `postapollo_connections_t`, world-readable dummy `shadow_t` content is denied, the reader can call only GetStatus, an unauthorized client cannot call or own the name, and clean service stop releases D-Bus ownership. Verify every gate on the **final commit**, not on an earlier branch run.

Sources: Fedora SELinux independent policy reference (`init_daemon_domain` .te/.fc workflow), https://fedoraproject.org/wiki/SELinux/IndependentPolicy ; Red Hat reference policy quick-start https://access.redhat.com/articles/6999267.

### C2r evidence checkpoint, November 6

The Fedora module compiles successfully using selinux-policy-devel. An enforcing Fedora 44 guest confirmed that the custom policy module installs and that the executable receives postapollo_connections_exec_t. The service *did not* enter the proposed domain in the first completed guest run: it stayed in init_t and the audit log explicitly denied process2 nnp_transition from init_t to postapollo_connections_t while the systemd unit retained NoNewPrivileges=yes. A narrow rule allowing precisely that transition was added, based on the audited denial. NoNewPrivileges has **not** been disabled. Source rule: allow init_t postapollo_connections_t:process2 nnp_transition.

This rule compiled again. Its actual transition and the negative-access test still require a successful guest rerun. The next GitHub runner's Ubuntu apt-get step was still in progress when checked, before the guest test. The workflow has since been bounded with explicit apt update/install timeouts so dependency delays fail visibly. **Do not claim dedicated confinement until the guest journal reports postapollo_connections_t and the negative dummy-read and D-Bus tests pass together.**

Recovery: inspect the latest head of draft PR #1338, check the enforcing-confined-fedora-service job, and search for C2R_SERVICE_SELINUX_CONTEXT and C2R_PASS // DEDICATED_CONFINED_SERVICE_DOMAIN_AND_NEGATIVE_ACCESS_DENIAL. The guest script and boot script now preserve full guest error output and exit codes in the serial log.

## WATCH OUT FOR

The module and package are unsigned temporary test inputs, not an installable production service. A newly defined domain is not automatically a proven complete least-privilege policy. Missing runtime permissions must be fixed with specific reviewed interfaces; do not add `permissive postapollo_connections_t`, domain-wide unconfined access, arbitrary syscalls, credential read, network access or use `audit2allow` blindly. Even a passing negative check covers **only** the particular denied file type tested.

SELinux modules in a throwaway Fedora guest do not prove the operator's live SELinux store, service integrity, Linux package provenance or personal consent. The temporary Fedora builder and QEMU tools live on GitHub's ephemeral runner only. GitHub Actions policy is limited to operator-owned pull requests and checks out without persisted credentials. No NASA API keys or requests exist in this test.

## CHECKLIST

- [x] Verify C2q merged, Syntagma protocols, repo HEAD and competing Connections PRs
- [x] Add custom type + exact executable file-context proposal
- [x] Add compiled module builder and enforcing guest CI
- [x] Add dummy world-readable SELinux denial test
- [x] Compiled Fedora SELinux module and loaded it into Enforcing Fedora guest
- [ ] Prove proper dedicated process domain with NNP transition rule in a new completed guest run
- [ ] Confirm process domain is dedicated and D-Bus remains read-only
- [ ] Confirm SELinux denial is OS-enforced (not merely DAC)
- [ ] Complete final-head GitHub CI and independent review
- [ ] Sign and package executable/policy, implement consent and real protected host

## NEXT

If all checks pass, the next bounded milestone should be policy minimization and adverse tests (no keyring/network/write access), plus controlled signed installation and removal in an immutable Fedora test machine. Production activation remains a distinct operator acceptance gate.

## DECISIONS

Draft review work only. No merges, personal-desktop writes, systemd/SELinux store modification outside disposable VM, live Hospital registration, credentials, API grants, NASA network calls or Quickshell UI changes.
