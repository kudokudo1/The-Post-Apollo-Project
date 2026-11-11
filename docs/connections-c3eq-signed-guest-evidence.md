# 🏥💜 C3e-Q // Signed guest evidence challenge contract (CI-only)

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · Protected host and evidence transfer  
STAFF ROLE // DOC · Original protected Connections development  
ASSIGNMENT // Consumer of C4b-owned guest measurements, without taking guest producer ownership  
C4b HANDOFF // [Issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606)  
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-O #1605 merged: exact signed C3d RPM Python script/unit/D-Bus payload bytes. C3e-P #1610 merged: a *real nonroot Python process* can be observed under Linux by checking process start, executable interpreter inode and script file hash. C3e-N separately validates C3b/C4b installed-origin-compatible evidence and distinct root witness, but neither source-controlled evidence nor a detached JSON status is a signed cross-guest measurement.

C3e-Q defines a bounded **test-only signed evidence receiving protocol**, independent of the C4b guest implementation:

1. The verifier issues a strict 32-byte challenge. The test producer signs an evidence document containing the challenge SHA-256, exact signed RPM SHA-256, signed and observed script SHA-256, interpreter SHA-256, dedicated service PID/start/UID/GID, matching D-Bus owner PID, expected systemd unit, enforcing SELinux marker and explicit negative authority flags.
2. The verifier imports a *separately pinned* disposable OpenPGP public key into its own private keyring, checks a real detached signature, exact signer fingerprint, bounded and nofollow input files, no duplicate/extra JSON fields, the producer's **exact sorted/compact ASCII JSON bytes**, canonical ASCII-decimal start ticks, and the full signed role/identity shape.
3. Independent expected package/script/interpreter fingerprints and expected PID/start must match signed observations. A one-use in-memory challenge is consumed only after successful verification. Duplicate use, false authority claims, changed PID, different key, forged package digest, changed script, disabled SELinux, mismatched D-Bus PID and unsigned edits refuse.
4. The only output is a CI receipt marking the *test cryptographic verification*, with **every real host authentication, installed guest measurement, approval and credential flag false**.

The 23 tests perform actual detached GPG Ed25519 signatures and exercise forged signatures, replay, substitutions, malformed inputs, noncanonical signed JSON encodings, deeply nested parser failure, noncanonical signed and independently expected start ticks, and false permission assertions. This does **not** modify C4b scripts, Silverblue guest, provider credentials, QML broker, or release state.

## HOW TO USE

**2026-11-10 DOC verification hardening:** Keep the existing signer and one-use challenge protocol intact. The receiving parser now refuses noncanonical encodings of the same signed statement and non-ASCII, leading-zero, zero or overlong start-tick strings. Deeply nested JSON and parser recursion are fail-closed, not exceptions leaking into caller execution. This is a **CI-only source test contract**; it does not create a release-signer, a production certificate authority, a C4b runtime witness, or a C5 grant.


GitHub workflow `.github/workflows/connections-c3eq-signed-guest-evidence.yml` runs as an unprivileged user for signing/verification, then reruns C3e-P/N/I tests. Only generated CI keys and evidence are used. No user-machine commands, signing-key enrollment or deployment action.

## VERIFY

- [ ] Exactly 23 signed evidence positive/adversarial tests green on the correction's exact head.
- [ ] Existing C3e-P/N/I runtime/identity/signed recovery tests green.
- [ ] Grammar and signed offline RPM regressions green on exact PR head.
- [ ] Independent security review and operator acceptance separate from CI.

## WATCH OUT FOR

A signed statement is **not attested guest reality**. A compromised guest or dishonest producer with the test signing key could sign false process data. The test signer is generated locally, not enrolled into an independent trust root. **Canonical JSON and predictable malformed-input refusal do not make a dishonest signed guest truthful.** The 4 KiB byte limit on evidence files is separate from the JSON parser's recursion depth; recursion is now explicitly refused. A volatile in-memory challenge has no reboot persistence, durable consumed-nonce ledger, stable issuer or protected enrollment. This checks a cryptographic *message boundary*, not physical/OS origin.

The producer is not implemented here. The C4b-owner must still establish a genuine installed service measurement, bind it to C3b systemd/D-Bus/SELinux evidence, a separately pinned C3e-O signed package, durable anti-replay custody, independently authenticated transfer and C3e-L witness state. Merely handing over signed JSON from an untrusted environment cannot establish the measurement's truth, prevent rollback or authorize credentials.

C3e-Q does not set `signedGuestOriginAuthenticated`, `installedGuestMeasured`, `hostAuthenticated`, `canApprove`, `credentialActionsEnabled` or `productionAuthority` true, even on successful signature verification.

## CHECKLIST

- [x] Recheck merged C3e-O/P and open C2v/C4b handoff issue.
- [x] Preserve C4b guest and C5 consent ownership.
- [x] Implement test signed evidence receiver and volatile one-use challenge.
- [x] Add actual-signature regression suite and CI workflow.
- [ ] Inspect exact-head CI and fix only observed scoped defects.
- [ ] Obtain independently reviewed C4b evidence producer agreement, installed-host provenance and signer-enrollment plan.
- [ ] Obtain operator review and merge disposition, without production activation.

## NEXT / DECISIONS

The next **real integration** is for the C4b owner to produce an actual running-service measurement in the disposable Silverblue guest; C3e-Q must not be used to turn that measurement into production authority. Any externally trusted attestation issuer, persistent nonce ledger, signed canonical package/service/guest binding and C5 human-consent grant protocol are separate milestones.

No local machine writes, production network access, real secrets, release authorization or live Hospital staffing registration.
