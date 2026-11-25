# 🏥💜 DOC 4 // Hospital C5-H12 confirmed PX COMMIT / lost desktop receipt

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections / Hospital C5  
**STAFF ROLE //** DOC 4 external Hospital-compatible, live registration unverified  
**OWNER //** DOC 4 native issuer source, not Hospital UI or PX writer  
**STATUS //** Bounded source development only, draft PR, no installed service  
**BASE //** app main `83473371e9ee9f02de88db5a0a28982a686732a1`  
**PRODUCTION //** HOLD

## IMPLEMENTATION

There are **two independent terminal uncertainty points** in a future
protected Hospital Room operation:

1. The native issuer sends one original signed PX COMMIT. If PX has
   durably committed a Room mutation but its ACK is lost, the issuer
   cannot know whether PX committed. **Merged H11** conservatively returns
   `PX_COMMIT_OUTCOME_UNKNOWN_HOLD_NO_AUTO_RETRY`, without another COMMIT.
2. If the issuer **does receive and verify PX's exact COMMITTED receipt**,
   the protected Room operation is already committed, but the final
   issuer-to-desktop packet can still be lost or fail. Previously
   `main()` raised `PARTIAL_CLIENT_RECEIPT_REFUSED` for a short send
   or a generic `NATIVE_IO_UNAVAILABLE` for send exceptions. Neither
   distinguished a completed protected Room mutation from a client
   communication failure.

C5-H12 changes only the DOC4-owned native issuer:

- After unchanged `_native_step(client, policy)` returns the original
  exact validated `COMMITTED` response, one
  `_send_committed_client_receipt_or_unknown` call serializes and sends
  exactly one canonical minimal client packet.
- A short send, disconnect, timeout, serialization error, or failure
  after validated PX COMMIT produces only
  `HOSPITAL_NATIVE_HOLD //
  PX_COMMITTED_CLIENT_RECEIPT_UNKNOWN_HOLD_NO_AUTO_RETRY` in the issuer
  error path. It does not claim PX failed, rolled back or was repeated.
- Even a successful kernel `send()` is **NOT** an application-level ACK,
  UI visibility proof or authorization to release a retry fence. The
  protected Room is already committed in this branch. This is **logging
  and failure-classification hardening**, not terminal recovery.
- Neither the desktop UI nor PX owner source, native protocol schema,
  signing key path, native consent H4 hard stop, or H11 one-shot PX COMMIT
  is changed.

No live operation can reach this response path today because the
independent exact-Room human-consent check unconditionally refuses
before private signing-key load.

## HOW TO USE

Inspect the draft PR's source/tests/CI and run the H12 GitHub workflow.
It creates disposable `AF_UNIX SOCK_SEQPACKET` socketpairs and mocked
client sends, **without running the actual issuer as a signer**, loading
an installed key, connecting to PX or mutating any real Hospital record.

The operator has no new usable Hospital Trash or Restore feature.
Current UI remains **HOSPITAL BACKEND NOT READY**, and failure of a
client reply cannot be interpreted as an instruction to click again.

## VERIFY

Planned exact-head CI (must be read before claims of PASS):
- **16 new tests** for one correct minimal COMMITTED delivery; actual
  Linux AF_UNIX SOCK_SEQPACKET receipt; actual disconnected recipient;
  zero, partial, negative, broken-pipe, reset, timeout and refusal
  outcomes; source canonicalization failure; no PX retry and no client
  ACK assumption; H4 and H11 static source continuity.
- **20 H11 tests** covering original PX COMMIT UNKNOWN/no retry and
  strict terminal PX receipt validation.
- **16 H4 tests** ensuring native human-consent denial before signer.
- **20 H10 real Linux descriptor cleanup tests**.
- **8 H6 Polkit/review-context tests**.
- Expected **80 targeted test cases** if every test succeeds. Workflow
  and test numbers are provisional until raw exact-head run completes.
- Additional native issuer/Connections source/grammar jobs may trigger
  on the change.

## WATCH OUT FOR

**H12 does not solve the actual retry hazard.** The current Hospital
Room UI `services/hospital/HospitalRoomLifecycleService.qml` clears
pending Room/action after an unknown native result, and can request
a new operation after the process exits. After protected signing is
eventually enabled, this would require a **Hospital UI owner** sticky
unresolved-original-operation fence, **PX owner** independently
authenticated exact original T0 RECOVER and durable current history,
and trusted source-level policy.

The PX #130/#133 branches are open draft/unmerged; their Room
`ConsentCoordinator` implements PREPARE/COMMIT but not an approved,
read-only, independently current original Room RECOVER. H12 only
classifies the second reply loss *after* an exact PX COMMITTED receipt.
It cannot recover the missing first ACK, infer original history from a
current Room snapshot, block a UI manual retry, or create a new grant.

**The exact signing refusal stays mandatory.** H0 real visible human
gesture, independent C0 one-use SPENT, S0 installed trusted enrollment,
PX W0/T0 original-source custody, client/window ownership and actual
native acceptance are still unestablished. Generic Polkit or a disposable
test receipt does not satisfy these gates.

## CHECKLIST

- [x] Recheck C5-H4/H10/H11 main, PX #130/#133, Hospital UI owner source
- [x] Identify second post-COMMIT terminal uncertainty in DOC4 native main
- [x] Implement scoped one-attempt desktop receipt failure classification
- [x] Add disposable real-Linux socket tests and inherited safety CI
- [ ] Verify exact PR head, raw native test results and full PR checks
- [ ] Request independent Nurse 2 security review of exact head
- [ ] Separate operator decision before any merge
- [ ] PX/W0/T0 owner recovery interface accepted
- [ ] Hospital UI original-UNKNOWN manual-retry fence accepted
- [ ] S0/H0/C0 native independent operator-consent trust accepted
- [ ] Real installed native end-to-end and operator production acceptance

## NEXT

Have Nurse 2 inspect the actual issuer `main()` sequencing and
exception boundary: response source proven COMMITTED, one send, never
new PX COMMIT and unchanged pre-key denial. If scoped PASS, ask the
operator to decide the source merge. Coordinate separate PX/UI owner
original-operation retry fences rather than making desktop QML or a
local marker a substitute for protected custody.

## DECISIONS

C5-H12 is a bounded **DOC4-owned security error-classification
increment**. It does not change the native wire, user-facing controls,
PX writer, root policy, enrollment, consent, signing grant, durable
history, installed service or original operation. Source tests are not
native installation and do not authorize COMMITTED actions.

**HOSPITAL C5 / SIGN-IN PRODUCTION HOLD.**
