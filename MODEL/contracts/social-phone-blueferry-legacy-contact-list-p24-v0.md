# Social PHONE P24 // BlueFerry 0.9.1 legacy cached contact-list compatibility

> **STATE:** Draft GitHub-only provider compatibility change. No local Fedora writes, pairing/audio/calling modifications, daemon restart, merge or production activation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **ROOM / ASSIGNMENT:** Social PHONE contacts.read / BlueFerry cached phonebook compatibility, P24. **PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible developer (no verified live Room, Staff Role, Assignment or registered Session). **BASE:** freshly checked `main` `30a11bf7ca75dc0d713bf059b52b6bfa19fb3440`, 2026-11-08, no open overlapping PHONE/Social/Identity PR at preflight.

## IMPLEMENTATION

The user's *actual Fedora* diagnostic confirmed:
- BlueFerry **0.9.1** is installed, storage **ready**, PBAP **true**, and `blueferry contacts-sync` returned **141 cached destinations**.
- `BackendClient.contact_cards` is **MISSING**, `BackendClient.list_contacts` is **AVAILABLE** and the user successfully fetched one legacy record with `list_contacts(offset=0, limit=1)`.
- `GetStatus` has no `contact_card_count` or `contact_card_epoch`. PHONE's current P18c `_status_ok` rejects `contacts.read` before trying the provider, so Social reports **READ FAILED** even though the legacy cached phonebook can be read.

Upstream BlueFerry `ListContacts(uu)` returns a bounded **JSON list of records** `{"name": string, "phones": [strings], "emails": [strings]}` with addresses grouped by person. Unlike `ListContactCards(uus)`, it provides **no persistent card ID**, photo support, total-count or provider epoch. The existing `BackendClient.list_contacts` uses precisely that D-Bus method; the user's local test proved it works.

P24 changes only the **phone provider read/normalization seam**:

1. `BlueFerryHostReadPort.py` supports the old `ListContacts(uu)` read under the **same unique-owner pinned D-Bus connection** and existing 256-KiB response cap, with at most `MAX_CARDS=100` returned records in this first page. A new `_contact_mode` selects modern card mode when *both* modern metadata fields are valid. It selects legacy mode **only when both fields are absent** and PBAP is active. Invalid, partial, negative or malformed modern metadata is **not** a fallback trigger. No fallback occurs merely because a modern provider read failed.
2. The host still checks exact active phone profile, PBAP capability, active unique daemon owner, and caller-supplied read-only host guard before and after the read. If mode switches, provider owner changes, device profile changes or PBAP drops during the read, the data is discarded. The existing release callback remains the sole content path; the provider response itself contains no personal data.
3. `BlueFerrySocialProjection.py` adds a *pure* `normalize_legacy_contact_page`. It validates record names and bounded phone/email arrays, uses the first validated phone or email for display, and produces the **existing Social contact-card view shape** (name, primary, phone/email counts, `hasPhoto:false`). It never fabricates a real native card ID, photo, chat conversation, routing permission, verified person, phone line, organization membership or send privilege.
4. Each legacy read gets a new `secrets.token_hex(16)` ephemeral read epoch. Synthetic `legacy-row-N` IDs exist **only in that snapshot**, change on refresh, and are not usable as stable native contact references. The result has `legacyReadOnly: true` and `historyPartial: true` when the 100-record limit is hit. The legacy result `total` is explicitly the *returned page count*, never a claim about the full iPhone phonebook or the **141 destinations** (destinations may include multiple numbers/emails per person).

No QML label, Contacts sidebar, chat feed, saved Personal permission flow, wallet implementation, Bluetooth audio, FaceTime or oFono/HFP code is touched. Future fully paged Contacts directory and contact-detail/call/send actions are **separate assignments** requiring provider and UI authority.

## HOW TO USE

