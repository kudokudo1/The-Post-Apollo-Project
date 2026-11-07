# 🏥💜 TASKS // M15b: Private Keyring-Backed Encrypted Draft Restart Integration

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS Source Integrity / Opt-In Encrypted Draft Recovery  
**ASSIGNMENT //** Connect existing vetted private draft encryption, atomic checkpoint storage, and Secret Service lifecycle through a genuine multi-process isolated integration check  
**STAFF ROLE //** External Hospital-compatible DOC / OPEN AI // CHATGPT, no verified live Hospital registration  
**CHECKPOINT //** M15a PR #1418 merged into `main`; M15b branch based on `c0a6712aa62b9b3b614f0442506255a7d34a54db`, November 7, 2026  
**PERMISSIONS //** Bounded GitHub fixture/CI/docs work only. No operator Fedora writes, no production TASKS draft capture, shared Connections credential action, live keyring, local process restart, PR merge or final acceptance.

## IMPLEMENTATION

### Why this milestone

M15a added **CHECK LOCAL SOURCE** in TASKS → SYNC → RECOVERY. That checks the actual saved JSON structurally after an explicit click, but cannot save an unfinished editor draft or recover it after a crash.

The accepted direction in M13f is **opt-in encrypted draft recovery across restarts**. M13g proved a disposable Secret Service key can survive separate process launches; M13m modeled AEAD source-bound encrypted checkpoints, M13o performed real atomic/fsync private ciphertext storage, and M13p/M13t modeled scoped consents. None of these individual tests established a **single joined end-to-end keyring + encrypted checkpoint file + restarted-process preview**. M15b joins those already-tested pieces before authorizing any real editor text.

### M15b implementation

1. **`TaskEncryptedDraftPrivateBridgeM15b.cjs`** (new, test-only): Compiles the existing M13m/M13o code with real Linux Secret Service calls. Under a fresh throwaway D-Bus session and owner-only temporary HOME, it creates a random 256-bit AES key, stores that key through `secret-tool store` on the **test bus only**, independently retrieves it, and compares with constant-time equality. It uses M13m's existing source-bound AES-256-GCM envelope and M13o's exclusive checkpoint lock/0600 atomic file, fsync directory and readback in a newly allocated `/tmp/postapollo-m13o-disposable-*` root. Nothing is written to real TASKS JSON.
2. The shell harness **`task_m15b_encrypted_draft_bridge.sh`** runs 8 separate Node processes under the same private D-Bus and disposable encrypted-checkpoint directory. It explicitly tests **capture → locked status → missing key refusal → wrong key rejection → source mismatch refusal → separately unlocked synthetic preview → ciphertext-only clear → no-checkpoint refusal**. The "preview" is synthetic, never a user-visible real draft. It deletes the **exact disposable key** separately after removing ciphertext, verifies both absent, and deletes only temporary roots it created.
3. Each subprocess has a strict isolation check: CI marker, private HOME under direct `/tmp/postapollo-m15b-private-*`, owner-only 0700 directory, private `unix:path=/tmp/dbus-...` session address, exact XDG subdirectories, nonroot Linux user, and M13o 0700 root. A normal user session or arbitrary source path returns a fixed refusal **before** keyring or filesystem work. These checks are **test precautions, not production authentication**.
4. The responses are fixed markers only. The key, source digest, stage identity, task text, fake draft marker, directory path and secret-tool output are never emitted in stdout/stderr. In-memory test key buffers are zeroized where possible, with no promise of complete JS heap erasure.
5. The original shared `ConnectionsBroker.qml` remains **`credentialActionsEnabled:false`**, while `ApolloHubTodoStore.qml` retains **one FileView / one setText** and hard-disabled encrypted recovery and ticket gates. M15b does not add an entry to `shell.qml`, import the new worker from QML, activate a host or accept real editor text. It also does not modify M13m/M13o fixture interfaces.

### Actual authority still missing

Successful test-only `optedIn:true`, an isolated keyring unlock, and a matching SHA-256 source digest are **not** real trusted operator consent or an independently authenticated saved TASKS revision. The M13p scopes remain distinct: `tasks.draft.capture.encrypted`, `tasks.draft.preview.unlocked`, and `tasks.draft.clear.encrypted`. The Connections owner currently denies each. Production activation must not happen without separately reviewed owner-specific consent, real key authorization, accurate source conflict handling and Fedora acceptance.

