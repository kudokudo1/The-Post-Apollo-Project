# Social Phone Bridge // Untrusted receive-intent boundary P1 v0

> **STATUS //** Isolated, offline parser for a **proposed** Phone Bridge host interface. NOT an authenticated host, SMS capability, grant service or production API.
>
> **PATIENT //** `kudokudo1/The-Post-Apollo-Project`
>
> **BASE //** `main` at `03b1ba929cec62e9914bc7e12899fa682c31fb5d` (PR #1044 verified merged 2026-11-02). Recheck current HEAD, ownership and tests before continuation.
>
> **CONNECTION //** OPEN AI // CHATGPT, external Hospital-compatible. No verified live Room, Session, Assignment, Staff Role or current Hospital checkpoint.
>
> **SCOPE //** New `services/phone/PhoneHostIntentBoundary.py`, `tests/phone/test_phone_host_intent_boundary.py`, targeted GitHub Actions, this contract, and one index entry. **No** changes to `services/identity/*`, `services/social/*`, `widgets/messanger/*`, existing Phone Bridge fixtures or Qt receiver, runtime, local machine or KDE Connect.

## 1 // Why this slice

[Identity Center ↔ Phone trusted-host integration handoff P1](./social-phone-identity-host-integration-handoff-p1-v0.md) describes a possible future privileged host that accepts a request from the existing Social PHONE surface.

The Social screen must only express a **selection**: which device, which line, which owner context and which operation the user is requesting. It must not choose the authenticated principal, assert membership, provide a bearer, claim SMS permissions or set `routeEligible`. A local organization created in Social USER // SETTINGS → ORGANIZATIONS is a display record, **not a verified legal tenant**. A portfolio or branch selection grants no phone authority.

The existing [Identity Center session host](../../services/identity/desktop_session_host_v0.py) and [private display IPC](../../services/identity/private_context_ipc_v0.py) are experimental. The display IPC cannot be reused as a writable permission/phone-content endpoint. No source file in those subsystems is modified here.

## 2 // Concrete behavior, intentionally non-authoritative

`parse_untrusted_receive_selection(request)` accepts a **single exact** dictionary:

```json
{
  "contract": "post-apollo.phone.host-intent.v0-proposal",
  "operation": "requestReceiveAccess",
  "deviceSelector": "fixtureDeviceA",
  "lineSelector": "fixtureLineA",
  "ownerKind": "PERSONAL",
  "organizationSelector": null,
  "requestedCapability": "messages.receive"
}
```

The only other accepted owner kind is `ORGANIZATION`, requiring a nonempty `organizationSelector`. The personal scope must use `null` for that field. Each device/line/org selector is a short ASCII opaque label starting with a letter, with alphanumeric/underscore/hyphen continuation. This filters obvious raw telephone numbers, paths, emails, logs and oversized values, **but it does not authenticate or make a selector trustworthy**. The full project may choose a different verified ID syntax only after Identity Center and Phone Bridge owner review.

A syntactically valid request returns an in-memory `UntrustedReceiveSelection` with only the four selectors. It is `frozen`, `slots`, and has no default `repr` with identifiers. That type represents **client intent**, never an authenticated principal, proven SIM, verified KDE device, consent receipt, bearer token or permission grant. It is not currently consumed by a real host or UI.

`sanitized_intent_status(request)` always reports:
- `execution: INTENT_VALIDATION_ONLY`.
- `status: AUTHORIZATION_REQUIRED` for syntactically valid intent, or `INVALID_REQUEST` otherwise.
- `routeEligible: false`, `contentAccessEnabled: false`, `platform: UNVERIFIED`, `transport: UNVERIFIED` in every result.
- `requestedCapability: messages.receive`, with a fixed proposed status schema.
- No raw device/line/org refs, session ID, tokens, phone numbers or SMS content.

Unexpected fields are rejected, including `principalId`, `identityId`, `accessToken`, `grantId`, `roles`, `authorized`, `canRead`, `phoneNumber`, `body`, `transport`, `bluetoothEnabled` and `routeEligible`. Requests for `messages.read`, `messages.send`, contact access and calls are out of scope and rejected. A requested `ORGANIZATION` is only an untrusted selector; even a known org ID is no proof of membership, line ownership or administrator consent.

