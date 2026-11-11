# MACHINE // Authenticated encrypted read-back, disposable Brave V1

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE / Brave session recovery
STAFF // DOC, external Hospital-compatible; no verified live Hospital registration
ASSIGNMENT // Read one encrypted test snapshot and authenticate it in Brave, revealing only redacted tab metadata

## IMPLEMENTATION

PR #1838 is merged on main. It enables explicit selected-tab AES-256-GCM encryption, with a ciphertext-only save host in a marked private /tmp disposable trial. It had no browser read-back.

This PR adds a **separate read-only native host** (MachineBraveReadHost.py), registered only through MachineBraveReadTrial.py after the existing save host and its transport/focus/title dependencies verify. Its exact-origin manifest remains inside the isolated temporary Brave configuration. The host accepts a canonical record UUID, a fresh challenge and explicit read flag. It reads the encrypted record without decrypting or modifying it, and returns only its sealed envelope and digest. It has no list/put/delete/Sway/MOVE/RESTORE operation and ignores the caller's XDG data path.

The extension's new **OPEN ENCRYPTED READ REVIEW** creates an isolated review tab only when clicked; it requires existing nativeMessaging permission but no tab URL permission or browser history access. The user enters a saved record UUID and the original passphrase and presses **DECRYPT AND REVIEW ONCE**. Browser WebCrypto derives the key using the envelope's PBKDF2-HMAC-SHA256 parameters, authenticates the AES-256-GCM tag with exact AAD, and validates the decrypted session schema. Only the window label, tab positions, hostnames, pinned/active flags and sensitive URL counts enter the visible review. No full URLs, query strings or fragments are exposed.

**FORGET THIS PREVIEW** clears visible contents and the record ID. Blur, tab hiding and page teardown also clear contents and invalidate in-flight replies. The decrypted byte buffer is zeroed. Immutable browser JS strings cannot be guaranteed physically zeroized. No browser sites are opened and no TimeW checkpoint or window placement is altered.

## HOW TO USE

After independent source review and **separate explicit local authorization**, register only inside the already verified disposable trial:

    python3 -B -I services/time/MachineBraveReadTrial.py register /tmp/YOUR_VERIFIED_TRIAL TEST_EXTENSION_ID
    python3 -B -I services/time/MachineBraveReadTrial.py verify /tmp/YOUR_VERIFIED_TRIAL

In the temporary Brave instance: brave://extensions → Reload the unpacked MACHINE extension → MACHINE popup → **OPEN ENCRYPTED READ REVIEW**. Paste the opaque record UUID from the previous save, enter its original passphrase, then click **DECRYPT AND REVIEW ONCE**. Expected status is **AES-GCM AUTHENTICATED // REDACTED REVIEW // NO RESTORE**. Finally choose **FORGET THIS PREVIEW** and **CLOSE REVIEW TAB**.

The test vault is still in /tmp. Its records may disappear on restart. It is not a durable backup.

## VERIFY

Synthetic tests exercise authenticated WebCrypto decrypt and wrong-password/tampered-ciphertext refusal; strict encrypted host response shape; full selected-tab save → real native host → private test ciphertext file → separate read host → WebCrypto-authenticated redacted inventory. Tests also verify missing records, wrong origin, no file mutation, no auto-read on opening the UI, and focus-loss invalidation. CI is not a Fedora/Brave real-runtime acceptance test.

## WATCH OUT FOR

This is **not persistent production storage** and native messaging's supplied origin argument is not cryptographically authenticated against same-UID local processes. The restriction to marked disposable /tmp trials remains mandatory. The stored SHA-256 covers ciphertext file consistency, not AES-GCM authenticity; only decryption with a correct key authenticates the saved plaintext. Window labels and tab counts do not prove which Brave window belongs to which Sway monitor. No restore authority, duplicate prevention, production host, password recovery, automatic browser launch or monitoring is added.

## CHECKLIST / NEXT

- [x] Existing encrypted save prerequisite checked on main.
- [x] Separate read-only host and exact verified disposable registration.
- [x] Browser WebCrypto authenticate and hostname-only review.
- [x] Explicit read/forget and stale UI result revocation.
- [x] Crypto, native and mocked UI regression tests.
- [ ] Exact-head CI, independent review and operator merge decision.
- [ ] Approved disposable Brave runtime test.
- [ ] Stronger origin identity and protected persistent snapshot storage.
- [ ] Explicit authorized decrypt/import, deduplication and multi-monitor restore.

## DECISIONS

Repository-only; no local machine writes, global registration, normal Brave access, browser profile modification, Quickshell restart, production activation or restore. The next implementation milestone is persistent client-authenticated storage, not bypassing this trial's security boundary.
