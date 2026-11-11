# MACHINE // Explicit selected-tab encrypted save pilot

PATIENT // The-Post-Apollo-Project  
ROOM // TimeW MACHINE / Brave restart-safe recovery development  
STAFF ROLE // DOC, external Hospital-compatible worker; live Hospital registration not verified  
ASSIGNMENT // Connect consented Brave tab selection to client-side encryption and a disposable ciphertext-only native receiver  
SCOPE // Disposable Brave extension and separately registered trial host only; not production, TimeW RESTORE or system activation

## IMPLEMENTATION

PR #1836 introduced a strict private-file **ciphertext-only vault** in
`MachineBraveSealedVault.py`, merged to main. This milestone connects
it to **explicit user-selected tabs**, while retaining the existing
privacy boundary and disallowing any restore behavior.

**New Post-Apollo MACHINE Brave pilot 0.5.0**

- Popup: **OPEN SEALED SAVE REVIEW** button, after the operator separately
  grants optional `tabs` and `nativeMessaging` permissions using
  the existing popup controls. This opens a new extension tab inside the
  same normal non-private Brave window, preserving a temporary reference
  to the previously active tab. Opening is a **user action** and changes
  the active tab to the review page; the original tabs are not navigated
  or modified.
- Review: **LOAD CURRENT WINDOW TABS ONCE** reads only the same normal,
  non-private window after checking both active permissions and its own
  extension-tab identity. Existing URLs are retained only in the review
  page's transient JavaScript memory. The list shows tab position,
  hostname and eligibility, but not the full URL path, query, fragment,
  title or content. Each checkbox starts **unchecked**.
- Internal pages, file URLs and embedded-credential URLs are excluded.
  Query/fragment-bearing addresses require an additional explicit
  **ALLOW ... QUERY / FRAGMENT URLS** checkbox before they can be
  selected. The user must individually check each tab.
- **ENCRYPT AND SAVE CHECKED TABS ONCE** requires: checked tabs, an
  operator label, a 16+ character matching passphrase, and a distinct
  explicit consent checkbox. The code re-reads the same window immediately
  before encrypting and rejects a changed URL/index/pinned state or
  changed browser permissions. The original active-tab reference is used
  only to mark the pre-review active tab, not a durable identity.
- `session-seal.mjs` creates an **AES-256-GCM** envelope using
  browser WebCrypto, PBKDF2-HMAC-SHA256 at 600,000 iterations, unique
  16-byte salt and 12-byte nonce, and exact authenticated additional
  data `machine-brave-sealed-session-v1`. Derived keys are not
  exportable. The encrypted JSON contains the user label, selected tab
  URLs, positions, pinned flags and the original active-tab indication;
  there are **no Chromium or Sway IDs in the encrypted payload**.
  The plain UTF-8 buffer is zeroed after encryption; immutable JS
  strings cannot be guaranteed physically zeroized by the browser.
- Only the opaque encrypted envelope is sent to the dedicated
  `org.postapollo.machine_brave_save_trial` native host; the
  passphrase and tab URL strings are never sent to that host.
  The native host validates one bounded native-messaging frame,
  an exact canonical UUID challenge and allowed request fields,
  then uses the **already merged sealed vault** to write ciphertext.
- Host registration is **separate and disposable only**:
  `MachineBraveSaveTrial.py register ROOT EXTENSION_ID` refuses any
  non-marked directory, mismatched existing transport/focus/title
  registrations, symlinks, collisions and unsafe modes. It installs
  only the host and vault-source bundle plus an exact-origin manifest
  into the private `/tmp/postapollo-machine-brave-trial-*` root.
  It creates `ROOT/vault-data` with mode 0700. The native host
  **ignores caller XDG_DATA_HOME** and forces all new storage underneath
  `ROOT/vault-data/post-apollo/machine/brave-sealed-vault`.
  No global XDG registration or normal Brave profile is modified.
- A verified response displays an opaque record UUID. No browser
  URLs, encryption passphrase or snapshot contents are displayed, logged
  or stored in the extension. Closing or blurring the review drops the
  in-memory list. No automatic retries, background workers,
  session restore or window placement actions are added.

### Critical security boundary

A Chromium native-messaging allowed-origin argument is not strong
authentication against arbitrary processes already running as the same
Linux user. For that reason, this host is intentionally **limited to
the marked disposable test trial**. The native host cannot validate
an AES-GCM tag without the passphrase; it only validates envelope
shape and writes ciphertext. A matching host response proves that
a file was written, not that future decryption will succeed.

## HOW TO USE (operator-approved disposable trial only)

