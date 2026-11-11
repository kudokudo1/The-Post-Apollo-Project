# MACHINE // Offline persistent encrypted archive staging

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE / Brave recovery
STAFF // Hospital-compatible external DOC; no verified live Hospital attachment
ASSIGNMENT // Copy a verified sealed disposable record into private long-lived storage without trusting a native host

## IMPLEMENTATION

PR #1843 is merged on main. It supports opt-in encrypted selected-tab saving and authenticated read-back, but both native hosts remain bound to a disposable /tmp trial. Their extension-origin argument can be forged by another process with the same Linux user identity. Connecting those hosts directly to permanent browser data would breach the intended trust boundary.

MachineBraveOfflineArchive.py adds an **offline terminal-only archiving path**, not a new browser host, daemon, scheduled operation, or extension permission. It:

- Inspects an exact UUID record in a verified private disposable Brave trial after checking its existing transport, focus, title, save and read registrations.
- Returns the source SHA-256 and sealed size, without exposing ciphertext, URLs, page titles or a passphrase.
- Requires a separate archive operation with the expected SHA-256 and an exact local terminal confirmation reading ARCHIVE plus the full record UUID. It re-reads the source after the confirmation before any destination write.
- Uses the effective account home from the operating system rather than caller-controlled HOME/XDG_DATA_HOME for the production destination. It refuses symlinks, unowned/group-writable destination ancestors and unsafe existing storage, without chmod or overwrite.
- Copies only the existing AES-GCM encrypted envelope into the already tested private ciphertext vault under .local/share/post-apollo/machine/brave-sealed-vault. Files remain mode 0600, vault directories mode 0700, and writes are atomic and no-replace.
- Returns a new archive UUID. It detects an existing identical encrypted envelope and declines a routine duplicate import. The source record is never deleted or moved.
- Never accepts a passphrase or plaintext URL; never opens tabs, issues Sway commands, imports browser windows, or enables RESTORE.

IMPORTANT // A terminal confirmation is a deliberate workflow gate, **not cryptographic authentication** against another same-UID process. File permissions also do not protect against malicious programs under the same user. No production native host is connected to this archive. The ciphertext is shape-validated but is not authenticated against its original passphrase by this offline tool.

## HOW TO USE

The following is a future manual operator workflow only, after independent review, merge authorization and separate explicit local-write approval. No local installation was performed by this repository-only work.

1. Inspect the selected trial record:

    python3 -B -I services/time/MachineBraveOfflineArchive.py inspect /tmp/YOUR_VERIFIED_TRIAL YOUR_RECORD_UUID

2. Copy using the SHA-256 shown by inspect:

    python3 -B -I services/time/MachineBraveOfflineArchive.py archive /tmp/YOUR_VERIFIED_TRIAL YOUR_RECORD_UUID EXPECTED_SOURCE_SHA256

3. At the physical terminal, type exactly ARCHIVE YOUR_RECORD_UUID.

This copies only ciphertext. The original trial stays untouched. The new archive record ID differs from the temporary source ID. The vault normally survives reboot but is not a backup against disk failure. No new UI control exists, and the existing disposable read host cannot reach the home archive.

## VERIFY

Python tests construct actual marked /tmp trials and private destination fixtures. They cover consent refusal, digest mismatches, missing IDs, source symlinks/hardlinks/orphans, unsafe destination permissions, duplicate imports, source preservation and injected failed atomic writes. A Node test saves real synthetic selected-tab AES-GCM ciphertext, archives it through the offline function, and authenticates the archived record using the original test password. No real Brave browser data, local desktop installation or production profile is used.

## WATCH OUT FOR

- The disposable trial may disappear on reboot, so the manual archive must occur before then.
- Host origin and same-UID process trust remain unresolved; a TTY prompt cannot solve that by itself.
- Archived records remain encrypted, but the archiver cannot verify the GCM tag without the passphrase.
- No automatic access to permanent snapshots from Brave or TimeW, and no password recovery.
- Duplicate detection is intended for ordinary operator retries, not a concurrent adversary race.
- A failed write may have published a file before a later fsync/read error. Inspect records before retrying.
- Strong client identity must be coordinated with the existing Connections security owner rather than editing that lane from MACHINE.

## CHECKLIST

- [x] Source reconciliation, existing Hospital boundaries and merged read-back checkpoint
- [x] Separate offline encrypted archive without an untrusted persistent host
- [x] Exact source digest, explicit local confirmation, post-confirmation recheck
- [x] Fixed-account private vault, no-replace save and ordinary duplicate detection
- [x] Synthetic filesystem and genuine AES-GCM tests
- [ ] Exact-head CI and independent security review
- [ ] Operator-approved local archive acceptance
- [ ] Trusted native client/process evidence and production access policy
- [ ] Safe persistent record inventory, read, delete and dedup UI
- [ ] Restart mapping and multi-monitor browser restoration

## NEXT / DECISIONS

Remain draft and unmerged pending review. No local files, normal Brave profile, native host registration, Quickshell process, TimeW SAVE/RESTORE state or production activation were changed.