## HOW TO USE

**No local installation required.** The GitHub CI workflow installs a private test Secret Service on a disposable runner and executes:

```sh
dbus-run-session -- bash tests/tasks/tools/task_m15b_encrypted_draft_bridge.sh --run
```

It is deliberately **refused in an ordinary user session** and is not a command to paste into the user's Fedora desktop. The pre-existing TASKS → SYNC → RECOVERY interface continues to show accurate disabled encrypted recovery permissions, and M15a's **CHECK LOCAL SOURCE** remains available once deployed.

## VERIFY

The new workflow must show a successful genuine Secret Service full lifecycle and private file durability readback over separate processes. The additional Node source tests check ordinary-session refusal, Bash syntax, exact expected stages and guards, no real TASKS imports and unchanged production writer count. CI reruns M13f AES-GCM tamper refusal, M13m source binding, M13o atomic checkpoint CAS/locks, M13p/T consent denials, M15a real-source inspector and M11d/C2a ownership safety.

**Native Fedora/Quickshell is not exercised in this M15b milestone**, because the host is deliberately not attached to production editors or QML. The existing M13l already verified a native QML → Node → private keyring test under an isolated bus. M15b provides the missing joined durable checkpoint file and restart model.

## WATCH OUT FOR

- **Still not usable draft crash recovery:** Real editor text is not captured, a user consent is not persisted, the current desktop's Secret Service is not touched, and no real encrypted checkpoint is saved.
- This is a **synthetic fixture and real OS integration test**, not a security certification. No one may promote fake `consent:true` or a private CI keyring to a genuine grant.
- The ciphertext and source ledger share one atomic checkpoint file, but the saved task source and ciphertext are two distinct files. Matching their synthetic digests does not establish a trusted storage generation. Same-UID malicious writers, full-file rollback, keyring compromise, and power-loss conditions remain outside proven guarantees.
- The Python-based live JSON source checker from M15a provides structural information, not a source-identity credential. A separate trusted source-owner design would still be required before treating a write callback as confirmed or clearing an editor draft.
- Deleting encrypted ciphertext does not securely erase old SSD snapshots or backups. Deleting the OS key and the ciphertext are distinct operations; no user key or source is deleted by M15b.

## CHECKLIST

- [x] Confirm M15a merged, check canonical Syntagma/Hospital protocols, repository ownership and current main
- [x] Reuse M13m AES-GCM source binding and M13o existing private-file semantics
- [x] Integrate real private Secret Service key lifecycle across independent processes
- [x] Add missing/wrong key, source mismatch, locked-only, explicit clear, and cleanup tests
- [x] Keep real TASKS/Connections permissions and source writer unchanged
- [x] Add scoped CI and Hospital handoff
- [ ] Final exact-head CI verification
- [ ] Operator merge decision, without Nurse 2 review per latest operator instruction
- [ ] Authenticated, revocable scoped consent/key release from shared Connections owner
- [ ] Wire real editor draft lifecycle to approved encrypted host and preserve unfinished work after restart
- [ ] Separate operator-approved Fedora native integration and recovery acceptance

## NEXT // M15c

Implement a narrow, **production-shaped but default-disabled** key/capture/preview interface that consumes existing M13p consent scopes and M13o storage results without copying the test-only `secret-tool` host into running Quickshell. Coordinate explicitly with the Connections owner before modifying shared credential code. Once an authenticated consent owner exists, integrate live editor draft events with an opt-in capture trigger and encrypted checkpoint preview. Keep saved TASKS JSON a separate single authoritative writer, and never auto-replay a recovered draft or clear it solely because a callback arrived.

## DECISIONS

Independent Nurse 2 review is **not a gate for this assignment**, per the operator's November 7 instruction. CI, bounded security requirements and explicit user merge/deployment authorization remain intact. M15b may be merged after operator approval, but that will not activate protected storage or imply final acceptance. There is no live Hospital registration or local-machine write authority.