**This is not a running IPC endpoint, not an authenticated verifier and not a grant.** It imports no Identity Center fixtures and reads no source of memberships. No network, session bus, disk, socket, phone or real data are touched.

## 3 // Production security requirements (still undecided)

The owner of a future authenticated host must:

1. Decide the actual privileged process and IPC trust boundary, including Linux same-UID D-Bus limitations. Existing Identity Center display socket is a **read-only display** service, not an authorization host.
2. Verify a signed/otherwise cryptographically validated session via a pinned IdP, trusted clock, audience/issuer, and revocation. Never accept caller-submitted principal or identity labels.
3. Resolve exact personal or organizational owner, fresh membership, explicit per-operation consent, bound phone/device/line identifiers, Android SMS permission and verified current network route. Local organization names and KDE plugin metadata cannot substitute for any of these.
4. Commit protected grant issuance/revocation and serialized content release under a reviewed transaction/IPC model, preserving the `grantGeneration` and `subscriptionEpoch` contract from the prior host handoff.
5. Bind receiver to an approved provider and sender. Only after all gates pass may a separately authorized *real* Qt receiver subscribe to KDE Connect, first with disposable test messages.
6. Document audit privacy, cancellation of buffered/visible content, and separate capabilities for history, send, contacts, notifications, phone calls and Bluetooth fallback.

The **Gate A host/security ownership and acceptance decision is still pending**. This change does not make it on behalf of the operator. The code must not be wired directly to KDE Connect or exposed as a public grant API just because the parser succeeds.

## 4 // Offline verification

On a disposable checkout, from repository root:

```bash
python3 -m py_compile services/phone/PhoneHostIntentBoundary.py tests/phone/test_phone_host_intent_boundary.py
python3 -m unittest discover -s tests/phone -p 'test_phone_host_intent_boundary.py' -v
python3 -m unittest discover -s tests/phone -p 'test_*.py' -q
```

Dedicated workflow: `.github/workflows/social-phone-host-intent-boundary.yml`.

The 27 synthetic negative tests cover exact personal/org selectors; unknown fields; forged principals/grants/tokens; incoming phone content; Bluetooth/transport overrides; wrong operation or capability; malformed schema; Unicode, path, email, numeric phone selectors; bounds; stable sanitized output and absence of authority methods. Passing tests prove only **input-shape validation and non-authoritative status**, not security or phone access.

## 5 // HOSPITAL HANDOFF

### IMPLEMENTATION
Pure untrusted request-intent parser and sanitized non-authoritative status for the proposed PHONE host interface, with offline tests and CI. New files only; shared Identity and Social sources untouched.

### HOW TO USE
Review the isolated PR and CI. No user-facing PHONE menu control or real identity/phone integration was activated.

### VERIFY
Check exact-head CI, branch file read-back and new test counts. All tests are synthetic; no hardware or live authentication assertions.

### WATCH OUT FOR
A valid syntactic request is easy to forge. It is **never** a grant. Do not reuse local Social organizations as authoritative tenant IDs. The future host owns all verification, audit and delivery decisions.

### CHECKLIST
- [x] Verified #1044 merged and current main; Syntagma/Identity/Phone boundaries inspected.
- [x] Created exact-schema non-authorizing receive-intent validator.
- [x] Added 27 adversarial offline tests, targeted CI and indexed contract.
- [ ] Exact-head CI and operator PR acceptance.
- [ ] Gate A Identity Center/security host owner acceptance.
- [ ] Trusted authenticated device/line/permission contract and real Android acceptance.

### NEXT
With the real host owner assigned, select the protected IPC/process boundary and authoritative grant implementation, then connect the validator as **input parsing only** before authenticated session verification. A future permitted Android test and Social integration-owner review are separate stages.

### DECISIONS
Network-first, Bluetooth per-capability opt-in fallback, separate iPhone/Android evidence, existing Social window and tenant isolation remain unchanged. No local file modifications, real phone access, PR merge, production activation or live Hospital registration performed.
