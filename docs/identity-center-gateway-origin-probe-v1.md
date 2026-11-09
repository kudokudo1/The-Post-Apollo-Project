# Identity Center // Signed enrollment and live gateway process origin probe V1

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Sign-In native host integration, external Hospital-compatible; no verified live registration  
**DOCTOR / PROVIDER //** ChatGPT / OPEN AI // CHATGPT  
**STAFF ROLE //** DOC-compatible implementation contributor; independent security and operator acceptance remain required  
**ASSIGNMENT //** Bind the merged Ed25519 signed Identity Center native client to separately signed release/key identity and actual Linux process evidence, without granting authentication  
**BASE //** `48640154239f01669362bb3ed47b84f9a2cce312`  
**PERMISSIONS //** Bounded GitHub source/tests/CI/docs in the Identity Center client lane. No user Fedora modification, installed service/package, signing-key custody, production IdP login, C3e/C4b/C5 ownership changes or auto-merge.

## IMPLEMENTATION

The merged [#1705](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1705) client verifies **Ed25519 command receipts** and a supplied trusted-server callback, but the client still lacks actual independently enrolled **Identity Center** installed gateway identity. The C3e-M/P tests prove relevant origin-verification mechanisms for a **different test Connections status service**; they do not provide production authorization or automatically establish our gateway process.

This V1 adds an **actual, read-only, purpose-specific signed gateway enrollment and Linux process probe**:

- `services/identity/signed_gateway_origin_probe_v0.py`: a pinned *separate release-root* Ed25519 public key verifies a canonical, strict exact-fields policy signature with a domain separator, explicit `post-apollo.identity.native-command-gateway.v0` purpose, epoch/release floor, installed entrypoint path and SHA-256, Python interpreter path, process UID/GID and **SHA-256 of the exact receipt-signing Ed25519 public key** already independently pinned by the command client. The policy root and public key must be supplied from separately protected enrollment, **never from socket JSON**.
- Its `SignedGatewayOriginProbe` also requires **expected PID and process-start ticks supplied by an independent launcher/witness**. Neither can be learned from the client's current kernel socket credentials. On each inspection it compares the *connected kernel SO_PEERCRED* PID/UID/GID to the pins, checks Linux `/proc/PID/stat` start ticks before and after, all four effective/real/saved/filesystem UID/GID fields, the executing interpreter inode via `/proc/PID/exe`, exact `/proc/PID/cmdline` entrypoint arguments and the actual opened **no-follow, bounded, hashed** script bytes. In installed mode, only an identity-scoped root-owned path under `/usr/libexec/post-apollo/identity/` with root-owned non-group/world-writable ancestor directories is admitted. Existing process identity, signer key and release root are independently bound to the same policy.
- Result is a **read-only `GatewayOriginObservation`**, with `production_authority: false`, `can_begin_sign_in: false` and `can_connect_provider: false` even when all physical observations match.
- `services/identity/desktop_signed_command_client_v0.py` adds optional `enrolled_origin_consistent(KernelPeer)` as an **additional rejection gate**, never a replacement for `trusted_server_peer`, `active_seat` or pinned command-receipt signatures. If the enrolled-origin callback rejects or fails, the native command client faults permanently. If absent, its original stricter mandatory independent peer/seat/signature checks remain. This is a small, backwards-compatible native-client seam for independently reviewed deployment.
- New live Linux tests spawn an actual disposable Python child and verify signed policy/real `/proc` PID/start/interpreter/argv/script bytes; test wrong release signer, wrong receipt key, wrong role or release floor, forged/mismatched PID/UID/GID/start, modified script, symlink and command-line injection. The existing signed real gateway test adds a negative enrolled-origin transition: no BEGIN when false, and a subsequent false revokes further client commands without allowing a boolean flip to recover it.
- CI runs both test sets alongside existing real native signed gateway/PKCE, unsigned-host compatibility, original Identity lifecycle and CPU++ default-deny suites. **No QML or connected provider code changes.**

## HOW TO USE

**No new desktop operation.** CPU++ → SETTINGS → CONNECTIONS remains the current read-only interface; Sign In, Cancel and Retry remain disabled.

Native integrator/independent security owners should provision an independently signed, purpose-scoped enrollment for the actual **Identity Center gateway** with approved release root/epoch/sequence, exact 0555/immutable installed Python entrypoint SHA-256 and approved receipt-signing public-key digest. The service supervisor/witness must supply the separate exact active PID and start-tick pins. The native client can then use `probe.consistent` as an **additional** negative guard, retaining independently verified kernel peer/seat checks and pinned receipt signature verification. **Do not self-sign a manifest inside the client** or accept a test receipt/key/script path from the socket. Do not install this test probe on the operator's Fedora workstation without separate explicit local-write approval.

## VERIFY

`tests/identity/test_signed_gateway_origin_probe_v0.py` exercises real `/proc` evidence on a spawned disposable Linux Python process, using separate ephemeral Ed25519 release-root and host receipt keys. The process script is not a production signed install. `tests/identity/test_desktop_signed_command_client_v0.py` exercises additional enrollment-denial behavior on the actual signed native client/server socket.

**Actual CI success alone proves process-observation code and signature-binding tests**, not live production host provenance. A real signed RPM/build/installed package plus independent witness PID/start/systemd/SELinux/seat, protected signer custody and C5 per-command consent must be independently verified before any production admission.

## WATCH OUT FOR

- **Core limitation:** comparing bytes of an installed Python script to a signed digest does not establish all imported modules, interpreter libraries, running Python memory, SELinux confinement or genuine signed installed RPM. A root-owned path and signing-key digest are necessary evidence, not a complete attestation. A process may load dynamically; it is not made trustworthy by a passing user-space probe alone.
- Test mode permits a disposable user-owned script so CI can test adversarial real process observations. **The test mode is never a production identity or authorization grant.** Production-grade acceptance must be independently implemented/approved with installed host and protected witness evidence, not just turn a flag on.
- The policy root and signer public keys, expected process PID/start and release floors must be securely pinned from independent owners. A malicious process that supplies *all the expected values* can make its own observations match. The new native guard only adds denial evidence; it cannot create authority.
- The original real signed command client and gateway remain experimental. C3e/C4d's signed guest processes are **not** the Identity Center gateway; C5 synthetic approval fixtures are **not** real operator consent.
- A signed `AUTHENTICATED` response remains a bounded host phase, not a QML/provider grant. The existing (HostBoundary.offline()) policy must not be weakened and provider actions remain prohibited.
- Do not interpret CI-only `production_authority: false` as an error to flip after passing a test. Only operator-approved independent installed host enrollment and actual consent can change the live production trust model.

## CHECKLIST

- [x] Recheck `main`, merged #1705, active owner PRs, Syntagma AGENTS/Hospital and C3e installed-host evidence limitations
- [x] Add purpose-specific release-root-signed Identity gateway policy binding installed script and receipt public-key hash
- [x] Add actual Linux PID/start/UID/GID/interpreter/cmdline/entrypoint digest observation, false authority
- [x] Allow an optional **additional** enrolled-origin rejection gate in the existing signed native client
- [x] Add real Linux child-process signer/swap/injection tests and native signed client-denial tests
- [ ] Exact-head CI, correction and review
- [ ] Identity Center/C3e/C4b owner approves independently signed installed actual gateway, supervisor PID/start and witness evidence
- [ ] Real active logind + reliable Sway/compositor lock signal, protected signer key custody, C5 per-gesture consent
- [ ] Operator final merge/acceptance and controlled native deployment
- [ ] Safe CPU++ action adapter, first real sign-in and provider-specific authorization

## NEXT

**Turn the process-observation seam into a verified installed Identity Center release and protected execution path**, under the actual C3e/C4b/C5 ownership approvals: independently enrolled signing root and signer public key, immutable/signed package, exact running PID/start with independently checked witness and systemd/SELinux scope, actual seat and one-use operator intent. Then integrate the attested native client with CPU++ using an owner-approved token-free capability channel. No production QML authorization or provider login before those dependencies and native negative tests are accepted.

## DECISIONS

Develop this narrow, read-only evidence/denial component inside the existing Identity Center native client lane. Do not modify separate Connections status host or C3e/C4b/C5 worker files, invent a new OAuth host, create local keys/services, enable credentials, merge PRs or claim live Hospital registration. Operator retains final acceptance. **Recovery:** this document, V1 branch/PR, [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662), merged [#1705](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1705).
