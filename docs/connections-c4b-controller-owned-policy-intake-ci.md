# 🏥💜 C4b Identity // Controller-Owned Read-Only Enrollment Policy Intake (CI Only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections · C4b actual signed Identity Silverblue guest / controller enrollment boundary  
**STAFF ROLE:** External Hospital-compatible DOC successor; authorized to continue C4b development, live Hospital registration unverified  
**ASSIGNMENT:** Bridge the existing C4b controller-enrollment verifier from arbitrary in-memory test arguments to a strict, read-only, caller-selected **controller-side fixture policy bundle**  
**OWNER:** C4b-only `tests/connections/identity_silverblue` and dedicated CI/docs  
**STATE:** Draft / review pending / production HOLD

## IMPLEMENTATION

Merged [#2038](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2038) repaired the real Silverblue signed proof UART framing. Its [exact-head KVM run](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/44252884317) **SUCCEEDED 5/5** and the raw job log contains both `C4B_ID_PASS // HOST_CONTROLLER_FRESH_CHALLENGE_SIGNED_DENIAL_VERIFIED` and `C4B_ID_PASS // REAL_OFFICIAL_SILVERBLUE_SIGNED_IDENTITY_RPM_TWO_REBOOTS_AND_ROLLBACK`. NRS-2 source re-review and final operator acceptance are separate.

[C4b #2033](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2033) introduced an Ed25519 controller-signed host-ID/receipt signer enrollment contract but accepts a **caller-supplied** expected controller root, host, release, epoch/sequence floor and revocation tuple. C4b's actual KVM guest does not prove those sources are independently controlled.

This next scoped component, `controller_owned_policy_intake_ci.py`, adds a read-only admission interface for a **pre-existing bundle outside the guest**. The CI caller explicitly selects the bundle directory. It must be absolute, owner-only mode 0700, and not a symlink. Each allowlisted file is opened with `O_NOFOLLOW` relative to one pinned directory descriptor, must be a regular owner-only 0600 **single-link** file and is bounded by exact size. Reading validates stable inode/mtime/ctime/size/mode before and after:

| File | Data supplied by controller fixture |
|---|---|
| `controller-root-public.ed25519` | Exactly 32 raw public-key bytes, no private key |
| `controller-policy.json` | Canonical exact-schema role/audience, host ID, signed release SHA-256, root hash, floor and revocation list |
| `gateway-enrollment.json` | Canonical role-scoped signed gateway key enrollment from C4b #2033 |
| `gateway-enrollment.ed25519` | Exactly 64 bytes of the independent enrollment signature |

The policy is strict JSON with no duplicate, unknown or noncanonical fields, no invalid host ID, no non-positive/boolean release floor, no malformed/unsorted/duplicate revocation entries. Controller public key SHA-256 must match the policy pin. It then invokes the existing C4b `inspect_enrolled_controller_challenge_ci_only` which verifies enrollment signature, exact role/host/release/key and revocation, before accepting an actual guest signed `BEGIN / UNAVAILABLE` receipt over the fresh controller nonce. An impostor guest with a different self-signed key is refused.

The resulting data can prove only **local test consistency**. No method in this code provisions keys, persists a ledger, invokes systemd or sign-in, or writes outside disposable CI. All host authentication, C5 consent, production permissions and root custody indicators remain FALSE.

## HOW TO USE

Dedicated CI: `.github/workflows/connections-identity-silverblue-controller-policy-intake.yml`. It uses disposable test keys and a private temporary directory owned by its CI test process. The tool is a Python **library**, not a production CLI, and performs no writes. Its input directory must be provided by an external trusted caller, not by a QEMU guest or returned UART evidence.

No user workstation action or Quickshell restart is required.

## VERIFY

- [ ] 28 new adversarial controller file ingress, source, revocation, guest substitution and no-grant cases pass
- [ ] 35 signed enrollment, 28 UART challenge, 25 signer binding, 31 RPM contract and 7 Identity release regression tests pass at exact head
- [ ] Existing real official Silverblue workflow stays green at exact PR commit, with the #2038 framing repair
- [ ] Independent NRS-2 security review and operator-controlled merge

## WATCH OUT FOR

**Unix file ownership, read-only access and a cryptographic signature do NOT establish independently authorized trust.** All four files may still be manufactured by one disposable CI process. In a production system, approved root custody, secure operator key enrollment, protected revocation / version floor, revocable authority and independent process/seat attestations remain mandatory. This contract intentionally does not decide who may populate a bundle.

Permission and directory metadata can also be replaced by a sufficiently privileged local administrator; the before/after check does not make the read atomic against an adversarial administrator. It fails closed for common symlink and file-swap cases but is **not a secure production trust store**.

The real Silverblue guest currently supplies its own public receipt key. C4b #2033 protects the *synthetic enrollment interface*, not the live KVM key's root custody. No automatic promotion from CI indicator to `hostAuthenticated` or `credentialActionsEnabled` is permitted.

## CHECKLIST

- [x] Reconcile #2038 merge, 5/5 passing exact-head real VM, original NRS-2 failure and canonical Hospital protocols
- [x] Keep new code in C4b-owned test harness and avoid C3e/Identity/C5 modifications
- [x] Implement read-only pinned source bundle and preserve all explicit hard-false authorization fields
- [x] Add 28 malicious policy, path, revocation, host and signed receipt tests
- [ ] Verify exact head fast/real CI and Nurse 2 audit
- [ ] Later root custody/rotation/revocation and external host attestation; operator approval required

## NEXT

Finish CI, fix any demonstrated failures and request independent review. The next separate **operator-approved** milestone is to choose who holds the real enrollment signing root, how root rotation and revocation are authorized, and how C3e receives an independently authenticated installed-host/process/seat witness. Do not auto-create a production key or accept guest-owned pins as independent controller authority.

## DECISIONS

No local machine changes, production service/sign-in activation, real root keys, C3e/Identity/C5 source mutation, automatic merge, credential actions or claim of live Hospital registration.
