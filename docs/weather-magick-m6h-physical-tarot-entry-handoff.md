# 🏥💜 Hospital // MAGICK M6h Physical Wild Unknown Card Entry

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / bounded MAGICK Tarot enhancement
ASSIGNMENT // M6h optional manual transcription of cards physically drawn by the operator
STAFF ROLE // Nurse 2, external Hospital-compatible
PROVIDER // OPEN AI / CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE; no live registration claimed
PHASE // Isolated GitHub draft pending CI, review, merge and native acceptance
BRANCH // feat/weather-magick-m6h-physical-card-entry-20261106
RECOVERY // M6g PR #1373 merged on GitHub at 8b0e4976a5c8a5b614f48b30f38d41e0df5fe321. Main already contains the 78-card Wild Unknown identity catalogue and M6g symbol-only draw, but not verified installed/accepted on the Fedora desktop.

## IMPLEMENTATION

Operator asked to continue after approving the Wild Unknown physical deck as preferred MAGICK Tarot identity. Current GitHub M6g merge, file ownership and concurrent MAGICK/Weather open PR searches were verified (no matching open PRs at branch creation). Rechecked Syntagma AGENTS.md, Hospital agent/ownership protocol, the existing Tarot deck policy, card rendering, routes, source tests, and CI. The scope is one feature that makes the operator's actual physical cards useful in the current on-screen Tarot workspace. No existing menu ownership or data source changes.

- Adds `widgets/weather/StationMagickTarotPhysicalPolicy.js`, a deterministic, pure **physical spread transcription** state machine. Reuses the existing 78-card IDs, Wild Unknown Daughter/Son/Mother/Father names and EXACT one/three/five position labels from M6g instead of copying or inventing another deck. A new physical spread starts empty and records only cards the operator selects.
- Every manual choice is explicit: selected card ID, specified UPRIGHT or REVERSED orientation, and next unfilled position. Prevents duplicate card IDs and advancing beyond a completed spread. Invalid card IDs, orientation, slot or source state fail closed. All state transitions allocate new arrays/objects, preserving the source catalogue and previous reading state. UNDO LAST removes only the most recently entered card; CLEAR resets to an empty source-verified spread.
- `widgets/weather/StationMagickTarotPane.qml` preserves existing **DIGITAL SHUFFLE** and its original Fisher-Yates pseudo-random source, while adding **MY PHYSICAL CARDS** mode. Physical CHOOSE CARD navigates to the existing full INDEX; the user selects a specific preview row, sets UPRIGHT/REVERSED for that card and presses ADD TO SPREAD. The next position is named. On completing the spread the UI returns to DRAW, where the actual selected card faces/placements are displayed. Duplicate cards are disabled from adding in the picker. Switching methods or spreads resets the current in-memory state explicitly; no data write, upload, external request or card scanner.
- Retains the optional source-controlled local artwork directory feature added by M6g, original Post-Apollo placeholder art and existing TAROT route. No Kim Krans illustrations or guidebook interpretations are added to GitHub. The manually selected physical card IDs can show authorized local PNGs when present, and otherwise use the original artwork.
- No journal/reading history saved. No new local credentials, browser, camera, random-number actor, file writer, timer, permission changes, scientific claim, magical efficacy claim or local desktop mutation.

## HOW TO USE

After operator-authorized merge and separately approved Fedora Quickshell installation:

1. Weather Station > MAGICK > INDEX > DIVINATION > TAROT.
2. Choose ONE, THREE, or FIVE spread, then **MY PHYSICAL CARDS**.
3. Shuffle and draw cards **physically from the Wild Unknown deck you own**; choose CHOOSE CARD in the GUI, browse INDEX by major/suit and page, and click the matching card name to preview it.
4. Choose UPRIGHT or REVERSED to mirror how your actual card is lying and click ADD TO SPREAD. Repeat for each explicitly named position. The GUI refuses the same physical card ID twice and returns to the visible spread when complete.
5. Choose UNDO LAST if you entered the wrong card, or CLEAR to discard the in-memory spread. DIGITAL SHUFFLE uses the original pseudorandom digital deck, unchanged.

This is transcription of the user's own physical deck choices, not a simulation of physically manipulating cards, and not a journal.

## VERIFY

- New `tests/weather/test_magick_tarot_physical_m6h.js` tests source-backed one/three/five spread positions, full five-card completion without replacement, manually controlled reversals, immutable state, duplicate/unknown/invalid ID refusal, input slot tamper rejection, undo/clear transitions, QML picker and original digital draw coexistence, lack of data/service actors and untouched route.
- Adjusted only the stale M6g button-label assertion: it now verifies that digital mode still shows SHUFFLE + DRAW when physical mode shows CHOOSE CARD. All other existing M6g tests preserved.
- The Weather COSMOS JPL/MAGICK workflow now runs M6h tests alongside previous M6g, M6f, M4/M5 and V4–V5/weather regressions.
- Exact GitHub CI status must be verified on the head commit before claiming pass. Native Qt compact card layout, click-to-preview, upright/reversed and actual user art still require desktop testing and operator final acceptance.

## WATCH OUT FOR

M6h does not automatically capture physical cards. The operator types/selects card identities, and no camera/files are collected. The local artwork feature remains subject to artwork-rights considerations; physical deck ownership does not grant permission for redistribution of illustrations or guidebook text. The original placeholder works without asset imports. Manual entry stays in QML memory only and is lost when closing/reloading the relevant component. Switching spread or draw method clears the current spread rather than silently transferring it.

Cards are symbolic and interpretations should not be represented as scientific facts or predictive guarantees. Existing M6g three- and five-card presentation may be tall on a compact panel: automated source tests do NOT prove native fitting or mouse hit-target accuracy, so visually review before accepting. No local Fedora edits, Quickshell restart, merge, production activation or live Hospital connection was performed.

## CHECKLIST

- [x] M6g merged state and concurrent PR search verified
- [x] Read canonical Syntagma/Hospital rules and actual M6g source
- [x] Manual physical spread state policy with no duplicates, new immutable entries and undo
- [x] Connect physical selection through existing 78-card index, preserving digital mode
- [x] M6h tests plus M6g compatibility test and workflow integration
- [ ] Exact PR head CI pass, mergeability and current branch comparison
- [ ] Operator-authorized merge and separate local deployment
- [ ] Native compact UI/card selection/reversal and final operator acceptance

## NEXT

Verify all exact-head GitHub tests and repair regressions, then leave a draft PR for operator approval. After authorized installation, try one real Wild Unknown deck three-card spread: match card titles, reverse one, reject a duplicate, undo and replace it, and verify the correct display and privacy boundary. The next independent assignment may focus on compact readable five-card spread layout or a rights-cleared original interpretation/reference system. Personal tarot journals and distributed artist artwork remain outside M6h and require separate authorization/rights.

## DECISIONS

Physical-deck transcription is optional and complements, rather than replaces, the M6g pseudorandom digital deal. Keep stable Wild Unknown card identities, independent original Post-Apollo fallback graphics, no copyrighted art bundled, no storage, no new application service, and the current accepted functional V5 design. Global Visual V3 is deferred.
