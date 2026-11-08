# CPU++ / Telegram S1 // Provider revocation transaction contract (synthetic only)

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** CPU++ Connections / Telegram session actions, external Hospital-compatible handoff (not registered live)  
**ASSIGNMENT //** Prove the provider-side sign-out semantics, two-part review, scope identity and replay/uncertainty boundary without enabling a live destructive operation  
**STAFF ROLE //** Unassigned (external DOC-compatible implementation)  
**PROVIDER //** OPEN AI // CHATGPT  
**SOURCE BASE //** `54324172dac9d42897acb8da171edcdb08826de6`  
**PERMISSIONS //** GitHub review-branch tests/docs/CI only. No Fedora desktop edit, host installation, Telegram API access, actual consent, keyring, provider session mutation, production adapter import, source writer modification, PR merge or production activation.

## IMPLEMENTATION

The operator verified the CPU++ OPEN TELEGRAM route, and PR #1530 (live Telegram adapter last-check status + RECHECK SESSION) is merged. Both ID MANAGEMENT and CONNECTIONS retain the same canonical local account-name editor, as explicitly requested.

The next blocker is **the real provider-side revocation boundary**. Existing Connections C5a/C5b/C5c are CI-only experimental TASKS permission layers. None authenticates a human to revoke a production Telegram session. C4b's protected Silverblue tests are a separate **fake read-only service** owner, and C3e is signed-release governance, not Telegram provider consent. This branch does not change them.

The official **Telethon 1.x TelegramClient** API has materially different behaviors:

- `disconnect()` closes the Telegram network connection and does **not** sign the user out.
- `log_out()` logs the client out and **deletes its local `*.session` file**. The client object cannot be reused after that operation. Source: https://docs.telethon.dev/en/stable/modules/client.html#telethon.client.auth.AuthMethods.log_out
- Removing a local session file without a provider logout must never be reported as confirmed provider revocation. A failed/ambiguous logout must be treated as an unknown state requiring an independent recheck. The existing QR/phone workflow is the explicit reconnect entry point; never silently re-pair.

`tests/messaging/fixtures/telegram_session_revocation_m1.py` adds an **isolated in-process fake** of a future protected host/provider transaction. It can run only when explicitly constructed with `CPU_PLUS_TELEGRAM_FAKE_REVOKE_ONLY`, and it never imports Telethon or receives a real session, path, key, code, API hash, provider token or filesystem authority.

- **Prepare:** client may request only `telegram.session.revoke` and `log_out` for either exactly `shared` with empty ID or `private` with canonical `identity-N`. The mock provider independently supplies an authorized, idle synthetic session receipt: target, identity, generation and a non-secret test nonce. A UI nickname, stale READY label, caller-chosen path, generic Disconnect, wrong role or noncanonical ID cannot satisfy this.
- **Two-part reviewer check:** a separate synthetic-reviewer API must affirm both remote revocation and **loss of the local session file**. It requires the exact pending scope and identity. The review is simulated, **not** authenticated operator consent or a production host grant.
- **One-use execute:** approval expires after 30 seconds or is invalidated on revocation. The fixture marks the operation CONSUMED before calling the fake async `log_out()`. It reobserves the exact synthetic scope/session owner and refuses changed generation, identity, nonce, unauthorized state or busy operations. A repeated execution never performs a second logout.
- **After-call uncertainty:** only an exact boolean `True` fake provider acknowledgment and a compatible non-authorized post-state earns a result explicitly labeled **SYNTHETIC**. A false/missing response, exception, missing post-status or immediate replacement authorization is UNKNOWN, not a successful disconnect. Every result, including the positive synthetic result, keeps **all actual host, caller, consent, credential, session mutation and production permission flags false**.

This is a rehearsal for the transaction ordering and provider semantics, **not a working host and not an action in CPU++**. An in-process reviewer cannot authenticate a person or an installed binary, and code inside a same-user process cannot guarantee session protection against another same-user process.

