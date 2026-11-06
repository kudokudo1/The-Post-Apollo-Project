# 🏥💜 Weather MAGICK // M6j Tarot Personal Artwork and Red Inspector Close

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Weather Station / MAGICK / DIVINATION / TAROT  
**STAFF ROLE //** DOC, external Hospital-compatible, provider OPEN AI // CHATGPT; no live Hospital registration verified  
**ASSIGNMENT //** Fix unavailable Wild Unknown card images and make large-card CLOSE button visibly red  
**BASE //** GitHub main `f8d02b5df10aac877a42d67cc5820121883d0cb7` at November 6, 2026 preflight  
**SCOPE //** Bounded GitHub source/tests/CI/docs; no live Fedora workstation changes, Quickshell restarts, auto-merge, actual copyrighted artwork bundling, or user filesystem reads.

## IMPLEMENTATION

### Verified cause of numeric placeholders

The existing `StationMagickTarotDeckPolicy.js` already defines all **78 Wild Unknown Tarot card identities**, but the GitHub repository contains **no card illustration assets**. `StationMagickTarotCard.qml` deliberately paints a Post-Apollo decorative glyph containing a card number while `Image.source` remains empty or fails to load. Before M6j the only path to a real face was entering an **absolute local directory** manually, with exactly named `<card-id>.png` files. Nothing downloaded or bundled the deck images. A physical copy of the deck does not automatically install digital images or grant redistribution rights.

### M6j changes

- **Easy folder selection:** TAROT's `LOCAL ART DIR` row now includes a **BROWSE** button opening the standard Qt 6 `QtQuick.Dialogs.FolderDialog`. The selection is converted from a `file:///` URL to a validated absolute local path. The old manual text input stays available. The path is session-only; there is no background scan, upload, copy, settings persistence, new network source or file write.
- **More image formats:** Each rendered card now tries the known card key with `.png`, `.jpg`, `.jpeg`, then `.webp`, in order. If one format cannot be loaded, `Image.Error` advances to the next candidate. A successful face uses Qt `Image.PreserveAspectFit`, never stretching the scan. Drawn cards, index previews and the large-card inspector all already share `StationMagickTarotCard`, so the same source resolution applies across all three.
- **Truthful artwork status:** A card with no selected folder displays `NO LOCAL ART FOLDER`, and one whose specified files cannot be loaded displays `IMAGE MISSING // CHECK FOLDER`. The draw and inspect views explain that images are not installed. Numbered Post-Apollo fallback graphics remain as a safe fallback until **actual authorized local images** exist.
- **Red large-card CLOSE:** In `tarotCardInspector`, only the existing `ActionButton` labeled `CLOSE` gains red fill/border/accent and dark label in idle, hover and pressed states. It continues to set `inspectedDrawIndex=-1` and close the overlay. Other actions and their semantics remain unchanged.

**Exact example:** A personal image named `major-the-fool.jpg` (or `.png`, `.jpeg`, `.webp`) in a private chosen folder will display on The Fool card. `wands-daughter.png` displays on Daughter of Wands. Filenames must match the established card keys; this milestone does not guess unnamed camera roll photos or scan directories automatically.

## HOW TO USE

After approved merge and a **separately authorized desktop update**, open:

**Weather Station → MAGICK → INDEX → DIVINATION → TAROT → BROWSE**

Choose your private folder containing authorized images of your physical tarot deck. Alternatively enter its absolute path into `LOCAL ART DIR`. Use **INDEX** to preview matching images, or **DRAW → SHUFFLE + DRAW** to use them in a spread. Click a card for the large inspector; its **CLOSE** control is red.

No user scans or licensed artwork have been provided to this GitHub worker, so the PR itself cannot make the actual Kim Krans illustrations appear. The user's scans must first exist at the selected path and carry known card-key filenames. Existing artwork rights remain with their owner. Do not download and redistribute arbitrary Internet copies.

## VERIFY

- GitHub CI runs M6j safe local URL/path/extension/large close tests and prior M6g (78-card identity and no copyrighted bundling), M6h (physical entry), M6i (responsive cards/inspector) regressions.
- Qt 6 `qmlformat` parses the changed QML files on disposable CI; no actual Quickshell graphics window is opened there.
- Same card component and folder property propagate to draw, index and inspector.
- Selecting, canceling or typing an artwork path never sends a network request or writes/copies artwork.
- Manual folder input remains session-only; empty or unsafe paths resolve to no image source.
- The inspector CLOSE still returns to the existing spread and is visibly red in the default action state.

## WATCH OUT FOR

This fixes the **configuration and loading path**, not the absent image files. Showing the original Wild Unknown images requires privately supplied images stored on the user's machine with matching names. A folder containing only anonymous scan filenames such as `IMG_0001.JPG` will not match; the existing card IDs must be used.

Native `FolderDialog` interaction and image decode support depend on the operator's installed Qt/Quickshell setup. CI syntax and JS tests do **not** verify actual local photo loading, panel z-order, focus behavior or visual red rendering. Those need native observation after deployment. A chosen path is user-visible in the text box, not persisted.

No change to COSMOS astronomy, other MAGICK subjects, tarot draws, privacy policy, readings, physical-card history, real TASKS work, protected Connections integration or live operating-system settings.

## CHECKLIST

- [x] Inspect Syntagma protocols, current GitHub HEAD, other PR ownership and existing M6g/M6h/M6i implementation
- [x] Verify no Wild Unknown artwork assets exist in repo and confirm original number fallback cause
- [x] Add private folder picker and safe `file:///` conversion
- [x] Add alternate local artwork formats to the shared card view
- [x] Make large inspector CLOSE button red across interaction states
- [x] Add regression tests, syntax CI and Hospital handoff
- [ ] Final-head CI, independent review and operator merge decision
- [ ] Separately approved local code deployment and native acceptance
- [ ] User's real private artwork files supplied/named and image-load verification

## NEXT

1. Review/merge M6j after CI and independent approval.
2. Once the user has privately saved scans/photos of the owned deck, prepare or rename the image filenames to match the stable card IDs and choose the folder in TAROT.
3. Native-verify a PNG and a JPG in DRAW/INDEX/INSPECT, absent-file status, reversed photo orientation and red CLOSE at current Weather Station panel geometry.
4. Only if needed, separately authorize a private, read-only card-to-image mapping UI to handle camera default filenames without renaming. Do not silently scan the home directory.

## DECISIONS

Preserve copyright boundaries and the user's control of private assets. No bundled copyrighted illustrations, no fake substitute identified as official art, no always-on directory discovery, no credential or network dependency, no local machine changes, no automatic PR merge or full Weather Visual V3 refactor. Technical CI success is not visual operator acceptance.
