# 🏥💜 TASKS M13k // Disabled Encrypted-Draft Host IPC

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity and opt-in encrypted draft recovery  
**ASSIGNMENT //** Connect a disabled QML component to a synthetic encrypted-draft host over real process stdin/stdout, reusing existing authenticated encryption and isolated GNOME Keyring tests  
**WORKER //** OPEN AI // CHATGPT · external Hospital-compatible doctor, no verified live Hospital registration  
**BASE //** GitHub `main` `1d81e9031feb11e6e79df4aa82d9cf8d310113fa`, November 3, 2026  
**PERMISSIONS //** Repository-only, separate draft branch: no local machine edits, keyring mutation, Quickshell restart, migration, real TASKS draft capture, extra source writer, production activation or PR merge.

## IMPLEMENTATION

### Confirmed handoff

- M13h [PR #1103](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1103) is merged and the operator reported `M13H_NATIVE_ENCRYPTED_RESTART_PASS` from Fedora, with fake data, cleanup and real GNOME Keyring.
- M13i [PR #1118](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1118) is merged. It introduced a dormant provider-status QML bridge into the sole TASKS singleton. The missing QML type registration was corrected by [PR #1120](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1120).
- M13j [PR #1141](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1141) is merged. The operator supplied a successful native `Configuration Loaded` and screenshot showing `PROVIDER // SERVICE_ACQUIRED`. This confirms the read-only provider status path Quickshell → Python → session D-Bus. It does **not** prove that encrypted recovery of real TASKS drafts is active.
- The canonical source remains `services/hub/ApolloHubTodoStore.qml`: one `FileView`, one `todoFile.setText()`, and exactly the existing public task mutations. Existing `guardedWriterEnabled`, `ticketProducerEnabled`, `independentlyAuthenticatedTicketReceipt` and encrypted-recovery flags are all literal **false**. There were no competing open TASKS PRs at M13k preflight.

### What this milestone actually adds

1. `tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs`: a **one-request Node host** meant to exercise the future Process/QML IPC shape with actual isolated cryptography and keyring. It takes a single fixed JSON line on stdin (`protocol:1`, `kind:RUN_SYNTHETIC_DRAFT`, `consent:CI_ONLY`) and returns one strictly bounded JSON status envelope on stdout. The `consent` field is a CI marker, **not authenticated operator consent**. It accepts no task/draft payload from QML.
2. **Fail closed before Secret Service:** the Node host refuses unless `--single-request`, non-root Linux, explicitly set `POST_APOLLO_M13K_ISOLATED=1`, existing M13g disposable gate, a 0700 owner-matched private `/tmp/postapollo-m13g-m13k-...` HOME, private XDG paths and an ephemeral `unix:path=/tmp/dbus-...` session bus address. It explicitly rejects the normal `/run/user/<uid>/bus` session endpoint. These are a **disposable-test environment restriction**, not a security boundary against an attacker who controls the process environment or can impersonate the bus.
3. **Real synthetic round trip:** inside the guard, the host delegates to the existing M13g fixture in *separate Node processes*: store a synthetic AES-256-GCM key in real Secret Service, create an exclusive private ciphertext file, recover it via fresh-process key lookup, verify missing-key refusal. The host does not receive plaintext draft or key material from QML and returns **status only**. It deletes exactly its fake test item (M13g-specific label/ID) and that known private ciphertext path, checking absence. Cleanup ambiguity invalidates PASS.
4. `services/hub/TaskEncryptedDraftHostBridgeM13k.qml`: dormant QML `Process` with `stdinEnabled`, `SplitParser`, strict one-reply JSON schema and fail-closed exit/status handling. It never starts automatically. The synthetic action is hidden behind CI environment markers, and all production/user draft/source-write/key-release permissions remain **literal false**.
5. `services/hub/ApolloHubTodoStore.qml`: embeds a single dormant M13k component and exposes read-only status only. Adds **no new public method**, task writer, source mutation, timer, persistent draft or keyring operation. The original live TASKS API remains intact.
6. `services/hub/qmldir`: explicitly registers `TaskEncryptedDraftHostBridgeM13k 1.0 TaskEncryptedDraftHostBridgeM13k.qml` as part of the same commit. This prevents repeating M13i's unregistered-type startup failure.
7. `TaskEncryptedDraftHarnessM13k.qml`: standalone, **unmounted** test panel showing fake encrypted-host status. Its button is locked in any normal session. It is not imported from `shell.qml`.
8. `tests/tasks/fixtures/TaskEncryptedDraftHostPrivateM13k.sh` and CI: create a disposable D-Bus + GNOME Keyring + private HOME in GitHub runners, issue the **exact QML-style stdin JSON request** to the real Node host, assert authenticated synthetic recovery and absent key/file, repeat the test twice to catch sticky state. Negative tests verify no access without private markers. Qt `qmlformat` parses changed QML and M11d enforces one authoritative production writer.

This is materially stronger than an abstract encryption model: it exercises a real one-shot process IPC protocol against GNOME Keyring and a real AES-GCM ciphertext file. **It is still a synthetic host and is not permitted to operate on user drafts.**

## HOW TO USE

No local tasks, local source changes, or user keyring commands are required. For operator review see the M13k PR and its GitHub CI check.

On the standard Fedora desktop, do **not** set the private CI environment marker or start the synthetic host. The standalone panel is for isolated QA environments only. **The normal TASKS UI is unchanged.**

CI's success marker is `M13K_PRIVATE_HOST_IPC_AND_CLEANUP_PASS`. The Node reply's success status is `M13K_SYNTHETIC_ENCRYPTED_RESTART_PASS`. No plaintext, credentials, labels or draft data are emitted in the status result.

## VERIFY

- Unqualified `node tests/tasks/fixtures/TaskEncryptedDraftHostM13k.cjs` is refused without a request.
- Explicit request in a normal user session is refused before starting `secret-tool` or touching disk.
- Missing/forged/unsupported request shapes are refused; successful return includes all **false** production permissions.
- CI starts fresh `dbus-run-session` with a throwaway GNOME Keyring; actual synthetic key and ciphertext survive a child-process restart and are cleared before PASS.
- Qt QML parser checks bridge, standalone panel and TASKS singleton.
- `qmldir` registration has an explicit assertion. M13i and M11d regression tests preserve the original TASKS writer, public mutation API and disabled gates.

**Not verified:** running this M13k bridge inside the operator's Fedora Quickshell process, user opt-in or authenticated app identity, full PC reboot, source-integrity backed durable receipt, rollback protection, real draft storage/retention, trustworthy key release or production activation.

## WATCH OUT FOR

- The literal `CI_ONLY` request field is **not a credential** and the test environment checks are not proof of trust against a malicious same-user process.
- `SERVICE_ACQUIRED` proves only that a name is owned on a bus, not a keyring unlock guarantee.
- The synthetic host reuses M13g's **fixed test label/ID** and must run on a newly created private bus. It refuses an existing item/file and only clears its exact fake key if it has attempted a new creation.
- A cleanup failure reports a refusal, not success; the isolated CI wrapper removes its entire private HOME after the run. **Never run this wrapper against a real session bus, even with fake data.**
- This M13k bridge is not a production key provider, application authorization, replay-protected draft transaction or source writer.
- The source test can parse QML and verify declarations but cannot prove the native Quickshell Process callback behavior; a later isolated native acceptance check is required before user-facing integration.
- User's dirty live `~/.config/quickshell` worktree must not be pulled, reset, checked out, replaced, or restarted in this milestone.

## CHECKLIST

- [x] Recheck merged M13h, M13i, M13j, current main, Syntagma and no active TASKS PR collision
- [x] Real synthetic host and one-request fixed status IPC
- [x] Private-bus guard and fail-closed normal Fedora-session refusal
- [x] Mount inert QML host bridge in sole TASKS coordinator, update `qmldir` in same branch
- [x] Standalone unmounted panel and exact source tests
- [x] GitHub CI real isolated keyring, QML parser, prior-source regressions
- [ ] CI complete, independent review and operator PR review/merge
- [ ] Isolated native Quickshell Process IPC callback test
- [ ] Authenticated opt-in, key-release and source rollback/retention design
- [ ] Separately authorized production encrypted draft storage/restore and operator acceptance

## NEXT

After green CI, the next step should be an **isolated native Quickshell end-to-end QML Process test** on a completely private D-Bus/Home (not the normal Fedora user bus), with status-only evidence. Then design a production host protocol with explicit opt-in, key scope, authenticated last-confirmed-source binding, lock/unlock workflow and durable-recovery checks. No real data yet.

## DECISIONS

**Verified previously:** actual Fedora GNOME Keyring supports disposable authenticated encrypted recovery, and M13j QML provider-status discovery works natively.  
**Selected for M13k:** dormant one-request synthetic IPC to existing M13g real Secret Service cipher fixture, with no live writes.  
**Not selected:** production key release, live encrypted draft data model, task source authority, unlock UI, recovery conflict policy, backup/retention or activation.  
**Not performed:** live desktop mutation, local Git operation, user keyring change, task migration, PR merge, production rollout or live Hospital session registration.
