# 🏥💜 Connections C3e-T // Owner-invokable running-service observer CLI

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · protected installed-host evidence handoff  
STAFF ROLE // DOC · Protected Connections development  
ASSIGNMENT // Expose existing C3e-P real-process observer as an opt-in bounded CLI for the C4b-owned accepted guest lifecycle  
CONCURRENT OWNERS // C4b/C2v Silverblue guest/rollback; TASKS C5 consent  
DEPENDENCY // C4b #1628 now merged; actual signed offline Silverblue guest workflow #42630365309 SUCCESS; C3e-O/P/Q/R/S on main  
HANDOFF // [Issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606)  
PRODUCTION // HOLD

## IMPLEMENTATION

The previously blocked C4b real signed Silverblue boot and rollback lifecycle has now passed, including its signed fake service, real enforcing SELinux, actual C3b service origin/DBus/identity, stop/cleanup and official rollback. However, that workflow does not export a separately verified **running installed Python script measurement** for the protected C3e trust receiver.

C3e-P already implements the root-only, nofollow, 0555, real /proc process interpreter+PID/start/UID/GID and script digest observation. C3e-T does **not** invent another host process or duplicate this verifier. It adds a small **CLI adapter** that the C4b owner can explicitly opt into staging and invoking from the established guest stage after:

`C3B_OS_ORIGIN_VERIFICATION_BEGIN` and `C4B_PASS // EXACT_RUNTIME_ORIGIN_AND_DENY_ONLY_CLIENT_CALLS`, **before** `EXPLICIT_SIGNED_SERVICE_STOP_BEGIN`.

The CLI accepts only expected service PID/start/UID/GID, the exact interpreter/script paths and the independently verified signed C3d RPM script SHA-256. It runs existing C3e-P, prints one bounded JSON observation or a single fail-closed refusal status, and returns nonzero on failure. It never grants, approves, opens an external provider, installs a package, starts a daemon, writes a file or modifies the C4b source.

### Future C4b owner-controlled invocation

The owner would stage **both** `C3ePRunningPythonSource.py` and `C3eTGuestObserverCLI.py` under the same root-owned protected guest test asset directory, then run the opt-in CLI as root in the existing signed boot guest with `GITHUB_ACTIONS=true` and `POST_APOLLO_C4B_TEST_GUEST=1`.

The owner must independently calculate these expected inputs from verified source, not from the inspected service:
- `--pid`: current verified C3b systemd MainPID (also matched to D-Bus owner)
- `--start-ticks`: that same PID's kernel /proc start tick
- `--uid`, `--gid`: installed dedicated service account
- `--python`: `/opt/postapollo-c2o-venv/bin/python3`
- `--script`: `/usr/libexec/post-apollo/connections-status-host`
- `--signed-script-sha256`: extracted script digest pinned by C3e-O's isolated signature verification of the actual signed C3d RPM

There is deliberately **no production approval field** and `installedGuestMeasured:false` even on a real guest-path observation. The result would be a bounded in-guest diagnostic, not remotely authenticated evidence.

## HOW TO USE

The DOC workflow `.github/workflows/connections-c3et-guest-observer-cli.yml` exercises the CLI with an actual separately running nonroot Python test script in Ubuntu GitHub CI. It tests valid identity/bytes and 11 negative/default-deny cases. The C4b worker decides whether to stage this read-only tool in its existing guest; this PR does not change that worker's guest runner, network, installed service, rollback or cleanup.

## VERIFY

- [ ] All 12 C3e-T CLI tests pass on exact head, including real process and negative guest-origin case
- [ ] Existing C3e-P real process and C3b origin regressions pass
- [ ] Meta Apollo Grammar, C3e offline signed RPM/root admission regressions pass
- [ ] C4b owner independently reviews the invocation location and signed-payload pin source
- [ ] Operator final PR disposition and C4b integration acceptance separately

## WATCH OUT FOR

This is **not C4b signed guest attestation**. The command-line pins are arguments from the caller; the producer must own and verify their source. A printed JSON result can be forged by a compromised guest/controller; /proc/PID/cmdline is mutable and matching disk bytes does not prove which Python source is loaded in memory. No external attester key, independent trust enrollment, durable rollback-resistant custody, guest-to-witness authentication, operator human consent or real provider account exists in this tool.

Do not treat `observedPathIsC4bGuestCandidate` or `script_file_matches_supplied_signed_payload` as `hostAuthenticated` or C5 approval. Even a successful real in-guest invocation remains diagnostic until separately authenticated by an owner-approved proof transport. The C4b owner controls any guest insertion and all actual rollback tests; this DOC PR must not rewrite those files.

## CHECKLIST / NEXT / DECISIONS

- [x] Reconcile merged C3e-S and C4b #1628 genuine second-boot rollback PASS
- [x] Avoid duplicate script verification: reuse C3e-P existing process code
- [x] Add owner-invokable CLI, real nonroot CI tests, exact bound denial output
- [ ] Exact-head CI, independent review and operator PR disposition
- [ ] C4b owner explicitly stages and uses CLI during the same C3b-verified running service, verifies separately signed RPM script pin and preserves second boot rollback
- [ ] Independent attestation producer, signed challenge, durably protected nonce custody and C5 consent remain separate production gates

**Decision:** main-based, additive DOC source and CI only. No local machine modifications, guest scripts, production keys, real provider calls or live Hospital registration.
