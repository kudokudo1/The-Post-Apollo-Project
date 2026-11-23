# 🏥💜 DOC 4 // C5-H9 original C3e kernel-origin + Hospital nonadmission

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5  
**STAFF ROLE:** DOC 4, external Hospital-compatible; no live registration  
**ASSIGNMENT:** Advance C5-H8's S0/R0/H0/C0 integration with actual merged
owner code, **without** authorizing native signing or PX commits  
**CHECKPOINT:** app main `ebd5e740f6042b366cb39487b453fe9deb6592ac`  
**OWNER INPUTS:** DOC 1 merged [#2361](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2361),
C5-H4/H6 merged, DOC 2 draft [#2360](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2360),
PX #130/#133 separate open drafts  
**PRODUCTION:** HOLD

## IMPLEMENTATION

A real Linux `SOCK_SEQPACKET` sender writes an original
`C3eLocalReadOnlyIpcProbe.frame_ci_only` request with
`op=CUSTODIAN_STATUS`. The original DOC 1
`C3eIdentityPacketOriginNonAdmissionCI.inspect_ci_only` executes
the **unchanged** kernel `SO_PEERPIDFD`/`SCM_CREDENTIALS` observer,
compares the packet's actual digest to the supplied expected bytes,
and routes through the original C3e `INDEPENDENT_CUSTODIAN_REQUIRED`
read-only boundary. The result remains `INDEPENDENT_CUSTODIAN_UNAVAILABLE_HOLD`.

Separately, original C5
`HospitalC5ExactConsentProbe.build_review` uses the **existing**
Hospital issuer core `validate_request` and `validate_prepared`
to construct a bounded exact TRASH or RESTORE review for a synthetic
protected PX response. Its `inspect_untrusted_claim` matches a
synthetic claimed native display/gesture and produces **only**
`MATCHING_CLAIM_UNTRUSTED_HOLD`, with all authority false.

The H9 cross-component test shadow does **not** pretend the C3e Identity
read-only report is Hospital source trust. It requires exact original
diagnostic shapes, refuses any positive security field or added grant,
and returns only a strict `C3E_PACKET_AND_HOSPITAL_CLAIM_NOT_NATIVE_CONSENT_HOLD`.
An actual call through **unchanged HospitalNativeIssuerService._native_step**
then replays the original H4 mocked preflight, Polkit and PX PREPARE
test harness. Despite the two superficially matching diagnostics,
`_require_independent_room_consent` rejects before
`load_installed_key`, `sign_px_grant` and PX COMMIT.

All new H9 code lives under `tests/connections/hospital_c5/`;
it is imported by **no** installed Hospital service. No new agent,
socket listener, Polkit action, storage adapter, root, key, Identity
gateway, renderer or signer is defined. DOC 1/C3e and DOC 2/C4b
owner sources are reused unchanged.

## HOW TO USE

Run the H9 pull request's isolated GitHub Actions workflow. The job
requires the original hosted Ubuntu Linux CI context and uses `sudo`
only to exercise DOC 1's existing root-guarded disposable C3e diagnostic
adapter with a genuine kernel packet. The sender and receiver are
temporary `socketpair` file descriptors; no host-path listener
or account credentials exist. C5 native credential/Polkit/PX replies
remain test callbacks, **not** an actual root service.

No workstation terminal or Quickshell action is required. This milestone
does not activate Hospital Room Trash/Restore, Sign-In or TimeW.

## VERIFY

Required source, integration and adversarial cases:
1. Genuine original C3e Linux sender observation is read-only protected
   HOLD; matching synthetic C5 review/claimed click still yields HOLD.
2. Both TRASH and RESTORE through original H4 real issuer entry function
   stop after protected PX PREPARE and mocked Polkit success; key and
   PX COMMIT are never invoked.
3. Added C3e current-history, sign-in, extra Hospital permission fields,
   local-only status or wrong operation cannot pass H9 shape guard.
4. Different actual sender payload cannot pass DOC 1's real kernel packet
   digest comparison; Identity `BEGIN_SIGNIN` is refused by its original
   read-only route.
5. Same Room with different C5 nonce, writerInstance, seat, action or
   claimed gesture fails untrusted claim match. A forged
   `agentReleaseDigest` may still match, but it never supplies trust.
6. Added/true C5 human-consent flags, safe actions, fake signed grant,
   contradictory claim status, stale or altered reference are refused
   or remain HOLD.
7. H9 `authorize_hospital_room()` always refuses, including caller
   fake root/custodian/consent. CI-only original C3e guard refuses outside
   the hosted root runner.
8. Static regression ensures the actual Hospital issuer imports neither
   H9 nor DOC 1's Identity test adapter; its hard stop still comes before
   the private signer and PX COMMIT.

Expected exact-head CI also reruns original DOC 1 22 source/kernel cases,
original Hospital H4 16 hard HOLD cases and H6 28 untrusted exact review
cases. These inherited test counts are expectations until raw CI confirms
them.

## WATCH OUT FOR

- A C3e **Identity-purpose** read-only packet cannot be reinterpreted as
  independently enrolled **Hospital-purpose** issuer or operator source.
  Exact kernel sender attribution proves neither host/release authorization
  nor what a human actually saw.
- Both the original C5-H6 review builder and the original H4 issuer
  `_native_step` are executed against disposable **synthetic PX/POLKIT
  sources**. These tests do not establish a running root PX writer.
- Even a matched test digest or claimed gesture is not independently
  protected SPENT. Neither the existing local C3e ledger nor a signed
  C4b UNAVAILABLE denial supplies current antirollback history.
- C5-H8 remains an RFC. DOC 1 / DOC 2, the trusted native display
  owner, and PX #130/#133 still must ACCEPT / REVISE / HOLD actual
  S0/H0/C0/W0/T0 source and custody responsibilities.
- A green test **does not** mean it is safe to remove C5-H4's hard stop.
  No full installed native host, SELinux/service/account/backup/legacy
  writer fencing, one-use custodian or operator acceptance is tested.

## CHECKLIST

- [x] Verify current merged DOC 1 #2361 and unmerged DOC 2 #2360
- [x] Reuse exact original DOC 1 kernel adapter and original C5 issuer,
      H4 refusal, H6 exact review reference
- [x] Add bounded purpose-separated negative integration shadow and tests
- [ ] GitHub exact-head CI and raw logs
- [ ] Nurse 2 independent source/CI review
- [ ] DOC 1/2, trusted display, PX owner C5-H8 decisions
- [ ] Operator native release and production acceptance

## NEXT

Submit the exact-head H9 CI and request Nurse 2 review, then track
actual owner responses on [C5 coordination issue #2052](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2052).
Do not replace DOC 1/2 source owners or PX writer code; only implement
further authorizing runtime semantics after accepted native trust,
H0/C0 custody and separate operator permission.

## DECISIONS

**NO PRODUCTION AUTHORITY.** No local machine change, native installation,
privileged runtime file modification, key, renderer, PX mutation, consent
root/enrollment, merge, or production activation as part of C5-H9.
Development remains local-first; future independently protected hardware
selection is separate and not an excuse to promote current local test state.

**HOSPITAL C5 PRODUCTION HOLD.**
