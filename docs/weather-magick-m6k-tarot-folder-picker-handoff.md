# 🏥💜 Weather MAGICK // M6k Tarot Private Folder Picker

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Weather Station / MAGICK / DIVINATION / TAROT  
**STAFF ROLE //** DOC, external Hospital-compatible OPEN AI // CHATGPT; not verified registered in live Hospital  
**ASSIGNMENT //** Complete the operator's missing Wild Unknown artwork setup without colliding with Nurse 2's existing M6j  
**BASE //** `main` `343160031584e1cda437c5e1d3bf0f0df07b1456`, after merged PR #1382  
**SCOPE //** Additive GitHub-only folder-picker control, safe path adapter, tests and CI. No local writes, user image reads, live Quickshell restart, merge or credential action.

## IMPLEMENTATION

**The underlying reason for numbered Tarot cards was independently verified.** The repository contains identities of the 78 Wild Unknown Tarot cards but does **not** include Kim Krans's copyrighted illustrations. Before M6j the card face drew a numbered original placeholder until the operator manually entered an absolute directory with images named after the known card IDs.

While M6j work was in progress, Nurse 2 opened **PR #1382** for the same issue. That PR has now been merged, including:

- A **solid red** large-card CLOSE button with black lettering, using the existing `ActionButton` styles.
- A conspicuous **NO PHOTO** placeholder and clear message when no authorized local image is found.
- Read-only local PNG/JPG/JPEG/WebP lookup through the already-known 78 card IDs, with no network access or artwork bundling.

I did **not** open a conflicting PR from my old M6j prototype branch. Instead this M6k branch starts from the exact merged M6j `main` and adds only the missing quality-of-life control: **BROWSE** next to `LOCAL ART DIR`. The button uses the supported Qt 6 `QtQuick.Dialogs.FolderDialog`. When the user selects a folder, the small pure `Deck.localFolderPath()` helper converts an accepted `file:///` URL into the original session-only absolute path; it refuses remote locations, encoded path separators, `..` segments, malformed URL encoding, query strings and invalid paths.

That populates the existing `TextInput`, so all existing readers (drawn cards, catalog preview and inspector) use the same folder. The manual absolute-path input remains. No new file reader, photo scanner, file copying, storage, settings persistence or upload is introduced.

**Important:** This improves the selection UI, but it does not create or supply copyrighted card images. Actual Wild Unknown illustrations appear only when appropriately authorized local files exist inside the selected directory and have recognized filenames such as `major-the-fool.jpg` and `wands-daughter.png`.

## HOW TO USE

After operator-approved PR merge and a separately authorized Fedora deployment, open:

**Weather Station → MAGICK → INDEX → DIVINATION → TAROT → BROWSE**

Choose the local folder holding your personal card scans/photos. The existing local-art field populates with the selected path. Open **DRAW** or **INDEX**; images with the correct card IDs and known extensions load in place of NO PHOTO. Click a card to open the large view and confirm the **red CLOSE** button.

If the folder contains unlabelled camera photos (`IMG_0001.jpg`), they will **not** automatically match the deck. Name them using the stable IDs in the existing 78-card catalogue. No rights to distribute images are inferred from owning a physical deck.

## VERIFY

- `tests/weather/test_magick_tarot_art_folder_picker_m6k.js` verifies Qt file-URL decoding, Unicode and spaces, remote/unsafe path rejection, existing local image URL candidates, UI binding and absence of network/storage effects.
- CI reruns M6j image-state/red CLOSE, M6g identity, M6h physical selection and M6i layout regressions.
- `qmlformat` parses the affected pane on disposable GitHub Ubuntu CI. This **does not launch Quickshell** or guarantee native FolderDialog focus/z-order behavior in Fedora.
- No Tarot image file or copyrighted illustration is added; shared card component, existing local image candidates and red CLOSE remain unchanged.

## WATCH OUT FOR

The FolderDialog requires Qt's `QtQuick.Dialogs` module at runtime. This is present in supported Qt 6 builds, but the operator's installed Quickshell packaging and the popup interaction must still be tested natively. A click-initiated folder chooser may be a separate native dialog rather than a contained panel; this is expected for Qt's standard picker.

The selected folder remains **session-only**, so choosing it again after restarting Weather Station may be necessary. This honors the prior privacy decision rather than silently persisting a filesystem path.

An empty or unrecognized folder will correctly keep showing NO PHOTO. Do not treat a successful CI test as proof that card image assets exist locally.

## CHECKLIST

- [x] Recheck Syntagma, MAGICK ownership, current main and branch conflicts
- [x] Confirm Nurse 2 PR #1382 merged with red CLOSE and local image format fixes
- [x] Avoid duplicate/overlapping PR
- [x] Implement safe private folder chooser on new current-main branch
- [x] Add path/behavior tests and Qt syntax CI
- [ ] Final exact-head workflow checks
- [ ] Independent review and operator merge
- [ ] Separately authorized desktop update and native visual acceptance
- [ ] Actual private source images prepared and card filenames matched

## NEXT

After CI, let Nurse 2 independently review this separate M6k picker. Do not merge or install without operator authorization. On the actual desktop, check that BROWSE opens, the chosen private folder populates the input, a matching `major-the-fool.jpg` displays in INDEX/DRAW/INSPECT and CLOSE remains red. If native popup containment is troublesome under Quickshell, keep the existing manual path field as a reliable fallback; any custom embedded file browser should be separately designed.

## DECISIONS

No second Tarot provider, asset redistribution, wholesale Visual V3 work, live desktop action, automatic merge or change to the merged M6j owner. M6k is a small follow-up to the user's visual complaint, not a claim that the actual deck images have already been installed.
