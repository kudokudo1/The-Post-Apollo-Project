# 🏥💜 DOC 4 // Hospital C5-H7 native consent-producer origin boundary

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5  
**STAFF ROLE:** DOC 4 · external Hospital-compatible, no live registration  
**ASSIGNMENT:** Candidate native operator-consent producer ingress, source/CI only  
**PX OWNERSHIP:** protected writer #130/#133, separate repository and review  
**DEPENDENCY:** C5-H6 draft #2268's future exact-review v2 diagnostic reference  
**PRODUCTION:** HOLD

## IMPLEMENTATION

The actual native C5-H4 issuer refuses signing after Polkit and before
private-key loading. The C5-H6 draft adds PX writer-instance/policy-expiry
context to a *diagnostic* exact-review v2. Neither produces a trusted
native display or operator confirmation.

C5-H7 adds an **isolated, test-only** candidate native producer packet
origin boundary. It reuses the source issuer's existing Linux
`SO_PASSCRED`/`SCM_CREDENTIALS` packet guard rather than silently
creating a second credential parser. The CI tests demonstrate:

1. `SO_PEERCRED` identifies the process that created/connected a Unix
   socket. After an endpoint FD is inherited by a child, that initial
   identity remains associated with the socket.
2. `SCM_CREDENTIALS` on each actual `SOCK_SEQPACKET` packet can identify
   the sending process. A packet sent from that child must NOT be
   misrepresented as coming from the original socket-opening parent.
3. A same-process packet may pass the kernel origin check. That proves
   only packet sender consistency, **not installed release enrollment,
   actual screen visibility, active unlocked seat, genuine human gesture,
   independent one-use history, or protected PX mutation authority**.

A diagnostic candidate envelope carries a provisional
`postapollo.hospital.c5h7.untrusted-producer-packet.v1` schema with a
reference to C5-H6's **test-only** v2 review schema, nonce, writer
instance, operation scope, user/seat/host, claimed producer PID/UID/GID/
start ticks, release digest, history digest and timing/gesture claims.
It checks exact canonical JSON types, bounded size and cross-origin
fields. However, those fields and timestamps are **all caller-controlled**.
Even when the claimed PID/UID/start ticks match a supplied kernel tuple,
every trust/consent/signing/production flag is permanently `false`.

The `authorize_human_consent` entrypoint always raises
`C5H7_INDEPENDENT_NATIVE_CONSENT_PRODUCER_NOT_ENROLLED`.
The actual production issuer **never imports this module**. No new
listener, service, QML callback, root policy, key, signer or real packet
provider is created.

## HOW TO USE

Run the C5-H7 GitHub Actions workflow on the draft PR. Its disposable,
unprivileged Ubuntu runner creates local Unix socketpairs and a short
Python child process that inherits one FD. The parent observes actual
Linux peer and per-packet sender identity, and verifies the child packet
is rejected when its PID differs from the original peer.

There is nothing to enable in Post Apollo or on the workstation. The
test does not communicate with the Hospital instance, read private
records, spawn a real native consent agent, open SQLite or mutate PX.

## VERIFY

Required cases:
- Well-shaped self-consistent but fabricated consent packet still cannot
  enable issuer signing or a Room action
- Crossed PID, UID, GID and process start tick are distinguished
- Forged release fingerprint, history head, display/click/expiry
  claims cannot create identity or consent
- Wrong audience, old schema, unknown authority fields, noncanonical
  JSON, duplicated fields, boolean numeric spoofing and bad nonces fail
- Actual same-process `SCM_CREDENTIALS` matches source but remains HOLD
- An inherited `SOCK_SEQPACKET` FD used by a different Linux child PID
  fails the existing issuer's per-message credential guard
- Truncated/missing/forged ancillary credentials are refused
- Native issuer still has the unconditional C5-H4 signing denial

These tests are **kernel transport observations only**, with no trusted
native renderer or independent custody.

## WATCH OUT FOR

A kernel PID/UID/GID and `/proc` start tick do not authenticate an
installed executable release, an input device event, a composited
Wayland surface or what the human saw. Even a valid signed candidate
envelope would not prove those things without a separately trusted,
enrolled producer and actual observed display/gesture mechanism.

The H7 diagnostic's future-facing schema is explicitly provisional,
not a production wire format or owner-approved evidence standard.
C5-H6 remains a separate unmerged draft until independent review and
operator merge disposition. This H7 PR does not import or alter it.

The strongest unresolved boundaries remain:

- **DOC 1:** independently selected root/release/witness and current
  antirollback history custody, enrollment/revocation and host identity
- **Trusted display owner:** actual protected operator-visible exact
  Room/revision/nonce/writer review and explicit gesture at the active
  unlocked seat; safe cancellation, focus/lock/display races
- **PX writer owner:** one-use protected original request and grant,
  cross-rollback history membership, durable unknown-outcome handling,
  all installed legacy writer fencing and exact Room COMMIT
- **Operator:** approve trust architecture, owner responses, native
  installation and final production acceptance

These are decisions awaiting owner/operator approval, not requirements
satisfied by this PR.

## CHECKLIST

- [x] Inspect C5-H5/H6 and protected PX source ownership
- [x] Reuse the actual existing C5 issuer per-message kernel credential guard
- [x] Add candidate origin/claim denial reference and adversarial Linux CI
- [ ] Exact-head C5-H7 CI
- [ ] Independent Nurse 2 pre-merge source review
- [ ] Retrospective Nurse 2 review of merged C5-H5
- [ ] Pre-merge Nurse 2 review and operator disposition on C5-H6
- [ ] DOC 1/PX/display-owner consent producer and custodian agreement
- [ ] Installed native source/recovery acceptance and operator production approval

## NEXT

Submit the exact-head CI to Nurse 2 for the C5-H7 review. Ask the
relevant owners to ACCEPT, REVISE or HOLD the independently enrolled
native producer, display/gesture, external custody and PX one-use
admission responsibilities before any authorizing native implementation.

## DECISIONS

No code from C5-H7 is imported by the production issuer, no runtime
enrollment or consent is granted, and no PX source, local workstation,
protected key, native service, Quickshell UI or Hospital database is
modified. Do not merge or activate without operator authorization.

**Production Hospital authorization remains HOLD.**
