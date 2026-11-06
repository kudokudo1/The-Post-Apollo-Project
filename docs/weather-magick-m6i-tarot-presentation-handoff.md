# 🏥💜 Hospital // Weather MAGICK M6i Tarot Presentation

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / Tarot presentation continuity
ASSIGNMENT // M6i responsive Wild Unknown Tarot spread, large inspection view and explicit physical-card index
STAFF ROLE // Nurse 2, external Hospital-compatible
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL; live Hospital registration/Room attachment not verified
PHASE // Isolated GitHub draft, verification pending, native operator acceptance separate
BRANCH // feat/weather-magick-m6i-tarot-presentation-20261106
RECOVERY // M6h physical-card entry PR #1377 merged at 5957fc778a38ed4e71820cb9565a7932e55a7265; follow-up test repair #1378 merged at adad76c046e78342c42f322bb9546728a580ca19; no open competing MAGICK/Weather PRs returned at M6i preflight.

## IMPLEMENTATION

The operator supplied two native screenshot captures of Weather Station > MAGICK > TAROT. One shows the three-card DIGITAL SHUFFLE with small card faces and unused blank space; the second shows MY PHYSICAL CARDS > INDEX where preview and selected card cues are ambiguous. The user explicitly said "continue" after accepting this bounded presentation target. Re-read canonical Syntagma AGENTS, Hospital Agent Protocol and Authority/Permissions, verified both prior merge commits, current GitHub main code and no active MAGICK/Weather overlap. No live Fedora state was touched.

**Functional boundaries:** M6i changes the presentation only. Reuse the existing M6g 78-card Wild Unknown IDs, Daughter/Son/Mother/Father courts, Fisher–Yates pseudorandom deck draw, M6h immutable physical card transcription, optional explicitly entered private-local artwork URLs and unchanged TAROT route. Do not modify draw randomness, interpretive meanings, persistent journal, user local files, private images, or other Weather modes.

- New pure `widgets/weather/StationMagickTarotLayoutPolicy.js`: viewport-bound single/three/five spread geometry. A single card is centered and receives most of the vertical allocation. Three cards use one balanced row at proper card-face proportions instead of fixed 175px height. Five cards use three-plus-two rows with bounded heights and an explicit gap rather than five miniature thumbnails. The same function handles resized panel widths and heights. A matching index policy scales the catalogue's live card preview and page row count; the full 78-source catalogue stays intact.
- `StationMagickTarotPane.qml` now binds these measurements into its existing Flow and INDEX layouts. Clicking any dealt digital or manually entered card opens a full-size read-only **CARD // INSPECT** overlay with its source card title, actual spread position, upright/reversed orientation and the existing original / authorized local artwork. Previous/next navigation and CLOSE return to the unchanged spread. Inspector state resets on a new deal or mode change, so no stale card is displayed.
- Physical INDEX now distinguishes the first catalogue card's **default preview** from a deliberate **row-selected card**: the default preview does not highlight as selected or authorize ADD TO SPREAD. Only an explicitly clicked valid row can be added, still using M6h's existing no-duplicate guard. Each successful physical entry clears the row-selection state, requiring a fresh click for the next position.
- `StationMagickTarotCard.qml` increases readability of card position/name/orientation labels and enlarges the original Post-Apollo geometric focal glyph. No Wild Unknown illustrations or guidebook text are included; existing local-only artwork source remains read-only.
- The source changes are limited to the Tarot layout policy, TarotPane/Card QML, M6i tests and source-bound M6g/M6h tests/CI. There is no new provider, process, timer, external browser, file writer, network actor or global MAGICK navigation change.

## HOW TO USE

After authorized merge and **separately approved Fedora/Quickshell installation**:

Weather Station > MAGICK > INDEX > DIVINATION > TAROT.

In DIGITAL SHUFFLE mode, choose SINGLE/THREE/FIVE and SHUFFLE + DRAW. Click a dealt card to open its larger inspector, navigate ◀ CARD or CARD ▶ and select CLOSE to return. Existing reversals and read-only optional local PNGs remain.

