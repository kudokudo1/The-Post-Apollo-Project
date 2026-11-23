# 🏥💜 DOC 6 // Identity Center V5 protected native admission handoff

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections / Identity Center and Sign-In V5 (external Hospital-compatible, no verified live Room registration)  
**STAFF ROLE //** DOC 6, Identity-owned native command client / protected Sign-In integration  
**BASE //** `6c0edc9bcd7df1b6c2f4fd13bad8caca6a53bdda`  
**TYPE //** Cross-owner contract / negative acceptance map, not an adopted security protocol  
**PRODUCTION //** HOLD; no authorized native command bridge or account login

## IMPLEMENTATION // Already present, do not rebuild

- Existing `desktop_command_gateway_v0.py` supports host-owned BEGIN, STATUS, CANCEL and fresh-request RECOVER. It uses peer, seat and intent callback contracts but supplies no real protected C5 authorization implementation.
- Existing `signed_command_receipt_v0.py` uses independently pinned Ed25519 command receipts bound to action, old request ID, fresh client nonce, host instance and monotonic sequence. Correct signature alone is not installed-host provenance.
- Existing `desktop_signed_command_client_v0.py` has total monotonic deadline protection, including after receipt verification and final host/seat check (DOC 6 #2193 and #2203 merged). On uncertain transport failure it faults; a client exception does **not** prove a dispatched BEGIN had no effects.
- `installed_command_adapter_v1.py` combines `SignedGatewayOriginProbe` and `InstalledGatewayWitness` with independent connected-peer/seat checks. The installed witness is **dpkg/Ubuntu disposable CI**, not an approved Silverblue/production identity issuer.
- `ConnectionsSignInHostBoundary.offline()` still provides no action capability. CPU++ QML must not import Python command clients, raw OAuth tokens or actual command sockets.

## Required independently owned inputs before a real native adapter

| Owner | Required supplied evidence | Not acceptable as replacement |
| --- | --- | --- |
| DOC 1 / protected C3e | Independently controlled enrolled release/receipt root identity; durable challenge/revocation/history custody; authenticated fresh process/seat witness and antirollback decision | Local SQLite test key, caller-selected pin, same-process signature, copied CI log, or self-reported witness |
| DOC 2 / C4b | Actual Identity-specific installed signed Silverblue gateway release; same live process PID/start/UID/GID, unit, SELinux/cgroup and executable/module origin; signer/receipt-key continuity; official reboot and rollback/absence evidence | C4d Connections status-host observation, synthetic RPM signature, Ubuntu dpkg fixture, guest UART assertion |
| C5 consent owner, independently assigned | Fresh human-origin command intent, exact active unlocked seat and peer, one-use per-command consume/revocation semantics; distinct BEGIN/CANCEL/RECOVER requirements and idempotency/unknown-outcome policy | Positive `approved_intent` test callback, button click boolean, same-UID socket, or previous account session |
| DOC 6 / Identity | Versioned native command/status contract wired **outside QML** through approved composite installed evidence, pinned receipt key, fresh nonce and request IDs, bounded deadline, host-loss refusal and a token-free UI projection | Direct QML call to `DesktopSessionHost.start_login()`, raw unsigned `UNAVAILABLE`, connected read-only SNAPSHOT socket, or `AUTHENTICATED` flag from display data |
| CPU++ UI owner | Explicit operator-visible BEGIN/CANCEL/RECOVER controls activated only after independent host+seat+consent admission is accepted; no credentials in QML | Treating signed status or account overview as authorization |

These inputs require owner-supplied source interfaces and security review. DOC 6 will not invent a positive C3e/C4b/C5 provider or change their files to make an offline flag true.

## Proposed V5 exchange and refusal semantics

1. **PREPARE** (native privileged side): verify independently enrolled host release and actual installed running process, current seat, command sender and approved C5 one-shot intent. Keep raw credentials and signer keys outside QML. If any are missing: deny; do not fall back to disposable Ubuntu witness, local storage or UI claims.
2. **BEGIN** (only from direct authorized operator action): host consumes intent, assigns its own fresh request ID, builds PKCE and returns a challenge-bound signed REQUESTED/UNAVAILABLE receipt. The client never supplies authorization state or provider endpoint.
3. **STATUS**: native host returns a request-scoped, signed monotonically sequenced bounded phase. `AUTHENTICATED` is a claim about the host-local session, not a provider-permission grant.
4. **CANCEL**: only for the exact pending request and independently approved action; a local dialog close or lost reply is not cancellation proof, and server-side external IdP revocation is not implied.
5. **RECOVER**: independently authorized new intent on a CANCELLED/FAILED request; host discards old credentials and mints a different request ID. Never automatic replay/undo.
6. **UNKNOWN / HOST LOSS**: if a command may have been sent and the receipt is missing/late, keep result **UNKNOWN_HOLD** at the integration boundary. Invalidate native client, refuse automatic BEGIN retry and require independent trusted host reconciliation and a new human decision. A transport timeout does not establish whether a browser opened.
7. **PROVIDER RIGHTS**: after personal sign-in, Telegram/Discord/organization-specific operations each require their own audited provider-specific scopes and consent. No implicit Connect All.

This is a **candidate** interface alignment document. It deliberately does not define unapproved signer custody, deployable socket locations, new key material, C5 grant bytes or a writable production ledger.

## VERIFY // Required negative acceptance before any native enablement

- Real official Fedora Silverblue signed Identity gateway running with enforcing SELinux; prove actual PID/start/unit/cgroup/loaded-module provenance, key continuity and boot/rollback by independently reviewed evidence
- Wrong/revoked release key, receipt-key swap, signer restart, stale PID reuse, substituted Python module, symlink/script replacement, wrong seat/lock state, forged peer, process death all refuse
- Missing/expired/replayed or cross-operation C5 intent, loss of consent after PREPARE, and one-use spend/ack ambiguity all refuse
- Exact one-shot BEGIN, pending CANCEL, terminal-only RECOVER, wrong/stale request IDs, action mismatch, nonce replay, out-of-order signed sequence, truncated or fragmented receipt, elapsed total deadline all refuse
- Side-effect ambiguity after dropped BEGIN or CANCEL response remains UNKNOWN_HOLD with no automatic reissue or false success badge
- QML remains credential-free and no action is enabled by `hostAuthenticated`, simulated signed `AUTHENTICATED`, private read-only context socket or synthetic CI fixture
- Disposable end-to-end login acceptance only after the cross-owner evidence above, then separate operator approval for actual installed runtime; no inference from CI workflow alone

## HOW TO USE

- DOC 1: use this as the request for protected issuer/history/seat witness, not as approval to adopt local test SQLite as trust.
- DOC 2: provide Identity-specific signed Silverblue installed-host/receipt lineage, not C4d's different service.
- C5: specify actual per-command operator intent and one-use SPENT/cancellation/unknown-outcome behavior.
- DOC 6: reconcile returned versioned interfaces on issue #1662; build a **separately reviewed** trusted production adapter, retaining hard-disabled CPU++ paths until all gates are independently accepted.
- Nurse 2: review this contract for cross-owner trust laundering, interface confusion and missing negative gates. This document has **no executable authority**.

## WATCH OUT FOR

DOC 1's operator direction is staged local development first, independent NAS/another host trust custodian later ([#2217](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2217)). Mainline source can be prepared now, but production native admission cannot trust the local test custodian. DOC 2's signed Silverblue combined C3e-AH execution ([#2211](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2211)) uses disposable test roots and remains deny-only. Neither merged milestone provides authorization.

## CHECKLIST

- [x] Reconcile latest merged DOC 6 timeout security fixes #2193/#2203
- [x] Inspect current installed adapter, receipt codec, C3e/C4b checkpoints and CPU++ default-deny path
- [x] Specify bounded owner evidence, negative acceptance and unknown-outcome handling as a **proposal**
- [ ] Explicit C3e/C4b/C5 interface acceptance and protected custodian policy
- [ ] Nurse 2 scoped contract review and operator disposition
- [ ] Owner-approved out-of-QML native bridge implementation and real signed Silverblue negative tests
- [ ] Operator acceptance for production installation and first real sign-in, separately granted provider permissions

## NEXT / DECISIONS

**NEXT:** Solicit exact versioned upstream interfaces on [Identity V5 coordination issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662). When the necessary evidence is independently accepted, implement only the narrow DOC 6 caller/projection without altering C3e, C4b, C5 or CPU++ ownership.

**DECISIONS:** No cross-owner implementation or production trust migration authorized by this document. No local Fedora/NAS write, live login, signing key enrollment, PR merge or Hospital registration. Operator retains final authority.
