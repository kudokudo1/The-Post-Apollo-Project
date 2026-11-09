# 🏥 Identity Center signed native command client and receipt transport v0

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Sign-In native host integration, external Hospital-compatible, not live registered  
**ASSIGNMENT //** Implement real challenge-bound signed native receipts and strict out-of-QML client over existing BEGIN / STATUS / CANCEL / RECOVER gateway  
**STAFF ROLE //** External DOC-compatible developer; production and security sign-off remain independently owned  
**DOCTOR / PROVIDER //** ChatGPT / OpenAI  
**SOURCE BASE //** `6f8b870a2440d5df786aa86f81cd75f5904b4d0a`  
**PERMISSIONS //** GitHub-only bounded gateway extension, new standalone signed receipt codec/client, integration tests, scoped CI and recovery docs. No Fedora machine mutation, installed service, persistent key material, actual provider login, C3e/C4b/C5 source changes, PR merge or production activation.

## IMPLEMENTATION

Confirmed PR #1692 Fresh RECOVER merged, completing the four experimental host operations. Current main has a real local AF_UNIX gateway but **unsigned token-free receipts do not authenticate the native host to an external client**. Its existing `SO_PEERCRED` and admission callbacks remain test-injected and cannot establish signed installed host or genuine C5 consent. C4d's signed guest work separately examines a disposable Connections status service, **not this Identity Center gateway**.

This milestone implements a **real, opt-in cryptographically signed client/server path**:

1. **Signed host receipt codec** `services/identity/signed_command_receipt_v0.py`: Ed25519 signature over canonical bounded JSON with an explicit domain separator, a random host-instance identifier, monotonically increasing sequence, host-owned phase/request ID, the request action and original request ID, and a 256-bit client challenge. Input keys, names, sizes, Unicode, JSON duplicate keys, signature encoding, action-specific phases and request-ID consistency are strictly enforced. A client can verify with an **independently provisioned pinned public key**; the key is never fetched from the socket. A valid signature alone is **not a production authorization grant**.
2. **Existing native gateway** `services/identity/desktop_command_gateway_v0.py` gains optional `secure_receipt_issuer` constructed only from an externally supplied host Ed25519 signing-key object. When supplied, the gateway accepts **only** the signed request frame with a fresh challenge; the legacy three-field unauthenticated request cannot execute commands in that mode. The gateway performs its existing real host-side peer/seat/operator-intent checks, calls the actual BEGIN/STATUS/CANCEL/RECOVER lifecycle under the original lock, then signs the returned bounded receipt. Signing failure permanently closes admission and revokes any in-flight host login, rather than leaving an orphaned session.
3. **Native client outside QML** `services/identity/desktop_signed_command_client_v0.py`: real Linux Unix-socket client with independently pinned Ed25519 host public key and required **trusted_server_peer(kernel credentials)** plus **active_seat()** owner callbacks. It checks private directory/socket permissions and connected SO_PEERCRED before sending, and repeats owner-guard checks after verifying the signed response. Each command gets a fresh random challenge. It verifies action/old-ID/challenge/signature and rejects host-instance changes and non-increasing sequences. It stores just its current host-issued request ID and observation, never bearer tokens, passwords, issuer URLs, signatures for display, provider grants or an `authenticated:true` UI flag. It faults closed after missing/invalid receipts, bad host or seat and cannot recover itself by toggling a UI boolean.
4. **Regression tests** in `tests/identity/test_desktop_signed_command_client_v0.py` run a real signed Unix request against the **existing host and disposable fake IdP/PKCE callback**, covering BEGIN → STATUS → pending CANCEL → fresh RECOVER → callback → STATUS, strict invalid/unsigned frame rejection, wrong pinned key, client peer/seat denial, host-instance switch, replayed challenge, tampered signature/phase/ID, and signing failure host revocation.
5. A dedicated GitHub workflow installs an explicitly pinned cryptography dependency for **CI only** and runs the signed gateway tests alongside original legacy disposable gateway and CPU++ fixed-deny tests. No separate OAuth implementation or new QML button.

### Signed experimental protocol

Client request (example, actual nonce always random):
```json
{"schema":"post-apollo.identity.signed-command-request.experimental-v0","action":"STATUS","requestId":"HOST_MINTED_REQ_0001","clientNonce":"<fresh base64url 256-bit random challenge>"}
```

