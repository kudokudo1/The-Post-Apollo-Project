# MACHINE // Offline encrypted archive manager

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE / Brave recovery
STAFF // External Hospital-compatible DOC; live Hospital registration not verified
ASSIGNMENT // Metadata-only persistent archive list/inspect and explicitly confirmed single-record deletion

## IMPLEMENTATION

PR #1849 is merged on main. Its offline archive copies a verified sealed /tmp Brave snapshot into the current Unix account's private long-lived vault without granting native hosts permanent access.

MachineBraveOfflineArchiveManager.py adds an **offline, terminal-only** tool:

- LIST returns opaque record UUID, UTC creation time, sealed size, checksum and total count, with no plaintext URL, passphrase or ciphertext. A missing archive is not created.
- INSPECT UUID validates one encrypted record and shows metadata only. The checksum does not authenticate AES-GCM.
- DELETE UUID EXPECTED_SHA256 checks current file/digest, asks for a precise typed confirmation through /dev/tty, rechecks the selected record after confirmation and invokes the existing checksum-aware one-record deletion. A failed confirmation does not remove anything. No DELETE ALL, background deletion or automatic cleanup is provided.

The normal CLI obtains its storage path from the effective Unix account rather than HOME or XDG_DATA_HOME. There is no CLI path override, no native host registration, no new Brave permission, no TimeW change or restoration authority. Tests may inject a temporary data directory.

TTY confirmation and Unix file permissions are workflow safeguards, **not cryptographic authentication of other processes under the same Unix user**. The final checksum-guarded unlink remains an optimistic race boundary under an adversarial same-UID process. Deletion is irreversible in this tool.

## HOW TO USE

After separate independent source review, operator merge authorization and explicit local-write approval, the planned operations are:

1. List stored encrypted records:

    python3 -B -I services/time/MachineBraveOfflineArchiveManager.py list

2. Inspect one record:

    python3 -B -I services/time/MachineBraveOfflineArchiveManager.py inspect YOUR_RECORD_UUID

3. Delete precisely the selected record using its current checksum:

    python3 -B -I services/time/MachineBraveOfflineArchiveManager.py delete YOUR_RECORD_UUID EXPECTED_SHA256

4. At the controlling local terminal type exactly DELETE followed by a space and YOUR_RECORD_UUID.
5. List again and verify only that record is absent. After an unexpected filesystem error, inspect first rather than blindly retrying.

No new Post-Apollo widget button is installed, and normal Brave cannot reach the archive.

## VERIFY

Tests use two synthetic sealed records in an isolated temporary vault. They cover no-create listing, no plaintext disclosure, exact record metadata, wrong checksums, refused confirmation, changed record after confirmation, symlinks, insecure modes, incomplete writes, unmodified neighboring records, exactly one confirmed delete, and a missing controlling terminal. CI also runs the prior offline archive, actual synthetic WebCrypto ciphertext and sealed-vault privacy tests.

## WATCH OUT FOR

- This offline archive is not an off-machine backup.
- Permanent deletion cannot be undone in this tool; no user data is deleted by CI.
- Native host extension-origin strings remain insufficient to grant persistent storage authority.
- File consistency SHA-256 is not AES-GCM authentication and a TTY prompt is not strong identity verification.
- Hostile same-UID races remain outside the current safety guarantees.

## CHECKLIST

- [x] Canonical protocols, prior merge and owned MACHINE seam checked
- [x] Metadata-only list and inspect with fixed account destination
- [x] Typed digest-guarded deletion, post-prompt revalidation
- [x] Synthetic malformed, race-change and adjacent-record preservation tests
- [ ] Exact-head CI, independent security review and operator merge decision
- [ ] Separately approved live local test
- [ ] Strong client identity coordinated with Connections security owner
- [ ] TimeW read-only archive browsing and eventually trusted restoration

## NEXT / DECISIONS

Keep source PR unmerged absent operator authorization. No browser, Quickshell, native host, local files, TimeW checkpoint or production state were changed by this repository-only work.
