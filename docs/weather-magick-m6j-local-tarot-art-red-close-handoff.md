# 🏥💜 M6j // Wild Unknown Tarot Missing-Artwork Diagnostics and Red Inspector Close

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station / MAGICK / TAROT Visual Recovery
ASSIGNMENT // Fix red enlarged-card CLOSE and explain/enable loading of user-provided deck photographs
STAFF ROLE // Nurse 2, external Hospital-compatible
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL, not live Hospital registered
PHASE // GitHub isolated draft; CI/operator review/native deployment distinct
BRANCH // fix/weather-magick-m6j-local-art-status-red-close-20261106
RECOVERY // M6i PR #1380 verified merged into main as d064f5701fb4d92b83795fba07a42c1be04e24a2; no open MAGICK or Weather PRs returned at preflight.

## IMPLEMENTATION

User reported that Tarot cards still show numbers instead of Wild Unknown images and requested a red CLOSE button on the enlarged card window. Inspected main and confirmed the root cause: the deck policy explicitly ships **card identity only** (`DECK.artworkIncluded=false`), and `StationMagickTarotCard.qml` draws a numbered geometric fallback unless its `Image` loads a matching **local file from the user's typed directory**. The default directory is empty. No Wild Unknown illustrations, user photo files, digital scans, or redistribution license were provided. Therefore, this repository patch **does not claim to install the artist's actual images**. The earlier successful source tests did not prove the artwork was available.

Changes:
- The full-size `CARD // INSPECT` **CLOSE** `ActionButton` is now visibly red (red fill, black text, red destructive border/glow behavior), using the canonical `Colors.red`/destructive semantics. Next/previous card controls remain cyan. Closing still resets inspector index only.
- `StationMagickTarotDeckPolicy.js` adds a bounded `localArtworkCandidates(directory,cardId)` function for original known-card file names in **PNG/JPG/JPEG/WEBP** order. It inherits the existing absolute-local-only, known-card-ID and traversal/remote-URL refusals from `localArtworkUrl`, never makes network requests, and never scans directories or copies anything.
- `StationMagickTarotCard.qml` attempts each supported candidate in order after `Image.Error`. Image readiness selects the actual local photo if readable; otherwise a clearly labelled **NO PHOTO** geometric fallback displays instead of a card number. The card/status makes missing artwork explicit rather than pretending the numbered placeholder is Wild Unknown art. On a new card/folder it resets candidate ordering. The enlarged inspector exposes the image readiness/missing-file state.
- `StationMagickTarotPane.qml` now says **NO WILD UNKNOWN IMAGES // SELECT LOCAL ART FOLDER** when the field is empty, and otherwise says **LOCAL ART CHECK** (not falsely "installed"). A valid folder-text syntax changes border yellow, **not green**, because syntax verification does not establish that actual images exist. On INDEX it shows the exact currently previewed card ID as a file naming hint; in full-screen inspection it shows the actual source ID and image status.
- Existing M6g/M6h tests were updated to match the more truthful missing-photo text; a new M6j test verifies local file candidates, safety limits, explicit empty-image states and canonical red CLOSE. Tests added to the current Weather COSMOS/MAGICK CI workflow. M6i responsive drawing, Tarot identities, actual M6g shuffle, M6h manual physical cards, no-duplicate and undo and other MAGICK functions stay unchanged.

## HOW TO USE

After operator-authorized merge and **separately authorized** Fedora installation:

Weather Station > MAGICK > INDEX > DIVINATION > TAROT.

1. Place your own appropriately authorized card image files in a **private local directory**, not inside public GitHub. A sample matching known card is `major-the-fool.png`, `major-the-fool.jpg`, `major-the-fool.jpeg` or `major-the-fool.webp`. A court example is `wands-daughter.jpg`. Images are not included in the software. Rights to reproduce or redistribute original card illustrations are separate from owning the physical deck.
2. Paste the directory's absolute path into `LOCAL ART DIR`. The directory path is held in memory for the session only; no auto-import, file copying, directory scanning, upload, remote link, or new persistent settings occur.
3. Open INDEX and preview a card. The exact card ID filename is displayed at the bottom. A matching file should replace NO PHOTO automatically if Qt's installed image decoder can read it; absent or inaccessible files remain explicitly marked. The same image should appear in the drawn spread and enlarged CARD // INSPECT window. No complete 78-photo image set was supplied or installed.
4. Open a drawn card and press the new **red CLOSE** button to return.

## VERIFY

- `tests/weather/test_magick_tarot_local_art_m6j.js` checks exact valid local filenames/extensions for known card IDs, rejection of remote schemes, path traversal and invalid IDs, no filename guessing or remote fallback, image status/candidate sequencing contracts and red filled/destructive inspector CLOSE behavior.
- Existing `test_magick_wild_unknown_tarot_m6g.js`, `test_magick_tarot_physical_m6h.js`, and `test_magick_tarot_presentation_m6i.js` remain in the original workflow with minimal state-name changes where earlier tests relied on `APOLLO ORIGINAL` text.
- GitHub CI results and PR mergeability must be verified against the final commit before claiming PASS. Source-level checks do not prove local image files exist or Qt can decode them on the user's workstation.

## WATCH OUT FOR

The core missing-image blocker is **artwork availability**. This patch makes the local images load from more file types and makes the missing-state honest. It cannot create or distribute The Wild Unknown deck illustrations from the user's physical-card ownership alone. Actual use requires the user to provide authorized digital image assets locally. Do not upload private scans to a public PR or imply copyright permission. Unsupported formats and local path permission errors will still show missing image status; this is not a licensing workaround.

Do not change global Post-Apollo UI colors, draw/shuffle algorithms, Weather data ownership, journal state, other workers' repos, Fedora live files or Quickshell runtime. No local desktop writes or restart performed. The user's next screenshots after authorized deployment are the native acceptance checkpoint.

## CHECKLIST

- [x] Verify M6i merged, no current open Weather/MAGICK PR collisions
- [x] Check Syntagma AGENTS, Hospital and authority permissions
- [x] Confirm source reason for numbered fallback and absence of bundled art
- [x] Make enlarged-card CLOSE visibly red using canonical component
- [x] Support optional known-card PNG/JPEG/WebP local imagery
- [x] Replace numbered placeholder with explicit NO PHOTO indicator and status
- [x] Show exact expected card filename and honest folder-path state
- [x] Add M6j tests and update earlier contract expectations
- [ ] Exact-head GitHub CI and mergeability
- [ ] Operator-authorized merge, separately approved desktop installation
- [ ] User provides authorized local photos and verifies they load in native Qt

## NEXT

Check exact-head GitHub workflows. Repair evidenced test failures only. Once integrated and installed with approval, test a single local known card, such as `major-the-fool.jpg`, then confirm it displays in INDEX, DRAW and enlarged focus, including red CLOSE; confirm missing images show NO PHOTO and no network access or data write. If importing and naming dozens of personal photos needs automation, plan a separate user-approved, local-first import workflow with clear artwork rights and access scope.

## DECISIONS

The Wild Unknown remains the deck identity and desired personal visual choice. No actual copyrighted images are distributed in Post-Apollo. Use only explicitly designated, authorized user-local photos; no web scraping or file copying. The red CLOSE is a narrowly scoped Tarot control change, and no Visual V3 or broader MAGICK redesign is included.
