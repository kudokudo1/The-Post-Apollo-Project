# 🏥💜 TASKS M13g // Linux Secret Service Provider Capability and Unlock Boundary

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity / opt-in encrypted recovery  
**ASSIGNMENT //** Verify real Secret Service capability in disposable CI and prepare a non-activating Fedora desktop inspection  
**WORKER //** OPEN AI // CHATGPT · external Hospital-compatible doctor; live registration **not verified**  
**BASELINE //** GitHub `main` `f2032e0d70a84d0ccaa22d51fe1f5d9300893b7f` on November 3, 2026  
**PERMISSION //** Repository-only test/docs/CI changes; no operator machine writes, local keyring access, installed packages, live Quickshell modifications, or production activation.

## IMPLEMENTATION

### Recovered checkpoint and decision

- [M13f PR #1089](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1089) merged at `bd85c5fff96b8af57691ecf23629d1564d3732fa`. M13f's pure Node AES-256-GCM fixture had already demonstrated synthetic encrypted file recovery across independent processes using an **ephemeral key passed through a test pipe**, not a real key provider.
- The operator selected **opt-in encrypted recovery across restarts**, not a particular persistent key store. M13e's [draft privacy dossier](./tasks-draft-storage-privacy-decision-m13e.md) remains background policy; M12l specifies one canonical local TASKS write authority.
- The production `services/hub/ApolloHubTodoStore.qml` has one `FileView` and one `todoFile.setText()`; `guardedWriterEnabled:false`, `ticketProducerEnabled:false`, `independentlyAuthenticatedTicketReceipt:false`. There were no competing open TASKS PRs at preflight.

### Actual mechanism and new test

**Secret Service** is a D-Bus specification for keeping secrets in a session service. GNOME Keyring is one provider, but the API does not promise isolation between arbitrary programs of the same logged-in user. Its metadata attributes can be unencrypted. A keyring may unlock during OS login or prompt on demand, and items or collections may be shared with other clients after unlock. This means **having the key in a keyring is not, by itself, a verified Post-Apollo per-app unlock or trusted identity proof**.

M13g adds:

1. `tests/tasks/fixtures/TaskSecretServiceProbeM13g.py` queries only the session bus daemon's `org.freedesktop.DBus.NameHasOwner("org.freedesktop.secrets")` using `gdbus`. It **cannot auto-activate** the target service. It does not enumerate items, read keys, call `OpenSession`, unlock, store, delete or reveal DBus connection/username/path details. Its fixed JSON answer distinguishes acquired, not running, unavailable bus, absent probe tool and unexpected result. An acquired name is only availability, not evidence that a collection is unlocked or secure.
2. `tests/tasks/test_task_secret_service_probe_m13g.py` mocks the D-Bus command, verifying exactly one call to the **bus daemon** rather than the secret service, no activation, a bounded timeout and no leaked stdout/stderr.
3. `tests/tasks/fixtures/TaskSecretServiceRoundTripM13g.cjs` is a **disposable-only CI tool** using a private temp HOME and a new `dbus-run-session`. In its first Node process, it generates one random synthetic 32-byte AES key, stores its base64 representation in the *real* GNOME Keyring via `secret-tool store`, immediately reads it back using `secret-tool lookup`, then encrypts a fake M13f draft and writes only ciphertext to `m13g-disposable/draft.enc` with `O_CREAT|O_EXCL|O_NOFOLLOW`, mode 0600 and file+directory fsync. No separate task-data writer is involved.
4. In a **separate second Node process** on the same isolated D-Bus session, it calls the actual `secret-tool lookup` again, decrypts the ciphertext with the existing M13f AES-256-GCM code and outputs a single fixed `SYNTHETIC_SECRET_SERVICE_RESTART_PASS` marker. It never places the key in environment variables, command arguments, the repository, logs or the ciphertext file. Missing key/item and no item after `secret-tool clear` fail closed.
5. `TaskSecretServiceIsolatedM13g.sh` runs the test in a disposable CI-only session with `HOME`, `XDG_DATA_HOME`, `XDG_CONFIG_HOME` and `XDG_CACHE_HOME` redirected under a private `/tmp/postapollo-m13g-XXXXXXXX` directory. The ephemeral **CI-only** keyring password is sent through stdin to `gnome-keyring-daemon --unlock --components=secrets`; no real operator passwords are used. It clears only the synthetic key on the private bus. No command in this test can target the real user's home path under its restrictive guard.
6. The GitHub workflow installs GNOME Keyring, libsecret CLI, D-Bus and `gdbus` **inside the disposable GitHub runner only**. It reruns M13f, M13e and the M11d one-authoritative-writer inventory.

The CI demonstrates an actual Secret Service key retrieval path across processes, unlike M13f's simulated parent-delivered key. It still does **not** run the operator's Fedora session, prove a UI authorization prompt, or verify malicious same-user key isolation.

## HOW TO USE

No install, local source update, or production task action is necessary to review this PR.

To inspect the user's *actual Fedora session* **read-only**, the operator may choose to run:

```bash
command -v gdbus
command -v secret-tool
command -v gnome-keyring-daemon

gdbus call --session \
  --dest org.freedesktop.DBus \
  --object-path /org/freedesktop/DBus \
  --method org.freedesktop.DBus.NameHasOwner \
  org.freedesktop.secrets
```

**Interpretation:** `(true,)` means a service currently owns `org.freedesktop.secrets`. `(false,)` means there is no currently acquired owner, **not** that one cannot be installed or auto-started later. A failed call means the local session bus or tool requires investigation. The check itself does not call or start the keyring service.

This is intentionally safer than using `secret-tool lookup` or `gdbus introspect --dest org.freedesktop.secrets` on the real desktop, since those may activate the service or interact with secrets.

## VERIFY

GitHub CI steps:

- Bounded read-only probe command contract, missing tools/bus and alternate results.
- Private GNOME Keyring started on a separate throwaway D-Bus bus and HOME; actual `secret-tool store`, then `lookup`.
- New process loads encrypted M13f fake draft using a key retrieved from Secret Service, **not** from inherited key argument/env or a startup-key pipe.
- Missing key and cleared fake key fail closed without revealing draft contents.
- Existing M13f crypto tamper/nonce cases, M13e privacy refusal and M11d production disabled gates remain green.

**Evidence limit:** CI uses Ubuntu/Node, not the user's Fedora 44 Silverblue, sway, Quickshell or personal keyring. No real keyring has been inspected or configured by ChatGPT. No actual on-demand prompt or user authorization, production key lifecycle, key loss/recovery, key rotation, rollback or power-cut durability is verified.

## WATCH OUT FOR

- An already unlocked GNOME Keyring can allow eligible same-session apps to request known secrets. Secret Service is a key storage API, **not** standalone per-application authorization. A future design should explicitly decide if an extra user-entered passphrase or locked collection is necessary.
- Lookup attributes are often plaintext metadata. Never include draft title, description, exact project, organization, private note, user identity or task contents as keyring lookup attributes.
- The fixed CI-only label and key ID are not production names or trust credentials. The hardcoded CI keyring password is safe **only** because the entire test runs with fake data in an ephemeral isolated process/home.
- `--unlock` can initialize a new keyring, so it **must never be run against the operator's session without separate approval**. This PR confines that operation to CI.
- Key recovery on actual reboot is unverified; the test closes only Node processes, **not** the D-Bus/keyring service between them. A future separate keyring-reattach/reboot test must be done with permissioned disposable data.
- The test retains a synthetic ciphertext file for the duration of the CI job and deletes the private test directory afterward. It never stores production task data or drafts.
- The key is handled in process memory and briefly transferred through Secret Service D-Bus. This is not protection from a malicious same-user process or memory inspection.
- The operating system may use alternative providers such as KeePassXC or KWallet implementing the same API. Do not switch providers or install GNOME Keyring on Fedora merely because the CI used it.
- **All production gates remain closed.** A successful CI provider test is not authorization to enable ticket writes, mount encrypted draft recovery, create a permanent helper, update local files or modify OS/keyring configuration.

## CHECKLIST

- [x] Verify merged M13f and current GitHub/Syntagma/owner state
- [x] Review existing M13f AES-GCM and production storage boundary
- [x] Add read-only desktop D-Bus owner probe and negative tests
- [x] Add real isolated Linux Secret Service key store/lookup/reopen test
- [x] Isolate bus/HOME and never use real user credentials or data
- [x] Preserve legacy single-writer and disabled-ticket source gates
- [ ] GitHub CI complete and independently inspect actual provider test logs
- [ ] Operator review/merge
- [ ] Operator may run read-only probe on Fedora and share status only
- [ ] Choose actual key-provider/unlock UX and app permission strategy
- [ ] Disposable **native Fedora/Quickshell** test and security review before any production integration

## NEXT

Once this isolated provider test is reviewed, establish what Secret Service implementation, if any, is currently present on the operator's Fedora Sway session using the read-only commands above. The next implementation should be a **disabled-only native host integration using synthetic draft bytes** under an operator-approved key provider and unlock flow. If the session lacks Secret Service, present opt-in setup options rather than installing packages automatically.

Do not create production drafts, edit the live singleton, modify keyrings, auto-unlock or enable ticket production.

## DECISIONS

**Selected by operator:** opt-in encrypted draft recovery across application restarts.  
**Demonstrated in test:** real Secret Service on a throwaway CI bus with a synthetic stored AES key, independent process retrieval and encrypted fake draft recovery, subject to CI results.  
**Not yet chosen:** GNOME Keyring vs other provider, actual unlock prompt/passphrase, key backup/rotation, application authorization, metadata disclosure, live storage path, deletion/retention/exports, or production activation.  
**Unchanged:** M12l single authority, existing JSON store, user environment, unactivated tickets, no live Hospital registration.
