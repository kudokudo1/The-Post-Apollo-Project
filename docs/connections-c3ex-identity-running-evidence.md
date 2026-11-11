# 🏥💜 C3e-X // Identity running-service evidence consistency (CI only)

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · protected C3e host evidence and replay trust
STAFF ROLE // DOC · original protected Connections developer
ASSIGNMENT // Strict test-only receipt/kernel-observation consistency receiver for the actual C4b Identity Gateway, not C4d fake status host
CONCURRENT OWNERS // C4b #1785 (Fedora Silverblue producer); Identity DOC; C5 consent; original C4d Silverblue
PRODUCTION // HOLD

## IMPLEMENTATION

This adds **four new files** only: a protected C3e-X Python receiver, 15 adversarial tests, a dedicated GitHub Actions workflow and this contract. It does not change C3e-Q/R/U/V/W, C4b, Identity native commands, C5, QML or the workstation.

C4b demonstrated a real Fedora 44 Silverblue **running** signed Identity RPM and four Ed25519-signed UNAVAILABLE responses in disposable VM CI with teardown and rollback. Its newer branch introduced per-receipt Linux SO_PEERCRED and /proc/PID start, UID/GID, cgroup and SELinux checks and an experimental dedicated test domain. These are still observations inside a CI guest, not separately authenticated release/process evidence.

This independent C3e-owned receiving contract accepts one bounded canonical JSON line and **exactly four separate signed receipts**. It is deliberately not a network service or host authenticator. An external caller supplies expected independent test measurements and an independently pinned Ed25519 public receipt key. The module cannot verify whether those inputs were actually obtained or stored outside the guest.

1. Require the Identity **deny-only CI role** and a unique C3e-X schema. Do not reuse C3e-U/V/W fake Connections status-host format. Four records in fixed BEGIN, STATUS, CANCEL, RECOVER order; no extra/duplicate JSON fields, exactly one newline, canonical JSON, 16 KiB maximum.
2. Every record contains a unique encoded 32-byte nonce, the correct CI request ID, before/after process snapshots, and Linux socket peer PID/UID/GID. Both snapshots must match the separately supplied expected test pins: signed RPM, entrypoint and executable SHA-256; executable path, actual service unit, PID, positive kernel start ticks, nonroot UID/GID, exact systemd cgroup, socket path and proposed test-only dedicated SELinux domain. Missing fields, mismatched peer, replacement or process drift refuse.
3. Use the already merged read-only Identity receipt verifier from services/identity/signed_command_receipt_v0.py to check all four Ed25519 signatures under the caller-pinned public key. The signed command, request ID and nonce must match. Every result must be UNAVAILABLE with no created request, one hostInstance and exact signed sequence 1,2,3,4. Reordered, modified, replaced or replayed-in-one-bundle receipts refuse.
4. Return three positive ...InCI flags for protocol consistency, with ALL independently authenticated host, issuer custody, external replay, human consent, credential and production flags FALSE. No actual Linux host process is read, no socket is contacted, no Identity command is emitted, and no privileged system or credential operation is performed.

## HOW TO USE

The dedicated GitHub Actions workflow connections-c3ex-identity-running-evidence.yml runs the 15 adversarial tests on a disposable Ubuntu 24.04 runner with pinned Python cryptography. No Fedora VM, production signer or root access is needed for this CI consistency stage. Do not install or use it as an Identity sign-in gate.

The test fixture generates an ephemeral Ed25519 key and synthetic process snapshots using C4b's proposed running-service field semantics. C4b's current guest CI emits a bounded SERVICE_OBSERVED line and PASS markers, **not** an independent full signed per-command process snapshot. A future C4b-owned host witness adapter must be separately reviewed before end-to-end use.

## VERIFY

- [ ] Exact-head C3e-X 15 adversarial tests.
- [ ] Dedicated workflow and Meta Apollo Grammar checks.
- [ ] Independent Nurse 2 review of exact source/CI head before any merge.
- [ ] C4b supplies independent real host proof and release/receipt signer custody, not ephemeral guest data.

## WATCH OUT FOR

**The process snapshots and report are not independently authenticated.** They are caller-supplied JSON test data. Even perfect internal agreement can be fabricated by the same compromised guest. Parameter names such as independently_measured and independently_pinned_receipt_key are not independently authenticated production evidence. A disposable guest Ed25519 signer also proves only that this test exercised a signing path; do not derive expected trust pins from the report or unsigned guest UART.

This receiver does NOT perform durable nonce consumption across separate invocations; bundle uniqueness is the only nonce repetition check. Previous C3e-R/W uses disposable root-local SQLite, which is not externally rollback-resistant command authorization. A future production adapter must cover complete audience-bound host evidence, an external independently issued and durably consumed challenge and externally enrolled signing authority.

The postapollo_identity_ci_t SELinux type is **only a proposed CI fixture domain** until C4b proves exact enforcing kernel context, negative forbidden-action denial and complete policy removal in real Silverblue. Mere compilation, SELinux enforcing or an unconfined_service_t label is insufficient. Process path, package and module hashes also require real independent installed-source measurements and rechecking on replacement/host loss.

C4b owns real process/SELinux/seat/release evidence; Identity DOC owns native command and adapter integration; C5 owns real one-use human intent. No real user, seat, keys, credentials, provider login, or production authority is created here.

## CHECKLIST

- [x] Current main, Syntagma Hospital protocol, C3e ownership and concurrent worker drafts inspected.
- [x] Add a deny-only Identity-specific receiver and 15 adversarial tests in new C3e files.
- [ ] Verify exact-head CI, request independent Nurse 2 review and merge only under established authorization after gates.
- [ ] Independently sourced C4b release, kernel/process/SELinux/seat host witness and external receipt-key custody.
- [ ] Protected C3e external rollback-resistant challenge, real signed full host evidence and process replacement refusal.
- [ ] C5 one-use human consent, Identity native integration and operator final production acceptance.

## NEXT

After exact-head C3e-X tests and independent Nurse 2 security review, coordinate a new genuine independently authenticated C4b installed-host witness producer and build its protected C3e production receiving contract. **Never promote the CI-only positive flags** or merge other workers' branches under this assignment.

## DECISIONS

DOC role retained. Repository-only C3e test implementation; no local user-machine writes, signer enrollment, protected system changes, operator-grant inference, credential operation, C4b/C4d/Identity/C5 source edit, assumed live Hospital registration, or production activation. Final user acceptance remains separate.
