# 🏥💜 Hospital // MAGICK M6g Wild Unknown Tarot Foundation

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station Visual Intelligence / bounded MAGICK Tarot feature expansion
ASSIGNMENT // M6g 78-card Wild Unknown deck identities, spread/draw UI and optional local-only artwork references
STAFF ROLE // Nurse 2, external Hospital-compatible
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL; no verified live Hospital Room registration or desktop access
PHASE // GitHub isolated draft; CI, operator approval, merge, local activation and native acceptance separate
BRANCH // feat/weather-magick-m6g-wild-unknown-tarot-20261106
RECOVERY // M6f PR #1368 verified merged (commit 318029837dd68354e3085efa07dfe6656a47c0af). Original LENSES and GRIMOIRE reference atlas retained.

## IMPLEMENTATION

The operator requested The Wild Unknown deck specifically because their physical deck's look fits the Meta/Post-Apollo design. They then explicitly said "okay go ahead" to implementation. Rechecked Syntagma AGENTS.md and Hospital Agent Protocol, current GitHub main M6f merge, no active MAGICK or Weather PR collisions, route and QML patterns. This is a bounded M6g repository implementation, not permission to write to the Fedora desktop, merge, install scanning software or distribute Kim Krans illustrations.

**Verified source:** The Wild Unknown Tarot is a 78-card deck created by Kim Krans, published by HarperOne. Original creator's source: https://kimkrans.com/the-wild-unknown . Publisher description: https://www.rpmystic.com/external/title/9780062466594/ . Its court cards use **Daughter, Son, Mother, Father** rather than Page, Knight, Queen, King. Reference for family titles: https://marselia.app/tarot-decks/wild-unknown-tarot . No numbered-major claim is made because available secondary guides disagree on Justice/Strength sequencing. Identity cards do NOT include guidebook interpretations or illustration reproductions.

- New pure `widgets/weather/StationMagickTarotDeckPolicy.js` defines the named 22 Major Arcana and 4 × 14 suit cards (Wands, Cups, Swords, Pentacles) using the original Daughter/Son/Mother/Father court names. Every entry has a unique identity key, family, name and stable index. Catalogue supports all/major/four-suit filter without inventing symbolic meanings.
- Transparent pseudo-random Fisher-Yates shuffle/deal of the full 78-card set, with no replacement and strict injected random validity. Supports single, three-position (past/present/future), five-position (context/tension/perspective/possibility/reflection) spreads, plus optional independent reversal rolls. The QML calls Math.random explicitly labelled **pseudorandom**, not cryptographic, genuine fate, prediction, or secret high-stakes influence. Readings exist in QML memory only and are not automatically saved.
- New `widgets/weather/StationMagickTarotCard.qml` draws an **original Post-Apollo geometric** monochrome/cyan/blue/yellow placeholder for every card, without imitating exact Krans illustration layouts. A deliberately optional `Image` loads only a **valid absolute local file URL** based on an explicitly entered directory and the card's predefined `id + ".png"` filename. A local image rotates on reversal, while its card label remains upright for readability. Default install has no actual Wild Unknown artwork files.
- New `widgets/weather/StationMagickTarotPane.qml` provides DRAW and INDEX modes, SINGLE/THREE/FIVE spread buttons, REVERSALS toggle, SHUFFLE + DRAW, CLEAR, displayed cards and original placeholders. INDEX filters families, pages through all card IDs and permits selecting a card to preview. An optional text field accepts a **local folder path in session only**; it never opens a URL, scans folders, uploads, copies or saves artwork. The user can supply private numbered PNG files with names such as `major-the-fool.png`, `wands-daughter.png`, `cups-ace.png`. The card side shows whether local art loaded or original placeholder remains.
- Existing `StationMagickSubjectPane.qml` mounts this page **only** at INDEX > DIVINATION > TAROT, optionally as an independent full-height content screen; other MAGICK references, LENSES, GRIMOIRE, JOURNAL, astronomy, source providers and menus remain unchanged.
- Existing `StationMagickSubjectPanelPolicy.js` updates TAROT's explanatory note only. The isInterpretationImplemented() global cross-domain gate remains false; producing a symbolic random draw does not mean the application has connected an astrological/medical reading or traditional guidebook interpretation.
- No new Process, Timer, WebEngine, browser, API, global local credentials, weather source, file writer, journal storage, network upload, copyrighted art, guidebook text or runtime service.

## HOW TO USE

After operator-authorized GitHub merge and **separately approved Fedora deployment**:

Open Weather Station > MAGICK > INDEX > DIVINATION > TAROT. The default deck identity is THE WILD UNKNOWN TAROT. Press SINGLE, THREE or FIVE, enable or disable REVERSALS, and click SHUFFLE + DRAW. The display uses an original Post-Apollo placeholder for each card if no personal artwork folder is provided. Each new click re-shuffles the 78 card identities and picks unique cards with the named symbolic spread positions. CLEAR discards the current reading from the UI; INDEX lets you browse the complete 78-card identity catalogue through family filters and pages.

Optional local artwork: prepare your **own authorized** PNG files privately, named by the card keys, in an absolute local directory. Type the directory into LOCAL ART DIR. Example `/var/home/USER/Pictures/PrivateTarot` (actual path is not assumed). The in-memory field constructs only `file:///...` URLs for known card names and reads the images without copying or uploading them. An image will appear only if a matching local file exists and Qt can load it. This is not a bulk import/scanner, not a rights grant to reproduce artwork, not permanent settings storage, not a licensing workaround and not a request to upload your scans.

## VERIFY

`tests/weather/test_magick_wild_unknown_tarot_m6g.js` verifies all 78 unique cards, 22/56 structure, exact Wild Unknown court rank names, without-replacement shuffle/three spreads/five spreads, optional independent reversals, invalid random value refusal, source immutability, complete index filter and local filename URL construction and refusal of URLs/unknown IDs/path traversal, QML draw/browser/artwork/geometry and existing route preservation. Added to Weather COSMOS JPL/MAGICK CI workflow next to M4–M6f and Weather/Grammar regressions. Review exact PR-head CI before claiming passed.

Native Qt tests remain pending: compact draw layout at one/three/five cards, card-level focus, wheel/card paging, correct family preview and local PNG loading from a user-authorized private folder. Tests cannot confirm images without files. No live machine was accessed or modified.

## WATCH OUT FOR

**Artwork rights:** Physical deck ownership does not itself license redistribution of copyrighted imagery, scans, or guidebook text. This PR includes **no** Krans artwork, guides or downloaded image assets. Personal scanning/reproduction may also require applicable rights or permissions; the optional local artwork interface does not represent a legal conclusion that copying is permitted. Public Post-Apollo builds should use licensed assets or the original placeholders. This PR does not add an image-copy tool or internet scraper.

**Randomness and interpretations:** `Math.random()` is a pseudo-random generator in Qt JavaScript, not cryptographically verifiable or a guarantee of balanced future draw histories. Readings are symbolic entertainment/practice records in memory and cannot independently predict future outcomes. Spread position labels are user-facing conventions and no author's guidebook text is reproduced. No private notes, readings or deck images are persisted.

**Integration:** Source documentation and Qt components are repository-level until deployed separately. Do not interpret GitHub CI as native visual acceptance. No Merge/Live activation, no local Fedora writes, no Quickshell restart. Existing multi-worker permissions and Hospital authority remain in effect.

## CHECKLIST

- [x] M6f merge and no concurrent MAGICK/Weather PR collisions verified
- [x] Canonical protocol and current Tarot route inspected
- [x] Wild Unknown creator, deck count, court naming checked from current sources
- [x] Full 78-card catalogue and independent pseudo-random draws implemented
- [x] Local image URL policy and original fallback presentation created
- [x] TAROT route hooked without interfering with GRIMOIRE, LENSES or astronomy
- [x] Source/identity/shuffle/rights/privacy regression tests and workflow included
- [ ] Exact-head CI and branch mergeability
- [ ] Operator-authorized merge and separate local deployment
- [ ] Native layout, artwork reading, input and operator final acceptance

## NEXT

Verify exact-head GitHub CI and repair evidenced issues. After authorized installation, inspect all spread counts, the full 78-card catalog, optional reversals and local asset placeholders. If the user chooses to privately prepare art files with necessary rights, use a specifically approved local folder; never push those files to GitHub. A future separate M6h could add secured optional per-user deck art mapping, user-controlled export (rights checked), full Tarot spread interpretation authored by the user, or private journal persistence only after a dedicated data and permissions assignment.

## DECISIONS

The Wild Unknown is the **preferred card identity and visual reference**, without implying rights in its artwork. Protect the artist's content, preserve the accepted Post-Apollo V5 graphical grammar and let a licensed/private local file display only when available. Keep the symbolic tarot engine independent of astronomical source actors and the privacy-sensitive GRIMOIRE JOURNAL. The larger Visual V3 restyle remains deferred.
