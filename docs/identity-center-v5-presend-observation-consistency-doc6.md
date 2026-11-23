# 🏥💜 DOC 6 // Identity V5 pre-send observation consistency

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center V5 native command  
**STAFF ROLE //** DOC 6, external Hospital-compatible (live Hospital registration unverified)  
**BASE //** `4828865507009530ee05a39671598114028f7440`  
**PRODUCTION SIGN-IN //** HOLD

## IMPLEMENTATION

This patch repairs a **specific** independently reviewed [#2246](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2246) diagnostic limitation: the signed client's `last_wire_outcome` was reset to `NO_SEND_ATTEMPT` **only after** early phase/request/nonce preconditions, so an early local rejection could leave a preceding `SIGNED_FRAME_SEEN` value showing as the most recent observation. A caller might misread the older signed result as the rejected command's result.

`SignedIdentityCommandClient._transact()` now marks `NO_SEND_ATTEMPT` **at the start of every non-faulted call**, before local command eligibility checks, challenge generation, frame building or socket setup. A duplicate BEGIN, STATUS/CANCEL/RECOVER without a host request, CANCEL from a terminal phase, RECOVER from a pending phase, or duplicate nonce therefore reports that **this rejected call never reached the native send boundary**.

Critically, the client's existing fault guard runs **before** this reset. When a prior command was already attempted and its outcome could not be authenticated, the client is permanently faulted and `last_wire_outcome` remains `UNKNOWN_HOLD` through any later denied BEGIN/STATUS/CANCEL/RECOVER calls. Even an earlier signed `UNAVAILABLE` is merely a signed frame observation and never proves a side-effect-free host. Existing socket/connected-peer/seat/pinned-Ed25519/total-deadline checks and `UNKNOWN_HOLD` assignment immediately before `sendall` are unchanged.

Six new tests reuse the existing **real disposable AF_UNIX gateway** and its fake IdP/browser. They cover all early request-missing cases, duplicate BEGIN after a signed REQUESTED, disallowed RECOVER while pending, disallowed CANCEL once CANCELLED, duplicate client challenge, and the full real BEGIN with deliberately missing verified reply followed by four blocked retries preserving `UNKNOWN_HOLD`. No new action, retry, persistence, provider permission, OAuth token or native QML binding.

This is a **client-local telemetry correction only**. A new client process still has no proof of prior sends. The rollback-vulnerable local SQLite reference [#2275](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2275), untrusted outcome candidate [#2289](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2289), and recorded signature shadow [#2349](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2349) remain **non-authorizing** and are not wired into this client.

## HOW TO USE

No new desktop control. CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains read-only; Sign-In/CANCEL/RETRY remain disabled.

For disposable CI:
```sh
python3 -m unittest discover -s tests/identity -p 'test_desktop_signed_command_client_v0.py' -v
```

## VERIFY

The existing `identity-center-signed-command-client-v0.yml` workflow automatically runs on changes to either modified file and includes the real signed gateway, Linux process-origin, lifecycle, CPU++ fixed-offline and native regression checks. Exact-head CI, raw logs, independent Nurse 2 security review and operator merge acceptance require separate verification.

## WATCH OUT FOR

`NO_SEND_ATTEMPT` means **only the current local invocation did not reach `sendall`**. It is not a global guarantee about prior commands, another client, same-UID file replacement, host state or consent. A faulted client never clears `UNKNOWN_HOLD` because a new rejected call cannot reconcile the previous ambiguous wire attempt.

Do not replace the protected original-command outcome issuer, independently enrolled C3e/C4b host/seat/root/current-history trust, or Identity-specific C5 one-use human consent with this telemetry. No production Sign-In authority.

## CHECKLIST

- [x] Confirm exact merged #2349 retrospective Nurse 2 source/CI PASS and current native signed-client source
- [x] Fix early local preflight report boundary without altering sender, verifier, host or QML
- [x] Add six adversarial signed-client regressions
- [ ] Exact-head GitHub CI and raw log verification
- [ ] Independent Nurse 2 pre-merge review
- [ ] Operator merge decision
- [ ] Protected C3e/C4b/C5 recovery and native acceptance remain blocked

## NEXT

Check exact-head CI. Request Nurse 2 scoped pre-merge review focused on: whether any pre-send rejection retains a stale signed observation; whether a post-send ambiguous fault remains sticky; and whether the correction permits any duplicate BEGIN, implicit recovery or native authorization. Final merge remains the operator's decision.

## DECISIONS

Development-only GitHub change to DOC 6-owned client/tests/doc. No production service, host key enrollment, real credential operation, local workstation write, external Hospital registration, cross-owner code change, Sign-In activation or automatic merge.
