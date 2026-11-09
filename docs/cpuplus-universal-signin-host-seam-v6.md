# 🏥💜 CPU++ Universal Sign-In V6 // Actual Identity Center host integration seam

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** CPU++ Universal Sign-In visual integration (external, no verified live Hospital registration)  
**DOCTOR //** OpenAI ChatGPT, DOC-compatible UI/integration contributor  
**PROVIDER //** OPEN AI // CHATGPT  
**ASSIGNMENT //** Verify the current *real* Identity Center host interfaces against V5 BEGIN/CANCEL/RECOVER expectations and protect existing CPU++ default-deny behavior  
**BASE //** `925a359e4e13912a003e1fedb16a536e7effaa31`  
**PERMISSIONS //** Read protected host source and run existing disposable test modules; write only an additive CPU++ integration-readiness test, scoped CI and recovery document. No Identity/C3e/C4b/C5 owner files edited, no native Fedora machine changes, production activation, credential access or merge.

## IMPLEMENTATION

**Current state:** V1–V5 (#1614/#1619/#1623/#1650/#1660/#1663) have merged. Cross-Room [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662) remains OPEN, with no independent Identity Center owner approval/response recorded for an authenticated native command/status transport.

V6 is **not more mock login UI**. It checks the *actual* Identity Center host code and pins the precise integration gaps so the approved host owner can implement the correct real service without confusing a local method or display socket for an authorized command:

1. `services/identity/desktop_host_lifecycle_v0.py` currently offers internal `start()`, `begin_login()`, `logout()`, `close()` and callback/snapshot helpers. `begin_login()` requires a started host, active trusted seat and one unconsumed attempt, then calls the host's `DesktopSessionHost.start_login()`. It is **not a command IPC handler**, returns `LOGIN_PENDING` for injected test browser flow, and has no independently installed/exposed CPU++ endpoint.
2. It has **no request-scoped CANCEL** command. Its `logout()` explicitly revokes host-local state and pending authorization; binding this to CPU++ CANCEL would confuse cancellation of *one request* with session logout, without authenticated request ownership/acknowledgment.
3. It has **no RECOVER command**. The host lifecycle limits attempts to one per start; recovery needs a newly authorized, host-owned attempt or fresh independent lifecycle/instance, not repetition of a stale request ID.
4. `services/identity/private_context_ipc_v0.py` accepts fixed `SNAPSHOT\n` only and fails other packets closed to empty display. It uses a same-UID Linux Unix socket with limited display validation, **not a privileged authentication channel**. `IdentityCenterOrganizationDisplayReader.qml` only invokes the existing read-only `--json` reader.
5. `ConnectionsRequestStatus.qml` continues to expose `hostAuthenticated: false`, `canApprove: false`; the broker's credential actions are denied; CPU++ V4's `HostBoundary.offline()` and V5 `review()` neither send nor authorize messages.
6. There is no approved owner-issued authenticated request receipt, command sender/seat binding, production OIDC launch/token custody or real C5 consent path to CPU++ today.

Added `tests/cpuplus/test_cpuplus_identity_host_seam_v6.py` to **inspect actual owner-source AST** (without importing or invoking its login methods) and check the internal host method boundary, one-time attempt, logout-not-cancel distinction, read-only socket, QML denial and V5 review-only contract. Existing Identity Center host lifecycle, session and IPC test modules are run in **the CPU++ workflow as cross-component regression**, without modifying their source.

The test asserts the **current** absence of `cancel_login`, `recover_login` and `handle_command` methods. An approved Identity host owner implementation will intentionally require updating this test as part of its integration acceptance, rather than silently treating an added method as a production-reachable authenticated command.

## HOW TO USE

No user-facing menu changes. Operator's merged V4 UI remains **CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS** and must show Sign In/Cancel/Retry unavailable.

Identity Center owner can use [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662) plus V6 CI to review exact missing code and propose a versioned independently authenticated command service, with protected BEGIN, request-scoped CANCEL ack and fresh RECOVER receipt. C3e/C4b owners continue protected installed host/witness attestation, while C5 owner defines authenticated human consent separately.

## VERIFY

V6 suite: `python3 -m unittest discover -s tests/cpuplus -p 'test_cpuplus_identity_host_seam_v6.py' -v`.

Cross-regression in same exact-head workflow:
```bash
python3 -m unittest discover -s tests/identity -p 'test_desktop_host_lifecycle_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_desktop_session_host_v0.py' -v
python3 -m unittest discover -s tests/identity -p 'test_private_context_ipc_v0.py' -v
```
Plus original CPU++ V1–V5 test suite, Social editor/Telegram, Connections deny-only and Qt QML parser. **These are source, test-only and isolated host facts; no production login/session or provider connection tested.**

## WATCH OUT FOR

Do not expose or invoke `DesktopHostLifecycle.begin_login()` from QML, use `logout()` as the CANCEL action, or reinterpret the read-only AF_UNIX `SNAPSHOT` socket as authorized commands. The Identity Center service is still designated **CI-only integration**, not installed/attested native host. C4c signed Silverblue guest checks and C4d #1657 exporting a guest record are separate evidence, not production enrollment. A C5 synthetic consent result cannot authorize real providers or tenants.

The cross-owner test intentionally *reads* Identity Center code but does not own its implementation. Any future owner-authored command method addition will require a coordinated V6 gate revision, independent review and actual negative verification. Role, local machine and production permissions remain unchanged.

## CHECKLIST

- [x] Recheck main, V5 merged, open owner issue #1662 and Syntagma/Hospital rules
- [x] Inspect real merged Identity Center `DesktopHostLifecycle`, `DesktopSessionHost`, fixed display IPC
- [x] Pin BEGIN, CANCEL, RECOVER differences to exact real methods in a source-level CI gate
- [x] Wire existing real Identity Center host, session and IPC tests into CPU++ exact-head workflow
- [x] Preserve V4 UI and V5 denial gates, no fake adapter or credential code
- [ ] Exact-head CI pass and repair if needed
- [ ] Identity Center owner acceptance/revision of #1662 command/receipt contract
- [ ] Protected host installation/provenance, C5 real operator consent and negative authorization checks
- [ ] Operator-approved protected host adapter and real first login
- [ ] Operator final acceptance

## NEXT

**Owner implementation and approval of the independently authenticated native Identity Center command/status service**, separate from read-only display. The first functional contract must bind the direct user BEGIN gesture to one approved current seat/host, mint one-use request receipt/ID, control the host-owned OIDC callback and protected token custody; expose request-scoped CANCEL acknowledgment and fresh recovery semantics; deliver authenticated status events and revoke on host/seat loss. After C3e/C4b/C5 independent acceptance, CPU++ can add a narrow, reviewed client and unlock existing controls. Until then, keep them unavailable. Update V6 source gate only with that owner-approved change.

## DECISIONS

No duplicate login service or future fake UI step; the real host source and its current gaps are now under CPU++ integration CI coverage. No Identity/Connections worker ownership transferred, no local desktop or production code writes, no real secrets/login, automatic merge or live Hospital registration. Operator remains final acceptance authority.

**RECOVERY //** this document, V6 test/workflow, [issue #1662](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662).
