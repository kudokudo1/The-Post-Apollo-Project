# Social PHONE // P40 Locked Favorites and Notes Contact UI

**Patient:** \`kudokudo1/The-Post-Apollo-Project\`. **Staff/role:** external Hospital-compatible ordinary DOC, PHONE contact-detail presentation only. **Room / Assignment / Session:** no live Hospital registration verified. **Checkpoint:** P39 PR #1907 merged before P40; P38 signed-format comparison and P37-P39 protected trust boundaries remain unchanged. **Operator authority:** GitHub-only implementation by the worker, merge and any local Fedora/Quickshell changes separate.

## IMPLEMENTATION

Existing \`PhoneContactDetail.qml\` is the same CONTACTS detail card shown when a user selects an authorized iPhone contact. P40 adds **visible but disabled** personal metadata surfaces without pretending the encrypted P35 vault has a live verified PHONE host:

- The existing \`IPHONE CONTACT // PERSONAL // READ ONLY\` header becomes a single header row with **EDIT** in the upper-right corner, visibly unavailable. No local or iPhone contact editor is wired.
- The CONTACT ACTIONS row includes **CALL, MESSAGE, FACETIME, EMAIL**, retaining the original CALL/MESSAGE behavior. FACETIME stays unavailable because Linux BlueFerry HFP has no FaceTime transport; EMAIL is explicitly unavailable pending a verified provider route and human action.
- **PERSONAL // FAVORITE** shows a magenta ☆ FAVORITE control and "NOT SAVED // UNAVAILABLE." The control cannot toggle itself, cache a tentative selection, allocate a contact ID, or claim the person is a favorite.
- **PERSONAL // NOTES** contains a fixed, non-editable explanatory placeholder, plus disabled **EDIT NOTE** (magenta) and **DELETE NOTE** (red, destructive) controls. No note is fetched, buffered, edited, deleted, displayed from an unapproved source, or written anywhere. There is no false saved confirmation or optimistic local draft.
- Both metadata areas show \`UNAVAILABLE // VERIFIED CONTACT SAVE HOST REQUIRED\`. The QML-facing \`personalMetadataWritable\` property is **read-only and hard false**. A local Personal read preference cannot make it writable. The card remains guarded by the existing selected-contact/approved-snapshot conditions in \`PhonePane.qml\`.
- All phone-number fields, individual MAKE CALL buttons, call-review/confirm, existing MESSAGE navigation, four-line list, A-Z headings, search and star scrollbar remain unchanged. The global Favorites++ and Notes stores, P34-P39 security modules and other workers' files remain untouched.

## HOW TO USE

After operator review, merge and separately authorized local desktop deployment, open Social → PHONE → CONTACTS → select a currently loaded, authorized contact. Observe Favorite and Notes sections, with visibly inactive controls and a plain-text explanation of why writes are unavailable. CALL and MESSAGE retain their existing restricted behavior. The EMAIL, FACETIME and EDIT controls are not active.

This release **does not** allow marking a favorite, typing a new note, deleting a note, editing contact fields, writing iPhone contacts or sending email. That requires a real independently verified per-action vault host, not a cosmetic button.

## VERIFY

- \`tests/messaging/test_social_phone_contact_metadata_locked_p40.py\` checks header/edit positioning, four contact actions, visual color semantics, magenta Favorite star and red destructive delete control, explicit unavailable copy, and absence of write-enabled signal handlers or editable notes.
- Existing contact selection/permission guard test and protected PHONE read-only UI tests remain routed through \`.github/workflows/social-phone-one-action-setup.yml\`.
- Exact PR-head CI and installed Quickshell visual behavior are separate verification gates. No local host access, real iPhone record or private note is used in these tests.

## WATCH OUT FOR

- **No note is actually locked in a running keyring by P40.** "Unavailable" means there is no authenticated PHONE save/read interface. Do not infer the existence of an accessible saved note from this placeholder.
- P34 contact IDs remain ephemeral BlueFerry row IDs, while local P34 matching uses only conservative, profile-scoped candidate HMACs. Never use an ephemeral row as a permanent favorite or notes key.
- The P35 encrypted vault and P36 synthetic keyring fixture are not currently authorized for production QML access. P37-P39 cryptographic receipts are signed synthetic evidence, not actual installed host or C5 human approval. The dependency issue [#1885](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1885) still tracks these unverified producer authorities.
- All new buttons are disabled. Their appearance is preparation for future functional actions, not a silent implementation of a save protocol. The UI's local hard-false property must not be relaxed simply because tests pass.
- Native Fedora screenshots/keyboard traversal and narrow-panel wrapping still need operator-approved installed-host verification; source tests alone do not prove native appearance.

## CHECKLIST

- [x] Verify P39 merge, scope, and PHONE UI owner boundaries.
- [x] Add disabled header EDIT; preserve existing CALL/MESSAGE.
- [x] Add EMAIL placeholder to the four-action row.
- [x] Add magenta Favorite star with explicit unavailable state, no toggle.
- [x] Add non-editable Notes placeholder with magenta EDIT NOTE and red DELETE NOTE, no false save.
- [x] Add UI tests and existing PHONE CI entry.
- [ ] Inspect exact-head CI and merge review.
- [ ] Explicit local host deployment approval and visual acceptance.
- [ ] C3e/C4b/Identity installed-host evidence, C5 human receipt and PHONE key lifecycle accepted.
- [ ] Implement actually authenticated one-action Favorite/Notes read/save/delete and user-visible save feedback.
- [ ] Then implement read/write-scoped contact editor, multiple custom labels and the separate blocking UX.

## NEXT

**P41:** Build the protected PHONE contact-metadata interface only after the P39 dependency owners provide real authenticated installed-host and C5 consent sources: one-use authority binding selected stable local record, current profile/session and exact change through P35's revision-locked encrypted commit. Implement live read/unlock/revoked/locked/error/saved states behind this contact detail UI. If the external authority is still incomplete, continue safe, bounded presentation/field-layout work, not simulated persistent favorites or notes.

## DECISIONS

Do not import generic Favorites++, ApolloHub Notes or unencrypted JSON storage. No real notes or favorites in QML. No user machine changes, keyring creation, SMS, FaceTime, email, contact edit or production activation. No Hospital live attachment claimed; operator decides merge and installed acceptance separately.