Response carries only a bounded `body` and a detached Ed25519 `signature`. The body includes exact `schema`, `hostInstance`, increasing `sequence`, `action`, `commandRequestId`, `clientNonce`, `state`, `requestId`. The signature covers *all* these fields with a domain separator. A local `AUTHENTICATED` status is a signed **observation** of the experimental callback state, not an attested identity grant or provider consent.

**No private signing key is generated or stored by production code.** CI creates ephemeral in-memory keys. The eventual independently installed host owner is responsible for a protected signer/key and approved trust-root provisioning and rotation; otherwise signed client activation must remain unavailable.

## HOW TO USE

**No new desktop action.** CPU++ → SETTINGS → CONNECTIONS remains the operator's current read-only status UI. Sign In/Cancel/Retry are still disabled.

For security review, the experimental native client is constructed only with an **owner-provided pinned public key**, a trusted kernel peer/process verifier and active desktop seat checker. The gateway is instantiated with a separately provisioned signing-key object plus the **existing mandatory** independently owned caller/seat/per-action intent gates. The client and gateway communicate through the existing command socket only when explicitly started by the trusted host. Do not install/activate or substitute dummy `lambda: True` gates on the operator's workstation.

## VERIFY

The tests use actual Linux AF_UNIX, existing host lifecycle/PKCE callback, real Ed25519 crypto and genuine signed byte frames; the IdP exchange, browser and operator/installed-host admissions are **disposable test fixtures**. Negative tests enforce exact command/receipt binding, no unsigned legacy fallback, key pin rejection, challenge/sequence anti-replay, forged fields and no secret disclosure.

CI separately reruns existing host/session/IPC, unsigned disposable legacy gateway and CPU++ default-deny contracts. Exact-head GitHub results must be checked and repaired before marking this milestone verified. This is **not** evidence of signing-key custody, production installed gateway or independently attested C5 human consent.

## WATCH OUT FOR

- A valid Ed25519 signature proves possession of the corresponding private key **only**. Unless an independently trusted signed-installed gateway identity supplies the key and attested signer binding, a hostile same-UID process could deploy its own key/service. The client requires an independent pinned key and trusted connected peer decision; the C3e/C4b actual installed gateway witness and C5 one-use per-action consent are still incomplete.
- The existing Identity Center read-only `SNAPSHOT` socket does not become a privileged command channel. No QML process imports this module or can change the `HostBoundary.offline()` flags.
- A client-rejected result after the real host has sent BEGIN might leave an in-flight host pending until the owner revokes it; native operator/service lifecycle must enforce expiration/cancellation and cleanup. Signing failure *inside* the gateway revokes immediately. Do not expose this protocol without supervised host lifecycle and expiration guards.
- No TLS transport, issuer selection or real account credentials are brought into QML. The native command client has no login authorization flag or provider connection rights.
- The legacy unsigned gateway remains available only in its pre-existing disposable mode when no signer is installed. In signed mode no unsigned client request is dispatched, and the signed client has **no fallback**.
- C4d evidence for the other Connections status service does not count as independent Identity Center gateway certification.

## CHECKLIST

- [x] Recover current main, merged #1692, current owner PRs and Syntagma/Hospital protocols
- [x] Implement real Ed25519 signed token-free receipts with challenge/old-request binding and replay checks
- [x] Add independent out-of-QML native client requiring pinned host key, peer and active seat
- [x] Wire opt-in real gateway signed response and disable legacy fallback when signer provided
- [x] Add disposable actual socket/client/callback test, adversarial forgery/host-replacement/unsigned tests and scoped CI
- [ ] Exact-head CI and correction
- [ ] Independent Identity Center/C3e/C4b/C5 review of actual installed host signer identity, process/seat and consent
- [ ] Operator PR merge/acceptance and native Fedora proof
- [ ] Approved protected client installation and CPU++ controls enabled by independent host capability receipt
- [ ] First real user login and provider-specific granted actions

## NEXT

**Independently attest and deploy the actual Identity Center gateway and signing key**, not the separate fake Connections status host. Owners must bind pinned signing public key to signed installed executable and actual running PID/start/seat/witness, establish protected signer lifecycle/key rotation and enforce genuine C5 one-shot operator intent per command. After that independent review, attach this non-QML client to an approved CPU++ command adapter and enable existing buttons only with current, verified host capabilities. Keep all QML credential gates false until acceptance.

## DECISIONS

Bounded GitHub implementation only, no live Hospital registration claim, no security-worker source edits, local machine writes, authentication-key storage, release, PR merge or production activation. Operator retains final approval. Recovery: this file, signed client PR, merged RECOVER #1692 and cross-Room issue #1662.