## HOW TO USE

There is **no new desktop button and no action on a real Telegram account**. GitHub runs the disposable fixture through:

`python3 -m unittest discover -s tests/messaging -p 'test_telegram_session_revocation_contract_m1.py' -v`

Current production UI remains CPU++ → SETTINGS → CONNECTIONS → TELEGRAM // NATIVE. Its OPEN TELEGRAM and RECHECK SESSION operations continue working independently. **No red DISCONNECT** is displayed because the protected consent and revocation service does not yet exist.

## VERIFY

The S1 source tests cover absent approval, separate acknowledgments, malicious/extra fields, wrong target, shared vs private isolation, active send/pairing refusal, changed session generation or nonce before review/execute, expiry, revocation, replay, provider failure, ambiguous remote acknowledgment, uncertain post-status, and false actual-grant flags. CI reruns existing fake Telethon subprocess and identity isolation, live CPU++ route/status, closed broker and sole TASKS writer tests.

**Exact-head GitHub Actions must pass before declaring the test-only boundary verified.** This suite performs no network requests, live Telethon logout, protected service installation, real operator review, Fedora/Wayland session access, or desktop UI testing.

## WATCH OUT FOR

The **next real protected host** needs a separately approved, independently installed/signed identity, confinement, caller-origin check, operator approval channel, explicit per-provider `telegram.session.revoke` grant, correct account/session ownership, revocation/expiry/audit state and a way to prevent simultaneous native sends or login. Existing C5a-C5c TASKS test scopes must **not** be copied into Telegram as if they were a universal permission grant.

Uncertainty after `log_out()` can occur **after the irreversible provider action has happened**. The final UI cannot blindly retry in that state; it must explain UNKNOWN, re-probe correctly, and require a new decision. The future red button must say **SIGN OUT & REMOVE THIS DEVICE SESSION** or equivalently clearly disclose local session loss; generic `DISCONNECT` is misleading given Telethon's actual semantics.

Do not mistake `PROVIDER AUTHORIZED AT LAST CHECK` for a provider-authoritative, fresh sign-out grant. Do not implement logout by file unlink, by direct CPU++ QML process execution, or by a UI-supplied boolean approval.

## CHECKLIST

- [x] Reconfirm #1530 merged and identify C3e/C4b owner collisions
- [x] Verify provider's documented `disconnect()` vs `log_out()` effects
- [x] Add isolated single-use, identity-bound, two-part synthetic sign-out transaction
- [x] Add denied/ambiguous-result test cases and CI workflow
- [x] Leave production CPU++, Social, Connections broker, Telegram adapter and bridge unchanged
- [ ] Verify exact-head GitHub workflows, resolve any test failures
- [ ] Operator review/merge decision
- [ ] Coordinate approved production protected-host identity, release and consent with Connections owners
- [ ] Implement host-owned Telegram revocation against real provider; verify error/retry semantics and same-session isolation
- [ ] Add clear confirmed-destructive UI only after real host returns trustworthy results
- [ ] Operator native Fedora acceptance and separate CONNECT ALL approval/queue work

## NEXT

**Protected host cross-owner integration:** agree a real Telegram-provider operation scope and approval/deployment plan with the Connections host owners, including revocable consent, independently verified caller/session owner and per-operation audit. Then build a genuinely isolated provider adapter that invokes Telegram's `log_out()` only after that host authorizes a fresh, exact shared/private session. Test live sign-out and restart/re-pairing with a controlled account before enabling the destructive control in CPU++.

## DECISIONS

Do not claim live Hospital registration, accepted production trust, genuine consent, real sign-out, or final user acceptance. Preserve both account editor locations, CPU++ three bays, the existing Telegram native login/probe path, and all existing production default-deny flags. No PR merge, local files, credentials, Telegram account or production session changed. Handoff recovery is this file plus the PR and isolated test fixture.