After operator review, merge and **separately authorized Fedora update**, open **Social → PHONE → CONTACTS** with the previously remembered `contacts.read` Personal consent, while BlueFerry storage is **READY**. Press **REFRESH** if needed. BlueFerry 0.9.1's cached phonebook should provide the first bounded page of contact records to the existing Social CONTACTS tab without requiring modern contact-card fields.

Do **not** re-pair the phone, clear history, repeat contacts-sync unnecessarily or downgrade storage. The already working Messages sidebar remains labeled **Contacts** and contains people with conversation history; the full CONTACTS tab is a different view.

## VERIFY

- `tests/phone/test_blueferry_legacy_contacts.py` uses invented names, numbers and emails only. It verifies the actual `ListContacts(uu)` method, owner-bound transport, JSON-string subclass handling, 256-KiB bound, modern vs legacy mode dispatch, per-read ephemeral IDs, 100-card page bound, privacy-safe error handling, malformed record rejection, host denial, provider owner/profile/PBAP/mode switches and no private data in public responses.
- Existing P18a normalization and P18c modern card tests remain unchanged. PHONE workflow includes the new test file in compilation/runners and PR/path triggers.
- **Not verified:** real updated Fedora deployment, complete legacy phonebook cardinality, visual UI behavior, full contact details, identities or app-isolated production permission. Actual desktop result still needs user acceptance.

## WATCH OUT FOR

This is a bounded **first-page** view. `MAX_CARDS=100` is the existing Social/BlueFerry projection limit, so even a successful legacy read may not include all 141 cached *destinations* or more than 100 distinct people. Do **not** claim the total is complete. A separate paginated directory design is needed if additional records exist.

The public snapshot IDs are ephemeral and **must not** be stored, used as recipients, used for dialing, or merged with other organizational contact stores. BlueFerry's same-UID D-Bus and P21 locally remembered Personal consent remain **not** cryptographic app/session-specific grants. The existing P18c host_guard/host_release callbacks are not actual authentication.

If the installed D-Bus daemon rejects `ListContacts` even though the user's local client was able to read it, or the returned fields differ from upstream, this patch will still fail closed. Do not print raw contacts, addresses, profile UUIDs, D-Bus payloads or private error strings to diagnose that.

## CHECKLIST

- [x] Inspect operator's *real* BlueFerry 0.9.1, `contact_cards: MISSING` / `list_contacts: AVAILABLE` / `Legacy contact read: WORKING` evidence.
- [x] Recheck current GitHub HEAD, overlap/ownership, Syntagma AGENTS and Hospital/working protocols.
- [x] Compare upstream D-Bus `ListContacts` and `ListContactCards` to current Social source/adapter contracts.
- [x] Implement strict legacy-only-if-metadata-absent fallback and ephemeral read-only card projection.
- [x] Add synthetic adapter/transport/security regressions and PHONE workflow routing.
- [ ] Exact-head GitHub CI.
- [ ] Operator PR approval/merge and separately approved Fedora update.
- [ ] Live BlueFerry 0.9.1 Contacts tab and real-person record display, no leakage on revoke/identity change.
- [ ] Pagination/full contacts and profile detail actions under separate scope.
- [ ] Production Identity Center/Account Broker authenticated provider host under assigned owners.

## NEXT

Run exact-head CI. After authorized merge and desktop update, verify Social CONTACTS loads a non-empty **read-only** contact page while BlueFerry storage is READY and the Personal `contacts.read` preference is approved. Confirm the Messages sidebar/working audio remain unchanged. If only 100 people are returned while BlueFerry has more records, implement a separately designed and tested paginated full-directory view. If read still fails, capture metadata-only diagnostics of the installed provider D-Bus method and safely rejected shape, not actual address book content.

## DECISIONS

The ongoing operator instruction to resolve real PHONE integration permits a bounded **GitHub draft PR** for this confirmed compatibility gap, but not local desktop mutation, service activation, merge or re-pairing. No verified live Hospital registration. Operator retains final acceptance. Roll back by closing the PR or reverting its bounded commit if merged. Preserve the exact branch head, CI outcome and unresolved pagination/device testing in this document.
