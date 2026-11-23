# 🏥💜 DOC 4 // Hospital C5-H8 independent native consent admission contract

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Hospital C5 native operator consent  
**STAFF ROLE //** DOC 4 · external Hospital-compatible, no verified live registration  
**ASSIGNMENT //** Coordinate the precise source, display, custody and PX boundaries before lifting C5-H4's runtime denial  
**CHECKPOINT //** Application `main` at `7a8c820416977653b045a1fa0a7265905ecb1315`; Nurse 2 retrospectively reviewed merged H5/H7 and pre-merge reviewed merged H6  
**DEPENDENCIES //** DOC 1 (C3e identity/current independent history), DOC 2 (installed host/release), trusted native display/seat owner, PX #130/#133 protected writer  
**PHASE //** PROPOSAL / OWNER RESPONSES REQUESTED  
**PRODUCTION //** HOLD

## IMPLEMENTATION // What the actual bytes and processes must do

The Quickshell Hospital widget passes only a Room/action request to the
fixed native client. The root-owned C5 issuer authenticates the caller's
Linux process and active local logind seat, generates a fresh 32-byte
`requestNonce`, and sends a PREPARE to PX. PX returns the exact current
Room/Patient/repository/graph/revision/legal-hold/retention decision plus
its own `writerInstance`, `policyGeneration` and deadline. The issuer
checks the reply and may call Polkit, but **its current
`_require_independent_room_consent()` must always refuse before private
key load**. That is the present safe behavior, not an integration defect
to bypass.

H3/H6's canonical exact-review reference and H7's real kernel packet
origin test are **non-authorizing diagnostics**. A canonical hash says
what bytes matched. Linux SCM_CREDENTIALS says who sent a packet.
Neither proves the actual operator saw those bytes, used the intended
input path, or authorized a one-use mutation.

This document proposes **one jointly auditable integration contract**
for a later trusted producer. It defines the evidence that must exist
without selecting or implementing a native agent, cryptographic wire
format, root key, custodian, systemd unit, approval gesture or actual
database writer.

### Evidence chain that must not be collapsed

| Link | Future protected source | Required fact | Currently established? |
| --- | --- | --- | --- |
| S0 · Installed source | DOC 1 / DOC 2 independently enrolled native release and host verifier | Actual running issuer, request client and producer release/process/policy/seat, enrollment chain, current revocation and authorized purpose | **NO**. Per-process kernel checks and release diagnostics do not prove independent enrollment |
| R0 · Exact Room source | PX owner read-only protected PREPARE authenticated to issuer | Current original Room/action/Patient/repository, revision, graph digest, issuer nonce, PX writer instance, retention/legal hold, policy generations and deadline | **SOURCE CONTRACT ONLY**. PX #130/#133 remain draft/uninstalled |
| H0 · Human-visible exact action | Separately enrolled trusted native display and input producer | Exactly the canonical R0 operation is visibly presented in the operator's currently active unlocked local seat, followed by an explicit gesture for that operation; renderer release, display/session identity and input event are bound to a fresh challenge | **NO**. Polkit detail, QML clicks, screenshots and H7 candidate claims are insufficient |
| C0 · Independent consent custody | Authorized independently current one-use C5 custodian | Current enrollment/revocation and exact purpose-bound H0 evidence; durably, atomically spend the **original** consent/challenge once before signing, prevent reuse after restart/rollback; return a protected committed SPENT fence | **NO**. Local test ledgers and same-rollback-domain files cannot qualify |
| W0 · Protected original write | PX protected native writer | Check currently valid R0 + C0 source admission and exact signed root-issued grant inside source transaction; consume one grant and original nonce, preserve original Room/history; all legacy SQLite writers fenced | **NO**. Owner draft source has not been installed/accepted |
| T0 · Terminal result | PX writer + independently protected outcome history | Authoritatively bind original operation/nonce/Room/writer instance to exactly one terminal COMMITTED/REFUSED result or UNKNOWN/HOLD; durable historical membership survives any local DB rollback | **NO**. Test-only receipts/SQLite rollback do not supply independent terminal trust |

C0 one-use SPENT and PX original-request reservation are related but
distinct. **Both** need an unambiguous relationship to the exact original
challenge and source transaction; one cannot be inferred from the other.

### Proposed ordered transaction

1. **Preflight:** Independently read current S0 trust/revocation and
   active local seat/host. A local fixture, self-selected producer key,
   cached guest diagnostic or absent trusted service yields HOLD.
