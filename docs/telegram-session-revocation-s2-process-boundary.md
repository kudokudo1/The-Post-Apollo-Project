# Telegram S2 // Kernel sender identity and separate reviewer for fake revoke

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** CPU++ Connected Accounts · Telegram session revocation (external continuity only, live Room unverified)  
**ASSIGNMENT //** Bind existing S1 fake single-use `log_out()` to real Linux process sender evidence, separate review channel and original C5b packet parser, without enabling production credentials or changing TASKS scope gates  
**PROVIDER //** OPEN AI // CHATGPT  
**STAFF ROLE //** unassigned (DOC-compatible external worker)  
**BASE //** `4549f2888f4bc3300738d47145e31d35f2622f20`  
**PERMISSIONS //** Bounded GitHub test/CI/docs-only review branch. No live Fedora changes, Telegram network, provider accounts, keys, session files, production host, saved source writer, automatic merge or host permission flags.

## IMPLEMENTATION

S1 PR #1541 merged and proved only a same-process fake reviewer and fake provider. Its one-use synthetic consent was **not** a protected IPC boundary. S2 adds an isolated **nonroot Linux test-only process transport**, executed under explicit `GITHUB_ACTIONS=true` and `POST_APOLLO_TELEGRAM_S2_DISPOSABLE` markers.

- A fake provider host is a distinct subprocess, holding the S1 fake review ledger and fake provider accounts **only inside its own memory**. A separate requester process gets one Unix `SOCK_SEQPACKET` endpoint. The synthetic reviewer (the disposable test harness) owns a different endpoint. Neither real credentials nor a real Telegram session are imported or read.
- Instead of building another generic Credentials broker, the S2 fixture **imports the existing C5b test-only** `SO_PASSCRED` / `SCM_CREDENTIALS` packet decoder and `/proc/<pid>/stat` process-start tick verifier. The test sender explicitly attaches Linux `SCM_CREDENTIALS` on **each** frame and the kernel validates the claimed PID/UID/GID. The reviewer binds the fake requester PID/UID/GID. Each client packet must match the bound kernel sender and process start tick. A malicious same-UID process using a transferred requester descriptor is refused. The reviewer identity is independently pinned from the **test harness** at host launch and checked against each review packet plus its process start tick; a transferred reviewer descriptor from another process is refused. The harness's pin is **not** authenticated human consent, installed executable attestation or production authority.
- The simulated reviewer must separately acknowledge remote Telegram revocation and losing the local session file before the host accepts S1 execution. This remains **fake, untrusted operator approval**, never a production reviewer. Scope `telegram.session.revoke` is distinct from C5a/C5b's three fixed **TASKS** scopes. No TASKS broker files, scopes, grants, owner or store are modified.
- S1 consumes the one-use request before invoking the **in-memory fake** provider. Stale source generation, revoked approval, wrong identity/scope, changed sender, fake provider exception or later replay is rejected. A successful synthetic result still returns every actual host/caller/consent/revocation/credential permission flag **false**.

The result improves *process-boundary evidence only*. It is not an independently signed executable, authenticated human operator, confined service UID, protected release installation or production host. In particular, the fixture is still a Python program launched in a test harness, and the harness controls both simulated reviewer and provider. A same-UID compromised user context may interfere with it.

## HOW TO USE

There is **no new CPU++ button** and **no real Telegram logout**. After authorized merge, GitHub's isolated workflow runs:

`python3 -m unittest discover -s tests/messaging -p 'test_telegram_session_revocation_s2.py' -v`

The existing desktop operations remain CPU++ → SETTINGS → CONNECTIONS → TELEGRAM // NATIVE → **OPEN TELEGRAM** and, with native Telegram active, **RECHECK SESSION**. Local saved account-name editing remains available in both CPU++ ID MANAGEMENT and CONNECTIONS via the same Social store.

## VERIFY

S2 tests exercise separate sender/reviewer processes, correct real kernel per-packet origin, transferred client descriptor from the same UID refused, transferred reviewer descriptor refused, exact shared/private scope, both fake review acknowledgments, synthetic one-use `log_out()`, replay/unknown provider result, revocation and changed synthetic session receipt. The workflow also reruns original S1, C5a/C5b, native Telegram fake Telethon/identity scopes, CPU++ navigation/status, Connections broker default-deny and TASKS sole writer. No actual Fedora user session, installed signature, SELinux confinement, provider network call or Telethon real `log_out()` is exercised.

## WATCH OUT FOR

**Process sender identification is not signed application identity or independently authenticated human consent.** The C5c signed executable proof is itself a disposable TASKS-only experiment and is not a Telegram grant. C3e signer/release authority and C4b Silverblue/SELinux work have separate owners. Do not widen their scope or infer production trust from the synthetic S2 success.

Telethon's `disconnect()` only closes the transport. Its `log_out()` revokes the device authorization and deletes the local session file. The eventual red control must clearly disclose both actions, verify the exact shared/private account and explicitly refuse uncertain or stale authorization rather than retry blindly.

The test fixture uses the original C5b packet parsing helper **read-only**. The actual C5b TASKS broker grants remain unchanged. It does not create a duplicate credential writer or a new installed host.

## CHECKLIST

- [x] Verify #1541, #1530 and #1522 merged, recheck open C3e/C4b owner PRs and Syntagma
- [x] Reuse C5b Linux per-packet origin / process-start utilities
- [x] Build isolated subprocess host, separate requester and synthetic reviewer descriptors
- [x] Preserve S1 exact-scope, one-use fake provider revocation and default-deny response flags
- [x] Add adversarial OS sender and fake provider tests, scoped CI and this recovery document
- [ ] Verify exact-head CI; fix failures if any
- [ ] Operator PR review/merge and final acceptance
- [ ] Coordinate protected signed/SELinux installed **Telegram-specific** host identity with C3e/C4b owners
- [ ] Independently authenticate operator consent for revoking one exact session
- [ ] Integrate real host-owned Telegram logout and post-operation confirmation
- [ ] Enable accurately labeled red sign-out only after above, test native Fedora

## NEXT

**S3 // Independently trusted Telegram host admission.** Coordinate with protected-host owners to bind the running, signed, installed Telegram provider client and reviewer to an independently pinned release and separate approved operator-consent channel, not a supplied process label or a same-user fake socket. Require explicit operation `telegram.session.revoke`, exact scoped account receipt and protected revocation state. Only then adapt the real Telegram provider's `log_out()` behind that host and add a red two-confirmation sign-out control. CONNECT ALL remains a separate permission-sequenced project after safe per-provider operations exist.

## DECISIONS

Keep both account-name management placements. No automatic sign-in/reconnect, real logout, local session unlink, broker flag changes, C5a/C5b/C5c authority escalation, release signing, workstation modifications, production services, automatic PR merge or Hospital registration claims. Operator retains final acceptance and production release authority. Recovery: this document and S2 test fixture/test/CI on the PR.
