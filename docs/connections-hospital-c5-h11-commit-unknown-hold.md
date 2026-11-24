# 🏥💜 DOC 4 // C5-H11 original PX COMMIT terminal uncertainty

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Hospital C5 native issuer  
**STAFF ROLE //** DOC 4, external Hospital-compatible; no verified live Hospital registration  
**ASSIGNMENT //** Make the original PX COMMIT failure state unambiguously
UNKNOWN/HOLD, without granting consent or revising the PX writer's wire format  
**SOURCE CHECKPOINT //** The-Post-Apollo-Project `main` at
`ba92482ba267a9e34fd91e76b03a65332101fad3`  
**PRODUCTION //** HOLD

## IMPLEMENTATION

The original C5 issuer obtains protected PX PREPARE, verifies seat,
peer and interactive Polkit, then currently **must** refuse exact-Room
human consent before loading its installed private key. When native H0/C0
integration is approved later, the issuer will send precisely one signed
PX COMMIT request to the protected writer. After the packet is sent, the
writer can durably mutate the original Room and lose its response before
the issuer reads it. Even a mismatched or missing terminal receipt cannot
prove whether the original mutation happened.

Previously the runtime called `_writer_exchange` and
`C.validate_commit_receipt` directly. If transport or terminal
validation failed, their generic `C.Refused` code could be interpreted
as a definitive refusal even when a PX COMMIT may have occurred.

This patch changes **only DOC4-owned**
`services/connections/hospital/HospitalNativeIssuerService.py`:

1. After unchanged H4 human-consent hard denial, key loading and signing,
   the native path delegates the **single original** signed grant/COMMIT
   to `_commit_with_terminal_receipt_or_unknown`.
2. A complete correct receipt is still checked by unchanged
   `C.validate_commit_receipt`. It returns the same minimal COMMITTED
   response, never the raw signed grant.
3. **Every** writer-exchange or receipt-validation refusal / IO
   exception at this point is conservatively surfaced as
   `HOSPITAL_NATIVE_HOLD // PX_COMMIT_OUTCOME_UNKNOWN_HOLD_NO_AUTO_RETRY`.
   Even an error before send is classified UNKNOWN because that is safe
   and does not invent proof that PX committed or refused.
4. The helper contains precisely **one** `_writer_exchange` invocation:
   no retransmission, locally writable fallback, signed-grant print,
   secondary COMMIT or automatic restoration. A future original-command
   RECOVER must use **PX-owned authenticated history and independently
   accepted T0**, not an assumed terminal ACK.

No C3e/C4b/PX owner code, QML UI, Polkit actions, keys, current
human-consent denial, installed socket, release policy or persisted
Hospital database was changed.

## HOW TO USE

Run the H11 GitHub Actions workflow on this draft PR. It composes an
**ephemeral in-memory Ed25519 fixture signed through the original
issuer core**, then directly exercises this post-admission helper with
a fake PX exchange. It never mocks the production H4 human-consent gate
to produce a live grant: direct native `_require_independent_room_consent`
still rejects, and the rest of the production issuer is not invoked to
sign in the absence of genuine approval.

No workstation or Hospital UI action is required. Do not invoke
`_commit_with_terminal_receipt_or_unknown` as a CLI or authorization
endpoint; it is a private source-only helper.

## VERIFY

Targeted tests (required, not claimed until raw CI):
- Correct TRASH and RESTORE exact receipts still validate and return
  original `COMMITTED` schema/Room/action, no burn, one PX COMMIT.
- Socket timeout, lost terminal ACK, reset, untrusted writer change,
  absence of PX path, malformed/empty/duplicated receipt,
  wrong graph receipt digest, room, request nonce, action, revision,
  preservation flag, or burn flag all return **UNKNOWN/HOLD**.
- No success or safe-to-retry claim may be generated from a mismatched
  receipt, even with a valid local test Ed25519 signature.
- No second COMMIT invocation occurs on any failure.
- H4 direct issuer hard denial remains before loading the key,
  signing or invoking this COMMIT helper.
- Inherited H4 16, H10 20, and H6 Polkit-detail 8 cases remain PASS,
  plus exact-head native issuer/Connections/Grammar workflows.

## WATCH OUT FOR

The protected PX writer itself, its one-use nonce custody, legal hold,
atomically fenced original Room revision, authenticated terminal history,
safe old-writer shutdown and purpose-specific H0 display/C0 SPENT are
still **not installed or accepted**. PX #130/#133 remain independently
owned drafts. H11 does not establish durable RECOVER. Classifying an
outcome UNKNOWN protects against falsely definitive failure, but does
not let the operator repeat that command safely.

The original Hospital UI currently reports `REFUSED / UNKNOWN // REFRESH
ROOM` for failed native requests and can clear pending intent. A
refresh is **not** equivalent to authenticated original-command
settlement. Any later UI reattempt controls belong to the Hospital
source owner and require separate reviewer/operator acceptance. No QML
or native client change is authorized by this milestone.

An exact-head CI pass is a source test result, **not** permission to
remove C5-H4's unconditional signing refusal or activate a root socket.

## CHECKLIST

- [x] Reconcile C5 H10 scoped PASS, DOC1/2 and PX owner boundaries
- [x] Identify ambiguous PX COMMIT ACK semantics in current native issuer
- [x] Add one-shot native COMMIT result classification without expanding authority
- [x] Add tests with original signed PX grant/receipt core and hostile terminal ACKs
- [ ] GitHub exact-head CI and inherited regressions
- [ ] Independent Nurse 2 pre-merge security review
- [ ] Separate operator merge disposition
- [ ] H8 S0/R0/H0/C0/W0/T0 owner ACCEPT / REVISE / HOLD decisions
- [ ] Production native installation and final operator acceptance

## NEXT

After CI review, the PX owner must define the source-authoritative
original-request read-only RECOVER path, its typed terminal states and
independently current historical membership proof. C5 can then integrate
that **accepted** read API without replaying the original COMMIT, and
only once H0/C0 protected human consent and S0 enrolled host trust exist.

## DECISIONS

This milestone is **source-level failure-classification hardening** for
DOC4's existing issuer, not a new consent interface, PX writer,
terminal receipt producer, UI permission or service. No local workstation
change, root key, production sign-in, native Room mutation, merge or
service activation is authorized.

**HOSPITAL C5 / SIGN-IN PRODUCTION HOLD.**
