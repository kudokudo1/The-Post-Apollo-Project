# 🏥💜 Connections → Hospital // Isolated staffing transport preflight

**PATIENT:** The-Post-Apollo-Project (Connections)  
**ROOM / ASSIGNMENT:** Isolated source-only Session/Doctor transport preflight, operator-authorized 2026-11-19  
**ROLE:** External Hospital-compatible DOC, no verified live Hospital registration  
**BASE:** Documentation-only draft PR #2077 at \`72944759e96286c94d5a1085c593977c6f0648e9\`  
**COMPATIBILITY:** Hospital protected-writer draft PR #133 at \`ee1dc74056fbd2c849d3391e3148b003514b2932\` (pinned in CI)  
**SECURITY STATUS:** DENY-ONLY, not an installed native issuer, signer, Polkit service, or authorization.

## IMPLEMENTATION

Added \`services/connections/hospital/staffing/StaffingTransportPreflight.py\`, a stand-alone, uninstalled Python source module. It can form the exact eight-field canonical Hospital staffing COMMIT from (a) an **original** canonical PREPARE, (b) the protected writer's writerInstance, and (c) canonical signed-envelope bytes **as already supplied by a separate future signer**. It never signs, verifies a private signing key, opens a source DB, connects to a named socket, grants a session or launches a native service.

Admission is intentionally split into separate checks:

- Complete PREPARE must have exactly \`schema,kind,action,roomId,intent,requestNonce\`, the staffing schema and either \`SESSION_ATTACH\` or \`DOCTOR_SUCCEED\`. The COMMIT must keep those original fields and add exactly \`writerInstance,signedEnvelope\` with \`kind=commit\`.
- Signed-envelope bytes must be \`1..8192\`. The unpadded Base64url encoding of 8192 bytes is **10,923 characters**. The helper checks only canonical envelope syntax, exact fields, signed operation/request nonce/scope/writer-instance claims and signature *shape*. It cannot verify the Ed25519 signature, native operator seat or trust in this package. The Hospital writer must independently verify all signing and source/graph/revocation constraints inside its source-owned transaction.
- The fully serialized canonical COMMIT must be \`<=16384\` bytes **including** original intent, writer instance, field names and encoded envelope. A frame exceeding 16384 is refused before any send. No trimming, splitting, unreviewed compression, alternate action or 8 KiB Room-parser fallback.
- \`observe_kernel_packet()\` is a read-only Linux \`SO_PEERCRED\` versus \`SCM_CREDENTIALS\` witness for an *already-connected* AF_UNIX/SOCK_SEQPACKET descriptor. It requires \`SO_PASSCRED\` to be armed before the packet is sent; refuses wrong peer UID, inherited FD sent by another process, oversized/truncated packets and wrong socket type. It takes a test-only \`expected_uid\` and does **not** validate current installed signer release, logind, Polkit or runtime authority. It is NOT a production peer authenticator and is not reached from any service.
- \`run_native_issuer()\` always refuses. No listener, systemd unit, operator UI, grant issuer, root key, SELinux change or runtime binding is present.

## VERIFY

\`.github/workflows/connections-hospital-staffing-transport-preflight.yml\` checks out both this draft and **exact Hospital #133** at its fixed source SHA. Tests compare all request/COMMIT fields, frame budgets, grant size and staffing domains directly to the Hospital implementation. Disposable, generated synthetic fixture signatures are never treated as valid authorization.

Tests cover complete raw 16,384 versus 16,385 boundary; decoded envelope 8,192 versus 8,193; large supplied intent yielding an oversized full COMMIT despite a fitting envelope; changed PREPARE nonce/scope/operation or writer instance; foreign Room grant domain; invalid signature shape, noncanonical JSON and unsigned unknown fields; native issuer hard refusal. Linux kernel tests use actual process credentials with socketpair, wrong UID, inherited descriptor sent by a forked process, wrong socket type, missing pre-armed PASSCRED and oversized/truncated packets.

A \`16,384\`-byte **syntactically invalid** dummy packet is admissible only to the *size-only* budget check. The real Hospital parser and signed verifier must still reject invalid requests. The deliberately oversized Bed fixture only exercises pre-send length refusal; it is **not** represented as valid Hospital Bed scope.

## WATCH OUT FOR

The future Connections issuer must receive an independently verified C3e/C4b signed release identity covering actual installed Python program/unit, enroll a distinct staffing signing key, establish root policy antirollback and correct active login1/Polkit **human-visible** consent. A matching executable ELF fingerprint alone may prove only the Python interpreter. Signature shape is not cryptographic verification. The Hospital writer owns protected transaction and candidate schema v13 migration, origin/replay admission, nonce consumption and receipts.

**Unapproved:** native service/socket path, installed UID/GID/SELinux policy, exact service READY handshake deployment, approved signer key custody and public enrollment, real operator review, protected database v13 cutover and old-writer fencing, native backup/rollback and production acceptance. Production Session/Doctor and Hospital Burn remain disabled; Room Trash/Restore issuer remains untouched.

## CHECKLIST

- [x] Operator approved isolated **source-only** framing/peer preflight.
- [x] Preserve separate source docs in parent PR #2077 and distinct native issuer ownership.
- [x] Compose exact bounded candidate COMMIT with separate envelope budget.
- [x] Source tests against pinned Hospital #133 and Linux socketpair identity.
- [ ] Verify exact-head CI.
- [ ] Independent Connections issuer-owner review.
- [ ] Owner/operator decisions on actual trusted native signer, seat, key, release, receipt and writer/DB migration.
- [ ] Separate authorization for merge, host install and production activation.

## NEXT

Review the exact source against Hospital owner and Connections issuer owner. Keep this draft stacked on #2077. If approved, the next **separately authorized** source-only package is protected native request/receipt identity binding and explicit protocol versioning, not installation.

## DECISIONS

No changes to existing \`HospitalNativeIssuerService.py\`, C5-H2, Hospital #133, C3e, native Polkit, installed keys, local machine or live Hospital records. This preflight neither grants nor asserts Hospital staffing authority.