In MY PHYSICAL CARDS mode, choose your spread, press CHOOSE CARD to open INDEX, click the actual card's row (the default preview is not a committed selection), set UPRIGHT/REVERSED and click ADD TO SPREAD. Repeat for the next slot, deliberately selecting each card. When complete, the draw view shows the real transcribed spread; click any card to inspect. UNDO LAST and CLEAR remain in-memory only.

No written or external history is created. Local art folder is not scanned, copied, uploaded or saved.

## VERIFY

- New `tests/weather/test_magick_tarot_presentation_m6i.js` exercises responsive single/three/five geometry at multiple widths and heights, bounded card counts and two-row fit, catalogue preview/paging responsiveness, inspector real-card bounds, explicit physical selection and source-preserving QML controls. It also checks no new network/storage/process side effects.
- M6g regression changed only to assert responsive dimensions instead of exact old hard-coded widths. M6h regression changed only to assert the new explicit-row-selection guard instead of the prior weaker non-empty preview ID. Existing deck, draw, card index, art/source, no-duplicate and undo tests remain.
- Wire M6i into existing Weather COSMOS JPL/MAGICK CI suite; re-check exact PR-head CI and mergeability before declaring a technical pass. Automated JavaScript/QML string inspection is **not** native Qt rendering.
- Native visual acceptance requires the operator to re-open DIGITAL THREE and FIVE, click a focus card, close the inspector, switch to physical INDEX, verify row-selected highlighting and add/undo; compare with the provided Nov 6 screenshot baseline.

## WATCH OUT FOR

M6i is a source-level visual improvement, not yet proof that actual Quickshell font scaling, screen height and clip boundaries are correct. The user requested a later system-wide Visual V3 overhaul; this milestone only fixes Tarot's immediate legibility and usability, preserving the current acceptable V5 theme. The layout intentionally shows up to five cards but does not add a new scrolling feed, tarot interpretations or card storage. If actual native scaling differs from these assumptions, adjust layout geometry **after** native screenshot verification.

Physical ownership of The Wild Unknown deck does not grant distribution rights for Kim Krans's copyrighted imagery; no artworks are bundled. The optional local image file display assumes independently lawful user-provided assets. No personal records, scans, camera captures, external image URLs or guidebook text are used.

No live Hospital connection, local Fedora write, Quickshell reload, merge or production activation occurred in this assignment. Operator acceptance is not implied by passing CI.

## CHECKLIST

- [x] Reconstruct M6g/M6h current source and both merged PRs
- [x] Reconcile screenshot evidence to current QML fixed sizing and selection behavior
- [x] Check canonical Hospital rules, ownership and active PR conflicts
- [x] Add pure responsive layout model and larger Tarot card inspection overlay
- [x] Make physical entry require a fresh explicit selected row
- [x] Preserve digital shuffle, physical state and licensed-art boundary
- [x] Add M6i test and update only presentation-bound prior assertions/CI
- [ ] Exact-head GitHub workflow pass and mergeability
- [ ] Operator-authorized merge and separate local installation
- [ ] Native user visual, click and layout acceptance

## NEXT

Review exact GitHub checks and repair only evidenced failures. After authorized integration, compare the screenshot baseline against the new three/five spread sizes and catalogue preview at the user's actual panel dimensions. Test inspector CLOSE/next/previous, physical selection/default preview distinction, and original draw/undo. Later M6j may expand accessibility or rights-cleared source interpretations, but must receive separate bounded scope. Do not use Tarot visual fixes to trigger the deferred global Visual V3 redesign.

## DECISIONS

Keep one Wild Unknown card identity model and M6h physical state engine. M6i owns only Tarot presentation, not MAGICK routing, artistic rights or private data. Keep a source-first read-only user-art boundary. Technical completion and native operator acceptance remain separate.
