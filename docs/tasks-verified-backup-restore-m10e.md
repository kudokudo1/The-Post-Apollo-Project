# 🏥💜 PROXY 1 // TASKS M10e Verified Backup & Restore Fixtures

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Worker:** Proxy 1, external ChatGPT development assignment; not live Hospital registered.  
**Scope:** CI-only, disposable test fixtures, not an active TASKS backup or restore command.

## IMPLEMENTATION

`tests/tasks/fixtures/verified_backup_restore_fixture.cjs` defines a
Node-only backup and restoration experiment in caller-selected directories.
The CI suite **only passes directories allocated through `mkdtempSync`**.

**Backup mechanism:**

1. Refuse symbolic-link/non-regular source files and untrusted backup-root paths.
2. Read original source bytes *as bytes*, without parsing, normalizing, editing
   or dropping unknown JSON keys. This captures even a future-version file
   before a later migration gate rejects it.
3. Reserve a unique backup ID, refusing duplicate or abandoned staging names.
4. Write `original.bytes` and a SHA-256 manifest into a new private staging
   directory; fsync both files.
5. Re-read the original to detect a change during copying, check staged
   checksum, fsync the staging directory, rename it to a committed backup name
   and fsync the backup root.
6. Re-open and verify the committed manifest and original bytes.

The backup directory has a manifest with `format`, `id`, `sourceName`,
`bytes` and `sha256`. A partially staged directory is NOT a committed
backup, and an existing committed backup is never silently overwritten.

**Restore mechanism (test-only):**

1. Verify the committed backup's manifest and SHA-256 first.
2. Require the **expected current SHA-256 of the destination file** as an
   explicit compare-and-replace gate.
3. Write restored bytes to a same-directory candidate and fsync.
4. Verify candidate hash and re-check destination fingerprint.
5. Rename over the destination and fsync the directory.
6. Re-read the target in the test to prove its bytes match the original backup.

For the future production restore, a passed fingerprint check is NOT enough:
the operator must explicitly authorize the action, the exclusive writer must
be stopped/locked, and pending journal/GitHub changes need an explicit
disposition. **This fixture is not a production recovery service.**

## HOW TO USE

GitHub CI only:

```sh
node tests/tasks/test_verified_backup_restore.cjs
```

Tests run entirely under OS-generated disposable CI temporary directories.
No path to the user's TASKS data, Quickshell runtime, or GitHub account is
opened, modified, or used.

## VERIFY

- Byte-for-byte backup of unusual whitespace, non-ASCII characters, legacy
  timestamps, current IDs, and even future/unknown fields.
- File and directory permissions, manifest integrity and SHA-256 readback.
- Refusal of duplicate backup IDs and incomplete staged capture.
- Capture interruption at creation, copy, manifest, precommit, post-rename,
  and final directory fsync.
- Simulated permission denial and disk-full errors.
- Refusal of damaged backups, malformed manifests, unsafe backup IDs, and
  symbolic-link backup folders.
- Restore blocked when target hash differs from expected version.
- Restore interruption before/after atomic rename, with clear old-or-new
  results for these in-process simulation boundaries.
- No reliance on a normalized v3 projection as the original-byte backup.

## WATCH OUT FOR

**Not yet tested or implemented:** hardware power loss, actual OS-level disk
exhaustion/permissions, concurrent writers, malicious symlink swaps between
checks, directory rename durability on different filesystems, cross-device
backups, key management/encryption, true storage adapter integration, or
migration on real user records. Exceptions injected within a process are not
proof of power-loss safety.

A successful rename observed before a directory fsync is NOT proof the file
will survive a physical power cut. An exception after rename may indicate
`COMMIT_UNCERTAIN`, not a safe opportunity to blindly retry.

Source-changed detection and target fingerprint comparison do not form an
atomic multi-process lock. The production migration needs an exclusive writer
protocol plus recovery of uncertain outcomes.

Backup manifest SHA-256 detects accidental modifications and mismatches; it
does not prove authenticity against a malicious actor able to modify **both**
the manifest and source bytes. Physical backup access and trusted storage
remain required.

The M10b journal remains a **prototype** and does not preserve historical
timestamps when later edited. M10d migration is a **dry-run only**. Neither
is connected to the live ApolloHubTodoStore writer or Proxy 2's PLANNER.

## CHECKLIST

- [x] Independent raw-byte preservation fixture
- [x] Hash manifest and committed/staged boundary
- [x] Guarded restore and stale-target rejection
- [x] Simulated interruption, corruption and access-failure tests
- [x] Separate CI workflow
- [ ] Confirm passing CI and independent source review
- [ ] Operator-authorized PR merge
- [ ] Live storage engine decision and exclusive-writer design
- [ ] Real platform failure injection, verified backup retention, rollback plan
- [ ] Operator-authorized production migration

## NEXT

After M10e: select an actual storage integration approach using the
existing Quickshell environment; design atomic model+queue persistence and
exclusive ownership; repair M10b's timestamps and validate duplicate raw JSON
keys before considering a live schema migration. Continue to provide
compatibility projections consumed by Apollo Hub, TODAY, and PLANNER.

## DECISIONS

No edits to `services/hub/ApolloHubTodoStore.qml`,
`ApolloHubTodoPolicy.js`, `widgets/TasksW.qml`, `shell.qml`,
GitW, GitHubProjectsService, Proxy 2 PLANNER files, or any user data.
Only four new CI-only test, workflow and documentation files are in scope.
