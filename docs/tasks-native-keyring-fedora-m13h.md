# 🏥💜 TASKS // M13h Native Fedora Disposable Keyring Test

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS JSON writer continuity / opt-in encrypted draft recovery  
**ASSIGNMENT //** Native Fedora-session disposable Secret Service key write, readback, fresh-process decrypt, and exact-item cleanup  
**PROVIDER //** OPEN AI // CHATGPT, external Hospital-compatible, no verified live Hospital registration  
**GITHUB BASE //** `56982637c2e0a298910b3c87c976045237aa2d07` (Nov 3, 2026)  
**AUTHORITY //** User approved proceeding after explicit request to test a disposable keyring write/retrieve/delete. Repository code changes are limited to a separate draft branch; **only operator execution on Fedora can perform the live disposable test**. No local mutation was performed by this browser worker.

## IMPLEMENTATION

### Prior verified evidence

- M13g [PR #1094](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1094) **merged** at `0d079505e90c38ce6d58abde3ad8f715227194c6`. It passed real GNOME Keyring/Secret Service synthetic encryption and recovery using a CI-only D-Bus session and temporary HOME.
- The operator's **read-only Fedora commands** identified `org.freedesktop.secrets` owned by `/usr/bin/gnome-keyring-daemon --daemonize --login`, PID 3902 at the time of observation. `gdbus` and `secret-tool` were present. This proves an existing provider on the user's running desktop, **not** that the collection is unlocked or that application-specific authentication exists.
- M13f AES-256-GCM pure test code supports synthetic authenticated encryption with identity-bound AAD, a locked no-draft indicator and fail-closed unlock. Production `ApolloHubTodoStore.qml` still has one `FileView` and one `todoFile.setText()`; ticket, guarded-writer and independent-receipt gates remain compile-disabled.
- No competing open TASKS PR was identified at branch creation. Live Quickshell was not inspected or restarted. The local worktree may contain unrelated changes and must not be pulled, reset or cleaned for this task.

### M13h native acceptance harness

New `tests/tasks/fixtures/TaskNativeKeyringRecoveryM13h.cjs` is an **operator-invoked test script**. Without `--native-disposable-test`, it performs no writes and returns `M13H_MANUAL_DISPOSABLE_TEST_ONLY`. It refuses non-Linux/root sessions, missing D-Bus and unavailable Secret Service, and does not itself launch or unlock the keyring daemon.

When the operator explicitly runs it in the already-running Fedora desktop session:

1. Generate a unique random 128-bit test selector and a random 256-bit fake encryption key **in process memory**. It checks that its exact selector has no existing keyring item, then creates **one** clearly labeled keyring item with two attributes: `post-apollo-test=post-apollo-tasks-m13h-disposable-test` and `nonce=<random-selector>`.
2. Use `secret-tool store` via stdin, never sending the key through argv, environment variables or logs; retrieve only the same test selector and compare keys with timing-safe comparison.
3. Call the **existing M13f AES-256-GCM fixture**, using a fixed synthetic draft and fake stage/epoch identity. Only ciphertext is written through exclusive creation `O_CREAT|O_EXCL|O_NOFOLLOW` to a new private `/tmp/postapollo-m13h-XXXXXXXX/draft.enc` (file 0600, directory 0700) with file and directory fsync.
4. Launch a **second Node process**, passing only the random nonsecret selector and the disposable ciphertext filename. This process retrieves its key independently from the actual running GNOME Keyring, verifies the locked-view no-title rule, and decrypts the ciphertext. Success is reported as `M13H_FRESH_PROCESS_RECOVERY_PASS` only inside the parent; neither process prints draft content or key material. A separate missing-item check must fail closed.
5. In a `finally` cleanup block, clear **only** the item with those two unique attributes, check lookup no longer returns a key, unlink **only** `draft.enc` in the generated private directory, and remove that empty directory. A failed/ambiguous cleanup reports `REFUSED_TEST_CLEANUP_UNVERIFIED`, plus the nonsecret selector or temp path needed to investigate. A cryptographic PASS accompanied by leftover material is **not** accepted.
6. Emit the sole success marker `M13H_NATIVE_ENCRYPTED_RESTART_PASS` when all required checks and cleanup succeed.

The keyring item persists only during the manual test, which is designed not to overwrite an existing entry. A prompt may appear if the operator's collection is locked, but this script does not auto-unlock or change system login preferences. If the provider refuses or times out, the test fails without enabling anything.

The workflow executes **the same operator-facing Node script** on a GitHub runner inside `dbus-run-session` with a throwaway GNOME Keyring and private HOME. This validates the exact harness before running it against Fedora, but only the operator's actual terminal output can establish the native workstation result.

## HOW TO USE

The operator may run the test **after reviewing the merged/tested harness**, using a separate disposable download directory. Do **not** pull/checkout/reset the live Quickshell repository. Obtain both these unchanged files from the same reviewed repository snapshot:

- `tests/tasks/fixtures/TaskNativeKeyringRecoveryM13h.cjs`
- `tests/tasks/fixtures/TaskEncryptedRecoveryM13f.cjs`

Then run:

```bash
node TaskNativeKeyringRecoveryM13h.cjs --native-disposable-test
```

The command must run **as the normal desktop user**, not with sudo, from the existing Fedora graphical session. The script requires `node`, `secret-tool`, `gdbus`, the active user D-Bus session, and the two sibling test files. It does not require Quickshell to restart.

Expected positive result:

```text
M13H_NATIVE_ENCRYPTED_RESTART_PASS
```

If it returns `REFUSED_...`, treat that as a non-passing test. Do not claim the provider is suitable until the cause is understood. If a cleanup-unverified marker includes a random ID, the **only** legitimate manual keyring cleanup target is:

```bash
secret-tool clear \
  post-apollo-test post-apollo-tasks-m13h-disposable-test \
  nonce '<random-ID-reported-by-the-test>'
```

Do not run that command with a guessed ID, omit the nonce attribute, list unrelated secrets or clear any collection. If a temporary test file remains, inspect only the reported `/tmp/postapollo-m13h-...` path before taking further action.

## VERIFY

CI requires:
- No-argument harness never touches keyring.
- Native test script has explicit opt-in, random selector, same-item clear, exclusive disposable ciphertext write, no broad recursive cleanup and no production TASKS path.
- The exact manual script PASS against an isolated real GNOME Keyring/Secret Service in CI; missing-key refusal and item cleanup are part of the harness.
- M13g isolated Secret Service integration, M13f encryption/tamper tests and M11d production single-writer/disabled-gate tests remain green.

**What success does NOT prove:** hardware reboot durability, a user-approved unlock UX, key availability after keyring/OS restart, per-app Secret Service authentication, encrypted backup/rotation, malicious same-UID process resistance, OS-level power-loss behavior, or live TASKS recovery. A fresh Node process while the user session continues is not the same as a full system reboot.

## WATCH OUT FOR

- The operator **has authorized a disposable keyring test**, not production key storage or activation. Do not store actual TASKS drafts or keys. Only the labeled random test item may be created and cleared.
- Secret Service may be unlocked by login and can provide secrets to other eligible user-session clients. A successful test must not be marketed as app-specific authentication.
- This fixture handles fake key bytes in Node memory; memory wiping is best-effort and does not cover strings, swap or core dumps. It does not expose real credentials or private task data.
- The operator's browser/network may have intermittent HTTPS failures; the test runner itself does not access any network. Acquire the reviewed files separately and verify their exact source before execution.
- Do not call `gnome-keyring-daemon --unlock` or `secret-tool clear` with broader selectors on the actual desktop.
- Preserve the dirty local Quickshell worktree and existing `apollo-hub-todo-v1.json`.
- Current ticket producer, authenticated receipt and guarded write path remain **disabled** in production.

## CHECKLIST

- [x] Recheck merged M13g, Syntagma, main and ownership
- [x] Reuse real M13f AES-256-GCM fixture rather than create a second crypto API
- [x] Native manual test has explicit invocation, one random keyring item, and one disposable ciphertext path
- [x] Fresh-process retrieval and missing-item refusal
- [x] Exact targeted cleanup and recovery pointers
- [x] Isolated CI execution and no-production-change source gates
- [ ] GitHub CI reviewed and merge authorized by operator
- [ ] Operator runs exactly this harness in Fedora and returns status markers
- [ ] Operator selects actual unlock/collection/key lifecycle and backups
- [ ] Separate disposable native Quickshell integration and production security review
- [ ] Real opt-in recovery UI and activation with final operator acceptance

## NEXT

If this test passes natively, the immediate engineering follow-up is a separately authorized **disabled-only Quickshell host boundary for encrypted drafts**, under the existing single-coordinator architecture. The host must not reuse M13a plaintext stages as persistent secrets. Decide the consent mechanism, locked-state metadata, keyring collection access and key loss/backup strategy before allowing real drafts. Recheck native process/task ownership and local repo state before any live work.

## DECISIONS

**Verified prior:** Secret Service is GNOME Keyring on the user's Fedora session; real isolated CI provider test passed and merged.  
**Approved here:** perform one disposable synthetic keyring write/read/clear test on Fedora.  
**Still not selected:** production key provider (beyond candidate), user unlock method, permissions, recovery path, backup/key rotation, deletion/retention details, or production activation.  
**Not done:** local test execution, live Hospital registration, desktop modification, ticket enablement, PR merge, or user acceptance.
