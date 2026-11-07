# 🏥💜 TASKS // M15a Explicit Live Local Source Check

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS Source Integrity / Encrypted Draft Recovery  
**ASSIGNMENT //** Bring first production-facing, explicit **read-only** source evidence into existing TASKS recovery screen  
**STAFF ROLE //** External Hospital-compatible DOC / OPEN AI // CHATGPT; live Hospital registration not verified  
**CHECKPOINT //** GitHub main `8ba6f300d1c8cfdeb673d531e3e09c5986edea09` at M15a preflight, November 7, 2026; M14c PR #1413 was merged.  
**SCOPE/AUTHORITY //** GitHub source/tests/CI/docs **draft PR only**. No Fedora installation or file modifications, no merge, no live TASKS data accessed by this worker, no privileged broker, no keyring use, no automatic restore/deletion, no production encrypted checkpoint activation.

## IMPLEMENTATION

### Why this step

The user asked to progress toward a **usable** encrypted TASKS recovery experience rather than endless disconnected synthetic fixtures. M13y–M14c now test crash review with actual native Quickshell, but only on disposable SQLite/JSON. M14a's live FileView callbacks are not authenticated to source bytes. M13f approved **opt-in encrypted recovery across restarts** as the desired direction, but that does not authorize persistent sensitive user drafts before scoped keyring/consent/retention and production deployment decisions.

M15a is the first production-facing incremental bridge: **an explicit, operator-initiated read-only check of the actual saved TASKS JSON's structure**. It does not persist an unfinished draft or claim that a previously uncertain save was confirmed. It never uses M13y's fake journal to make claims about real data.

### New source check

`services/hub/TaskLocalSourceInspectM15a.py` is a standalone read-only CLI invoked only when the user clicks **CHECK LOCAL SOURCE**. The running TASKS screen passes the already-owned `ApolloHubTodoStore.storagePath` as one argument to `python3 -I -B`.

The helper requires an **absolute path ending in exactly `apollo-hub-todo-v1.json`**, a non-symlink parent directory owned by this desktop UID, a regular single-linked source owned by this UID, **owner-only file permissions**, a positive size up to 1 MiB, and `O_NOFOLLOW` inode-checked read-only `openat`. It checks file metadata before and after reading, UTF-8/JSON, rejects duplicate keys and nonfinite JSON values, and checks a deliberately narrow *structural* subset of version 1/2/3 TASKS shape: bounded task/project lists, essential IDs/titles/types and version sequences. It does **not** fully replicate `ApolloHubTodoPolicy.validate()`.

The reply contains **only** a fixed status, a boolean source-present flag, and optional structural task/project counts; all writer provenance, saved ACK, source revision, encrypted recovery, restore, draft deletion and key-release flags are literal false. It never returns the source content, title, description, ID, source path, file hash, key, private record, or native error text.

Possible statuses include **STRUCTURE READABLE**, **FILE ABSENT**, **PERMISSIONS NEED REVIEW**, **JSON INVALID**, **STRUCTURE INVALID**, **VERSION UNSUPPORTED**, **FILE CHANGED WHILE READING**, **UNSAFE PATH**, and **CHECK UNAVAILABLE**. A `0644` source is flagged for permission review without opening its task contents or changing permissions. This is observational only, **not** an automated chmod/remediation tool.

### Existing user-facing route

`TaskLocalSourceInspectPaneM15a.qml` is mounted once inside the existing `TaskRecoveryStatusPaneM13q.qml`, between live in-memory editor signals (M13s) and the existing M13z illustrative post-crash scenarios. The user sees:

```text
TASKS → SYNC → RECOVERY
LOCAL EDITORS // UNSAVED CONTENT STATUS
LOCAL SOURCE // READ-ONLY CHECK
 [CHECK LOCAL SOURCE]
 LOCAL SOURCE // NOT CHECKED
POST-CRASH SCENARIOS // EXAMPLES ONLY
RECOVERY PERMISSIONS // NOT ACTIVE
```

Clicking is required; merely opening the page does not start a process, watch the directory, use Secret Service, or read user data. The QML `Process` reads one bounded stdout JSON frame only; the pure `TaskLocalSourceInspectPolicyM15a.js` refuses unknown/extra fields and any attempted authority/grant. It waits for the process exit before accepting a result, refuses failures and extra lines, has a 5-second timeout, and refuses to run during an existing TASKS save.

A new real save request in this Quickshell session invalidates a previous successful result with **RECHECK REQUIRED**. This does not protect against external same-UID writers changing the source after inspection. Every displayed status explicitly says **ONE-TIME STRUCTURAL CHECK / SAVE AND WRITER NOT AUTHENTICATED**.

