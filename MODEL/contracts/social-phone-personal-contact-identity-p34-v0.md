# Social PHONE // P34 contact identity and local favorite/notes policy

> **STATUS:** GitHub-only draft. Pure policy + synthetic tests. **Not** a usable encrypted contact store or enabled PHONE UI. No local Fedora changes, production activation, or registered live Hospital session.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
> **ASSIGNMENT:** establish a safe local Personal contact metadata identity boundary, preceding persistent Favorites/Notes.
> **ROLE:** External Hospital-compatible ordinary DOC; explicit live Staff/Room/Assignment/session identity not verified.
> **NEIGHBORS:** Existing Favorites++ owner and Contacts/BlueFerry host-read owners remain independent. No shared Favorites store, Notes store, protected Syntagma policies or phone-provider IPC changed.

## IMPLEMENTATION

BlueFerry 0.9.1 contacts use ephemeral `legacy-row-N` with a fresh read epoch, not durable identifiers. PR #1851 restores complete **currently loaded** legacy phone/email arrays but cannot make those IDs persistent. Existing AppControl/Favorites++ stores and ApolloHub Notes use local JSON, not a secure Personal contact vault, and therefore must not receive contact notes or raw addresses by accident.

`PhonePersonalContactIdentity.py` is a **pure, dormant policy** and provides:

1. **Candidate matching:** caller provides a current `contacts.read` card, the entire current bounded contact snapshot, a verified phone profile UUID, and at least 32-byte host-owned secret. Policy accepts **only** an exact-profile BlueFerry card with `hasAddressDetails === true`, nonempty normalized name, and complete well-formed phone/email arrays; no name-only or counts-only matching. Exact sorted address set and normalized name, plus profile, are HMAC-SHA256'd under the host secret. No provider contact ID, raw name or phone/email value enters persistent identifiers.
2. **Ambiguity is denial:** if the same match candidate occurs more than once in the currently loaded page, linkage is rejected. Missing cards, malformed addresses, unsupported telephone extensions, duplicate addresses and 100+ snapshot overflows fail closed. A successful match is **not** proof of a real human; source uniqueness is only within the current page, so duplicate people outside the first page remain a limitation.
3. **Explicit link:** `link(... user_confirmed=True)` allocates a new independent random UUID for a local Personal record and stores only profile-scoped HMAC match proof, favorite boolean, and note in an **in-memory returned document**. No saved note is revealed by `resolve`; it reports only match status and local ID. The host must independently verify current approval, identity, ownership, and secure write authority.
4. **Revisioned edits/deletion:** `edit(... user_confirmed=True)` accepts bounded favorite/note changes only with an exact document revision. `unlink(... user_confirmed=True)` deletes the entire local record, including the note and favorite, from the resulting document. No modification writes anything to disk. Invalid documents, replays, duplicate local IDs and conflicting proofs are denied.
5. **Isolation:** no Quickshell, shell subprocess, D-Bus, networking, SQL, file I/O, keyring, iPhone edit, SMS send or call-control behavior. Existing PHONE UI is **unchanged** by P34.

## WATCH OUT FOR

- This is **a candidate, not a stable person ID**. Phone number reassignment, reused names, merges/splits of iPhone contacts, rename, or changed address sets can invalidate or misassociate a proof. A future host must display provenance and support explicit **relink**, pause when uncertain, and avoid automatic disclosure of private notes. Never treat the proof as trusted authentication.
- **Do not serialize** the returned document directly to AppControl Favorites, FavoritesDefaultStore, ApolloHub Notes or any plaintext JSON. The `note` field is sensitive. A follow-up host must supply actual authenticated encrypted at-rest persistence, key handling/unlock/rotation, atomic revision-checked writes, explicit deletion, and revoke/identity-switch invalidation.
- The secret must be generated and maintained **outside** the policy in an approved protected store and remain stable across restarts if the user wants saved metadata to reassociate. Rotating/loss of the secret makes old candidate bindings unmatched, requiring explicit recovery/relink.
- The current local remembered Personal preference is **not cryptographically app-authenticated**. A future vault must not take a QML-supplied `user_confirmed=True` flag as evidence of consent. That is a pure policy input for a trusted host to use only after verifying an actual approved interaction.
- BlueFerry currently exposes only the **first up to 100 contacts** in the legacy read path. Candidate uniqueness is scoped to these loaded rows, not the entire iPhone contact book.
- Contact note body exists **only in memory** as a proposed output while vault storage is absent. This PR is not advertised as durable Favorites or Notes; it does not expose an editable note field or active favorite star.
- Favorites++ remains owner of its own neutral-resource collections. Post Apollo Personal contact notes must not be copied into its existing unencrypted stores or an automatically serializable resource key.

## VERIFY

`tests/phone/test_phone_personal_contact_identity.py` uses invented sample contacts only and asserts:
- match candidates independent of ephemeral daemon epoch and list order;
- different profile, secret, name, address set produce different proofs;
- counts-only/no-address, duplicate candidates, invalid email/phone and malformed source fail closed;
- explicit link, randomized local ID and no raw contact info in stored match metadata;
- no note content in normal `resolve` output;
- user-confirmed revisioned favorite/note edits, no optimistic overwrite, explicit deletion and no mutation of the input document;
- no file I/O, contact read, provider, network, keyring, FaceTime, SMS or call activity.

Exact-head GitHub CI and operator acceptance are separate gates.

## HOW TO USE

No live UI change yet. Future work supplies a **trusted, encrypted Personal contact metadata host** and explicit UI controls which request current `contacts.read` authority, obtain a unique candidate, ask the user to **link** the contact, and only then permit local favorite and note updates with visible save confirmation. Nothing syncs to the iPhone.

## NEXT

1. Review and accept the P34 policy and its CI without merging protected Favorites/Notes providers.
2. Define and implement a dedicated **encrypted** local Personal contact vault with authenticated identity/scope binding, stable secret, keyring handling, revisioned atomic writes, and metadata-free public errors. Do not borrow unencrypted generic favorites storage.
3. Expose the UI favorite star and notes editor only when protected vault availability and explicit opt-in can be verified. Add user-visible *unlink/delete* and accurate “local only” wording.
4. Verify with an approved Fedora deployment, a bounded real-phone snapshot, re-read/restart/revoke and two duplicate-name/number cases; final acceptance belongs to the operator.

## DECISIONS

Separate private Personal contact data from Favorites++. Refuse unambiguous-looking IDs derived from row numbers or from unsalted phone/address hashes. Do not declare an HMAC a verified person identity. Build a small, reviewable **matching and revision-policy** foundation before implementing persistence and the UI.