2. **Read source:** C5 issuer mints a fresh nonce and obtains R0 from
   the authenticated protected PX PREPARE. Retain the exact canonical
   review bytes and digest. Distinguish PX `writerInstance` from issuer
   nonce and separate PX vs issuer policy generations.
3. **Show:** Give an enrolled display producer only the exact bounded
   review and a separately issued short-lived purpose-specific
   challenge. Producer must prove current surface/input/seat provenance
   and **the actual rendered review and deliberate operator action**.
   A generic Polkit success does not satisfy H0.
4. **Recheck:** Re-evaluate active seat/session/lock, installed release,
   current revocation, source writer/Room graph/policy/expiry and
   challenge lifetime. Any drift/cancel/focus ambiguity denies; do not
   reuse the displayed permission for a changed Room.
5. **SPEND BEFORE SIDE EFFECT:** Independent C0 authority atomically
   records the exact original challenge as irreversibly SPENT and
   returns the authenticated commitment under its current trust head.
   If the SPENT ACK is lost, **UNKNOWN/HOLD**, not free-to-retry.
6. **Grant / source transaction:** Only after complete S0/R0/H0/C0
   verification may a future separately reviewed issuer implementation
   consider loading its key. PX independently verifies W0 admission,
   one-use original request and grant under one source transaction.
   No client, QML or producer receives the signing key or raw grant.
7. **Terminal / recovery:** Reconcile T0 using a fresh authorized
   read-only RECOVER query and independently trusted historical
   membership/current head. An old signed PENDING packet is not a
   COMMITTED or REFUSED decision. No automatic COMMIT replay.

**Important:** This sequence is a proposed ordering, **not** an
approved implementation. In particular, it does not define what a
future C0 service stores, what cryptographic signatures are accepted,
or how a compositor proves actual visibility. Owners must resolve
those before writing an authorizing code path.

### Exact-review fields that an eventual H0/C0 binding must cover

The evidence must purpose-bind at least:
`HOSPITAL_ROOM_TRASH` vs `HOSPITAL_ROOM_RESTORE`;
Room/Patient/repository; expected source revision and graph digest;
issuer-generated requestNonce; PX-provided writerInstance and PX
policyGeneration; root-issuer policy generation and authorized host;
operator UID and active logind seat/session identity; retention/legal
hold and `originalPreserved=true`, `burnAllowed=false`; short
issued/displayed/approved/expiry times; approved producer release,
display/input provenance and current trust/revocation generation;
separate challenge ID and independently current one-use custodian
SPENT identity. Any missing, renamed or contradictory field is HOLD.

H6's CI-only v2 review hash is a **starting comparison reference**
and should not be promoted directly into a production packet or
signature domain. The future schema and key purposes require an
explicit joint owner revision.

## HOW TO USE // Owner responses, not workstation commands

**DOC 4 / Hospital consent:** ACCEPT, REVISE or HOLD the source-to-show,
show-to-SPENT, SPENT-to-grant admission ordering. Identify the exact
function where a trusted future witness could be checked and retain
the H4 unconditional refusal until independently reviewed code and
installed trust exist.

**DOC 1 / DOC 2:** ACCEPT, REVISE or HOLD the independent installed
native producer/issuer enrollment and fresh current authority,
release/purpose separation, revocation, cross-host/seat drift and
approved custodian trust mechanism. Do not reuse Identity, TimeW or
C4b test signer roots as Hospital consent authority.

**Trusted display owner:** ACCEPT, REVISE or HOLD the ability to
produce actual rendered bytes, active unlocked seat and deliberate
input evidence. State which existing OS-managed native agent and/or
compositor hook can prove it. A generic authenticated process PID or
`pkcheck` status is not proof of visible per-operation confirmation.