The production `ApolloHubTodoStore.qml` remains completely unchanged: **one FileView and one `todoFile.setText`**. The existing live callback panel, M13z examples, read-only C2 status and disabled encrypted draft/keyring gates remain intact. The new `Process` is a one-shot **reader**, not a second writer or persistence host.

## HOW TO USE

After independent Nurse 2 review, operator-authorized merge and **separate approval to deploy the updated code to Fedora**:

1. Open **TASKS → SYNC → RECOVERY**.
2. Find **LOCAL SOURCE // READ-ONLY CHECK** and click **CHECK LOCAL SOURCE**.
3. Read the returned status. **STRUCTURE READABLE** confirms only a bounded snapshot of the actual saved JSON was readable and structurally recognizable. **FILE ABSENT** or any refusal means no reliable source evidence was obtained. If file permissions are not owner-only, the result will say **PERMISSIONS NEED REVIEW** and will not open or modify content.
4. Return to TASKS to edit normally; no stored draft is created by a check. After a subsequent local write request, the result becomes **RECHECK REQUIRED**.

No terminal, keyring unlock, credential, new preference, background service or manual file path is required to use this feature.

## VERIFY

The new Python unit suite opens **real, disposable** local files and checks legitimate v1/v2/v3 structure, missing source, symlink/hardlink refusal, nonprivate permissions without automatic chmod, malformed/duplicate/oversized input, replaced inode during inspection and no source writes. It also launches the CLI in a real separate interpreter and verifies that private titles, paths and draft text do not appear in stdout/stderr.

The new Node/QML policy suite enforces exact status schema, fixed false authority flags, no data forwarding, canonical singleton source-path binding, click-only Process launch, stale-on-new-write handling, unchanged writer count and disabled Connections grants. CI reruns M13q/M13s/M13z/M14a/M13y, M11d and C2a, plus Qt 6 `qmlformat` syntax.

**Status //** PR CI and any future real Fedora/native acceptance must be verified independently. Python and QML syntax tests cannot establish actual desktop visual/focus behavior.

## WATCH OUT FOR

- **This is NOT an encrypted draft backup.** It cannot recover text lost in a crash. It cannot assert the saved source matches the latest memory document, tie an `onSaved` callback to a stage, or prove disk durability.
- It intentionally reads actual saved TASKS data **only when the operator clicks**, via a same-user process. The bounded results contain only counts and classifications; actual task contents pass through the process memory, not through the UI/IPC response. The source path is passed as a local command argument. No network.
- A structural acceptance result is **not** a full `TodoPolicy.validate()` pass, authentication of writer identity, or same-UID tamper resistance. A malicious same-user process may change source or metadata after checking. M12l's single local coordinator still has these explicit limitations.
- The source may already have mode bits `0644`; the helper will report **PERMISSIONS NEED REVIEW**, never silently alter the operator's files.
- An explicit check is not a guarantee the user's unsaved editors were backed up. The M13s live editor flags remain only in memory.
- No new keyring/consent policy is selected, and no recovery data is written or exported.

## CHECKLIST

- [x] M14c verified merged; inspect current main, Syntagma and Hospital ownership; no conflicting TASKS PR
- [x] Reuse the real canonical source path and existing RECOVERY route
- [x] Add manual-only read-only Linux source helper with strict no-text status
- [x] Add finite UI projection and stale-on-next-write behavior
- [x] Preserve all disabled recovery grants, separate Connections owner and sole JSON writer
- [x] Add real-file tests, integration tests and scoped CI
- [ ] Final exact-head CI, independent Nurse 2 security review and operator merge
- [ ] Separate authorized local Fedora visual/native execution and accurate-structure check
- [ ] Opt-in encrypted draft capture/unlock/recovery under shared Connections permission authority
- [ ] Verified save receipt/callback-to-source attribution and crash/restart acceptance

## NEXT

Next implementation should use the accepted M13f/M13o **opt-in encrypted draft** contracts to implement a narrowly scoped, owner-approved, fully encrypted checkpoint **capture/preview** path. It must acquire verified user consent and OS key material before persisting sensitive editor text. Recovering a draft returns it to a preview, not to canonical TASKS storage. A separate, independently reviewed source-owner model is needed before an ambiguous native callback can authorize clearing a draft.

## DECISIONS

M15a is **real saved-source structural inspection**, not real encrypted recovery, a trust anchor or a second writer. No changes to the shared Connections module, production store, user desktop, keyring, persisted drafts, saved task source, live Hospital registration or PR merge. The user remains final acceptance authority.