This PR is repository-only. **No local files have been installed by
this development session.** After independent security review and a
separate operator approval to write under the disposable trial:

1. Verify the trial's existing title host:
   `MachineBraveTitleTrial.py verify TRIAL_ROOT`.
2. Register and verify the save host using the exact original test
   extension ID, inside the marked /tmp trial:

   ```sh
   python3 -B -I services/time/MachineBraveSaveTrial.py register \
     /tmp/YOUR_MARKED_TRIAL YOUR_TEST_EXTENSION_ID
   python3 -B -I services/time/MachineBraveSaveTrial.py verify \
     /tmp/YOUR_MARKED_TRIAL
   ```

3. In the **disposable** Brave browser only, open
   `brave://extensions` and reload the unpacked MACHINE pilot.
   In its popup use **ALLOW LOCAL CONNECTION** and
   **ALLOW TAB ADDRESS ACCESS** if not already granted, then
   **OPEN SEALED SAVE REVIEW**.
4. Click **LOAD CURRENT WINDOW TABS ONCE**. Select only the intended
   tabs. Optionally allow the extra review gate for URLs containing
   query strings or fragments.
5. Supply a unique operator label and a strong passphrase, confirm
   it, check the explicit saving consent, then click
   **ENCRYPT AND SAVE CHECKED TABS ONCE**. The result is a test-vault
   record UUID. Do not reuse this test passphrase as an account password.
6. Close the review tab. Grant/revoke optional tab and native
   permissions using the existing popup controls as appropriate.

The isolated `/tmp` trial and ciphertext vault can disappear on
restart. This phase does **NOT** offer persistent production storage,
cross-restart browser recreation, or multi-monitor restoration.
There is no automated recovery of forgotten encryption passphrases.

## VERIFY

Dedicated CI tests real browser-compatible AES-GCM/PBKDF2 encryption of
synthetic selected URLs, nonce/salt uniqueness, decryption and tamper
failure, strict nonce-bound native response validation, explicit
browser review and zero-read-before-consent behavior, duplicate
submission refusal, and full framed host registration and ciphertext
save inside a verified marked disposable trial. Negative tests cover
malformed origin, wrong extension ID, plaintext-bearing request fields,
unsafe XDG override, missing host files, manifest tampering, symlinks,
and registration rollback. Prior vault, privacy and title-marker
contracts are also rerun.

The Node/Python CI fixtures do **not** prove live Brave UX or
the system's ability to restore a session. A real operator's consented
disposable browser test is a separate acceptance gate.

## WATCH OUT FOR

- `tabs` is a browser-wide optional permission; selecting one window
  is a **code constraint**, not a browser-enforced per-window permission.
- Origin hostnames and selected tab metadata are visible locally in
  the extension review UI and process memory. Paths, queries and
  fragments stay out of the UI but **are encrypted** if selected.
- A passphrase length minimum does not establish password strength;
  choose an independent memorable high-entropy passphrase.
- Saving can finish after the review page loses focus if native IPC
  was already submitted. A late/unknown status is not proof of failure.
  Never repeatedly click save to resolve uncertainty.
- The test data vault is under /tmp and must never be mistaken for a
  durable production backup. There is no decryption/recovery UI in
  this milestone. Losing the test passphrase or /tmp directory makes
  the snapshot unrecoverable.
- Native origin is not strongly authenticated; a same-UID program
  can bypass the extension and cause ciphertext writes within the
  limited trial. That restriction must be redesigned before creating
  a persistent production host.
- No automatic browser launches, window moves, URL deduplication,
  security credential recovery or TimeW SAVE/RESTORE authorization.

## CHECKLIST

- [x] Reconcile canonical Hospital DOC lane, PR #1836 and code ownership
- [x] Require already-granted optional tab + native permissions
- [x] User-selected current normal-window tab checklist
- [x] Separate query/fragment consent and explicit save confirmation
- [x] In-page WebCrypto passphrase encryption, no URL/plaintext host transfer
- [x] New isolated, exact-manifest disposable native receiver and vault bundle
- [x] Frame, privacy, crypto and registration rollback tests
- [ ] Exact-head CI, independent security review and operator merge decision
- [ ] Operator-approved disposable Brave live test
- [ ] Protected long-lived storage with stronger host authentication
- [ ] Authorized decrypt/import flow and duplicate prevention
- [ ] Trusted monitor mapping, multi-window restoration and acceptance

## NEXT / DECISIONS

Keep new PR draft and unmerged pending security review and operator
decision. No normal Brave, local Quickshell, real browsing sessions or
production data were altered. No live Hospital registration is claimed.