**PX owner (#130/#133):** ACCEPT, REVISE or HOLD protected original
request/W0/T0 ownership: root-controlled writer and DB/WAL custody,
one-use reservation, new grant/reused original refusal, state/graph
revalidation inside SQLite transaction, independent terminal receipt,
old-writer cutover, backup/restore and UNKNOWN outcome.

**Operator:** The accepted development strategy is ordinary local data
and tests now, separately protected hardware/NAS-connected custody
when infrastructure is ready. This **does not** select a real C0
custodian, trusted producer, enrollment root or production release.
Do not require the operator to repeat the local-first strategy decision;
request only concrete unresolved native trust/release choices after
owners provide credible alternatives.

Each answer belongs in the appropriate owning issue/PR and should be
cross-linked to the canonical C5-H2 handoff issue #2052, not silently
treated as accepted from a source merge.

## VERIFY // Required native acceptance, not CI substitutes

| Adversarial event | Required outcome |
| --- | --- |
| Valid Polkit return, but no actually displayed exact review | HOLD before private-key load |
| Claimed visible/confirmed fields with matching H7 kernel packet origin only | HOLD before SPENT/signing |
| Renderer enrolled for another purpose/host/release, or revoked after review | HOLD; never adopt a caller-provided key/root |
| Lock/focus/seat change, display obscured, producer restarted or active session changed | HOLD; no reuse of previous H0 |
| PX writerInstance, graph/revision, retention, policy or source expires between display and spend | HOLD and invalidate original display |
| Two concurrent C5 requests for same original nonce, one with changed grant | At most one durable original admission; no second mutation |
| C0 SPENT commits then ACK is lost before signing | UNKNOWN/HOLD; never re-spend or automatically retry |
| Source COMMIT succeeds, then PX terminal ACK is lost | UNKNOWN/HOLD and read-only authenticated reconciliation |
| Local Hospital or consent SQLite restored to prior backup | Previously spent original request remains fenced independently |
| C0/PX custodian partition, split history or stale signed head | HOLD/UNKNOWN; never local fallback |
| Old desktop PX or already-running writer attempts direct SQLite writes after cutover | Denied by installed ownership/process fence, independently verified |
| Burn, cross-purpose TimeW/Sign-In grant, changed Patient/Room or copied review | Denied without grant or mutation |
| Native host exact end-to-end Trash → HOSP Bin → Restore | Authorized operator observes one confirmed action per transaction, source/history preserved; requires separate acceptance |

GitHub source-only tests may check packet formatting, nonce binding,
process credentials and negative behavior, but cannot certify H0/C0,
installed PX writer isolation or full recovery. Native-host and human
acceptance evidence must be obtained after explicit operator approval.

## WATCH OUT FOR // Non-negotiable security HOLD

- The H4 `_require_independent_room_consent()` hard stop is **not a TODO
  that may be replaced by a boolean, QML callback or fixture signer**.
- C5-H7 `SO_PEERCRED`/`SCM_CREDENTIALS` only validates Linux packet
  origin. It does not prove what was rendered or clicked.
- PX #130/#133 are independently owned unmerged sources. This RFC
  neither installs their protected SQLite writer nor fences legacy
  desktop processes.
- A normal local test ledger can preserve work now. It must never
  be promoted to independent antirollback authority or backfilled
  as a valid historical consent grant after future hardware enrollment.
- A signed ACK with a stale head or an unsigned local absence
  claim cannot authorize the next original request or a retry.
- Neither this RFC nor a successful CI/manual dry-run grants
  production Sign-In, Hospital Trash/Restore or Burn.

## CHECKLIST // C5 assignment and evidence

- [x] C5-H5 exact source-entrypoint audit independently scoped reviewed
- [x] C5-H6 exact protected review fields independently scoped reviewed
- [x] C5-H7 real Linux origin probe independently retrospectively reviewed
- [x] Unconditional native issuer H4 signing refusal still present on main
- [x] One proposed cross-owner S0/R0/H0/C0/W0/T0 contract captured
- [ ] DOC 1 / DOC 2 enrolled native trust and independent custody response
- [ ] Trusted display/source owner native actual visibility/gesture response
- [ ] PX owner exact original one-use writer/terminal/old-process fence response
- [ ] Operator accepts future key/custodian/renderer architecture and host release
- [ ] Native end-to-end positive/negative acceptance and independent Nurse 2 review

## NEXT // The first real unblock

Collect explicit **ACCEPT / REVISE / HOLD** on source/enrollment,
display/gesture, current independent one-use SPENT and protected
PX original-request terminal admission. Once recorded, DOC 4 may
propose the smallest new authorizing implementation **for an approved
real producer**, not for a test-only positive claim.

## DECISIONS

**RFC ONLY.** No new signing code, native host, socket, agent, policy,
root key, schema activation, credential grant, storage selection,
database migration, PX branch modification, local workstation write,
live Hospital registration, PR merge or production activation is
authorized or performed by this document.

**Hospital C5 production remains HOLD.**
