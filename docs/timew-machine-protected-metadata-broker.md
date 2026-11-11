# MACHINE // Protected archive metadata broker contract (CI-only, deny by default)

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Brave encrypted recovery
STAFF // External Hospital-compatible DOC; no verified live Hospital registration
ASSIGNMENT // Separate permanent ciphertext storage from normal Brave and define a strictly read-only future broker boundary
CONNECTIONS HANDOFF // PR #1855 comment 6795713946; Connections C3e/DOC retains its own assignment and review role

## IMPLEMENTATION

This is a **disconnected, deny-only architecture test**, not a production service or a Brave extension feature. The offline encrypted snapshot importer and LIST/INSPECT/DELETE manager from merged PRs #1849 and #1855 remain unchanged.

`MachineBraveProtectedMetadataContract.py` defines one bounded AF_UNIX framed request containing only:
- `LIST_METADATA`: fixed kind, action and canonical challenge UUID
- `INSPECT_METADATA`: same plus one canonical record UUID

Only a kernel `SO_PEERCRED` read supplies peer PID, UID and GID. Browser-supplied `uid`, `pid`, `origin`, `authorized`, arbitrary file path and other fields are refused. The protected archive root is provided separately by a hypothetical trusted supervisor; request JSON cannot choose the root. The reader opens the root with `O_DIRECTORY|O_NOFOLLOW`, requires it to be owned exclusively by the **running non-root service UID** and mode 0700, then reads 0600 owner-matched, single-link encrypted records by descriptor-relative path. It rejects symlinks, unknown filenames, unfinished temp files and malformed entries. Only opaque record IDs, UTC timestamps, sealed byte counts and SHA-256 hashes can leave the reader. No ciphertext or passphrase is returned.

The handler **always denies by default** because independent client identity, session/seat/lock state, signed release, C3e evidence and C5 one-use operator consent have not yet been connected. A separately named `test_only_grant` injection exists solely to exercise synthetic metadata output in CI; its successful replies are explicitly named `test_only_metadata_listed` or `test_only_metadata_inspected` and keep `client_authenticated:false` and `operator_consent_verified:false`. There is no runnable service `main`, socket listener, installer, RPM, systemd unit, native-messaging manifest or production key.

**Important:** kernel PID/UID/GID alone does not establish a genuine signed client, Brave extension, unlocked seat, non-replayed human consent or trusted process image. Checking a supplied extension ID, a claimed PID or a user-owned executable path cannot solve that problem. This implementation does not claim that it does.

## VERIFY

The dedicated GitHub Actions privileged **temporary CI-only** fixture runs separate numeric Linux UIDs:
- A synthetic browser UID.
- A different non-root service UID that exclusively owns a temporary 0700 archive and 0600 ciphertext record.
- A foreign third UID.

It checks the browser UID is rejected by Linux when attempting **direct open, directory listing, write, chmod and unlink**, without contacting the broker. A separate CI-only AF_UNIX test listener runs as the service UID. Its default runtime gate refuses valid requests, even when correctly framed. Malicious JSON claims (fake origin, claimed UID, path, authority, malformed UUID and DELETE) refuse. A synthetic test-only callback exercises successful metadata list/inspect, while preserving false authentication/consent fields, not exposing ciphertext, and leaving the protected record unchanged. Foreign UID is refused. Unsafe mode, wrong owner, file symlink, unfinished write orphans and malformed records also refuse.

The CI runner uses `sudo -n` solely inside ephemeral GitHub Actions to assign numeric test UIDs. It does **not** create user accounts, change /etc/passwd, change SELinux/AppArmor policies, or mutate any operator workstation. If root privilege is unavailable, this security test must fail rather than pretending a mock proves direct bypass prevention.

## HOW TO USE

There is **no user-facing operation yet**. Do not run the test broker on the operator machine, copy current home archives into it, or register a browser host. The existing offline manager stays available in its documented scope. The intended future runtime shape is:

1. An operator-reviewed migration/backup procedure moves only ciphertext to storage owned by a **different dedicated service account** with no traversal rights for the ordinary desktop/browser UID. No silent chown or move of live user files.
2. A signed, independently supervised client connects to a dedicated Unix socket. The broker obtains kernel peer credentials and verified PID start time / pidfd, release witness, cgroup and security label, active unlocked logind seat/session, and purpose-bound one-use C5 consent. Nothing is accepted merely because it claims an extension ID.
3. Only after all independent checks and atomic replay consumption may one `LIST_METADATA` or `INSPECT_METADATA` query return safe metadata. No direct ciphertext export, password, delete, restore or background polling.

## WATCH OUT FOR

- **No production client authorization exists.** `test_only_grant` is an injected CI fixture, not permission to expose protected records.
- There is **no installed protected service identity**, no approved filesystem migration, no authenticated client/seat witness, no C5 consent issuer, and no replay ledger. This code alone cannot make a real normal-Brave browser safe.
- `SO_PEERCRED` pins socket peer credentials but does not by itself prevent process replacement, PID reuse or identify the extension driving a browser.
- Unix 0700 protection is effective only when the protected files are actually owned by another restricted OS principal. It does nothing to isolate processes with the same archive-owning UID.
- The metadata reader verifies encrypted file structure, not AES-GCM tags without a passphrase; a checksum verifies file bytes, not trusted browser contents.
- A root process or sufficiently privileged attacker can bypass ordinary ownership checks; this milestone tests **ordinary unprivileged browser-UID bypass** only.
- CI fixtures are not deployment acceptance. No production activation, native registration, browser restore, permanent encrypted read-back, or real user file ownership changes.

## CHECKLIST

- [x] Recheck Syntagma, merged #1855 and exact Connections handoff
- [x] New bounded read-only broker protocol and deny-only runtime contract
- [x] Distinct non-root archive-owner UID and strict metadata-only reader
- [x] CI kernel permission denial for browser UID, foreign UID and fake-origin cases
- [ ] Exact-head CI and independent NRS-2 security review
- [ ] C3e verified signed/process/seat witness contract and C5 one-use consent interface
- [ ] Operator-approved protected service install, archive migration/backup and rollback
- [ ] Replay ledger and audited metadata broker lifecycle
- [ ] Real browser/TimeW metadata viewing, protected ciphertext transfer and eventual restore

## NEXT / DECISIONS

MACHINE owns this implementation. Connections C3e remains its owner and reviewer; C5 owns operator consent. A cross-room comment is a contract handoff, not a transfer of Time Machine ownership or authorization to modify those lanes. PR remains review-only, unmerged pending explicit operator decision. No local machine writes were performed.
