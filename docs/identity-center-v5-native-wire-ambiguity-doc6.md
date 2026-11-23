# 🏥💜 DOC 6 // Identity V5 signed native client transport ambiguity

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections / Identity Center protected Sign-In  
**STAFF //** DOC 6 · external Hospital-compatible, live Room registration unverified  
**BASE //** `77eb3c63f36d0a7018d3ea015688f7b7255bf48b`  
**PRODUCTION //** HOLD

## IMPLEMENTATION

The already-merged native command client has a strict two-second end-to-end deadline, pinned signed receipts, and an explicit hard-fault on ambiguous command results. Prior to this patch, its `faulted` flag did not distinguish a refused connection **before any send** from a missing/invalid acknowledgement **after a send was attempted**.

Identity-owned `desktop_signed_command_client_v0.py` now records a **local, read-only diagnostic** `last_wire_outcome`:

| Value | Exact meaning | Never means |
| --- | --- | --- |
| `UNOBSERVED` | This client instance has no command transmission observation, including after a new process is constructed | Previous processes never attempted a command |
| `NO_SEND_ATTEMPT` | This individual call did not enter `sendall`; the client rejected it before transmission | The native host has no other pending request or it is safe to retry |
| `UNKNOWN_HOLD` | This call entered `sendall`, but no fully accepted, signed and timely response was completed | The host did nothing, a cancellation occurred, or a replay is safe |
| `SIGNED_FRAME_SEEN` | The strict signed receipt, deadline and final peer/seat checks passed for the call | Human consent, external IdP revocation, provider scopes, absence of side effects, or production authorization |

The client sets `UNKNOWN_HOLD` **before** attempting `sendall`, so even a partial write or broken pipe is conservatively ambiguous. A signed receipt becomes `SIGNED_FRAME_SEEN` only after existing nonce/action/request/host-instance/sequence, total deadline and independent connected-peer/seat checks succeed. Faulted clients remain unusable and no automatic repeat, retry, cancellation or recovery is introduced.

These observations live only in this Python process. They are **not durable recovery**, and the absence of a previous command observation after restarting the process is not evidence of a safe first BEGIN. A production recovery protocol needs the separately protected custodian, signed outcome reconciliation, and fresh C5 human intent.

## HOW TO USE

No desktop action. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains read-only with Sign In/CANCEL/RETRY disabled.

For CI review, run the existing native signed client suite:
```sh
python3 -m unittest discover -s tests/identity -p 'test_desktop_signed_command_client_v0.py' -v
```
This exercises the actual disposable AF_UNIX gateway, a fake browser/IdP, and negative cases for pre-send refusal, real BEGIN with lost signed reply, broken send and valid signed receipt.

## VERIFY

- [x] Same existing out-of-QML client, no new gateway/transport/provider.
- [x] No C3e, C4b, C5, CPU++, QML or installed-adapter edits.
- [x] Four new scoped negative tests; inherited source/receipt/CPU++ workflow triggers via modified existing client and test paths.
- [ ] Exact-head GitHub CI / all inherited tests.
- [ ] Independent Nurse 2 security review **before merge**.
- [ ] Operator merge decision; separate production approval.

## WATCH OUT FOR

**This is a local telemetry distinction, not authoritative command reconciliation.** In particular, a signed `UNAVAILABLE` receipt can follow partial host side effects. The only safe interpretation is that a signed frame was received, not that the host did nothing. Likewise the pre-send marker is not a global proof about commands in other processes or earlier instances.

If the native client may have dispatched BEGIN/CANCEL and the receipt is absent or rejected, remain `UNKNOWN_HOLD` and **do not open a new client to silently resend BEGIN**. A later independently protected host reconciliation and new operator gesture are required. The current native UI stays disabled.

## CHECKLIST

- [x] Recover exact merged/review-debt #2236 and current Identity source.
- [x] Add narrow client-local wire ambiguity observation.
- [x] Add four adversarial tests without real login/provider operations.
- [ ] Verify exact-head CI and request independent Nurse 2 pre-merge review.
- [ ] Operator accepts merge separately.
- [ ] DOC 1 protected custodian, DOC 2 verified installed Silverblue, independently issued C5 consent and native outcome recovery remain blocking.

## NEXT / DECISIONS

Request Nurse 2 review of the exact head, including whether `UNKNOWN_HOLD` is set before every possible side-effect-bearing send and never cleared by a thrown/replayed receipt. Later native integration must use independently signed cross-process outcome evidence, not this ephemeral marker, to settle an unknown command.

No new keys, local Fedora writes, merge, real IdP sign-in, runtime activation or live Hospital registration. All production authority stays false. Cross-owner source remains untouched.
