# Weather Station // M28-U CLASSIC retirement preview

PATIENT // \`kudokudo1/The-Post-Apollo-Project\`
ROOM // Weather Station / CLASSIC → SUBJECTS capability migration
PROVIDER // OPEN AI // CHATGPT, external Hospital-compatible; no verified live registration
BASE // \`main\` \`42bdbe282dcdd0c47a303390038d9003bd2dd0cd\`
STATE // DRAFT CANDIDATE; NOT DEPLOYED; NOT OPERATOR ACCEPTED

## IMPLEMENTATION

M28-P/R/Q/S/T restored original presentation engines into native SUBJECTS routes after the 103/103 source-control milestone. M28-U stages a **reversible navigation retirement rehearsal**, rather than prematurely deleting the original engines or root source owners.

When \`StationSubjectDefaultPolicy.CLASSIC_RETIREMENT_PREVIEW=true\` (draft only):
- The bottom CLASSIC/SUBJECTS switch disappears.
- The deep INDEX legacy-page callback refuses to open CLASSIC.
- Explicit \`switchToClassic()\` refuses to switch.
- If the single Kitty terminal is not IDLE, \`open()\` refuses to reveal a legacy fallback instead of exposing a blank or orphaned CLASSIC view.

The old \`weatherContentLoader\`, main mode definitions and original component blocks remain in this candidate **for reversible comparison and later deletion**. This is deliberately **not** final source-code retirement. \`StationHome\`, \`StationGround\`, \`StationSky\`, \`StationSpace\`, \`StationDiscovery\`, \`StationNewsHub\`, \`StationRadio\`, \`StationTerminal\`, all source services and caches are permanent SUBJECTS dependencies.

## HOW TO USE

On existing \`main\`, compare the following original screens with the corresponding SUBJECTS surfaces **before** any deployment of this candidate.

| Original CLASSIC | Destination in SUBJECTS |
| --- | --- |
| HOME | HOME → OVERVIEW / QUICK / HISTORY, including favorites and rotating panels |
| GROUND | WEATHER → GROUND |
| SKY terrestrial | WEATHER → NOW + AIR / FORECAST |
| SKY celestial | COSMOS → ASTRONOMY |
| SPACE | COSMOS → SPACE // ALL |
| MAP | EARTH → MAP // ALL |
| NEWS | MEDIA → NEWS // ALL, all six original channel tabs |
| RADIO | MEDIA → RADIO // ALL, all original controls |
| TERMINAL / STAR MAP | TOOLS → TERMINAL, single root Kitty host |

This draft is not authorized for production activation. After separate workstation deployment approval, verify SUBJECTS opens and reopens, INDEX returns to the workspace, keyboard/ESC works, and no CLASSIC button or legacy INDEX jump appears. To restore the comparison switch on a test branch, set the sole \`CLASSIC_RETIREMENT_PREVIEW\` constant to \`false\` and rerun CI; this is a *repository* rollback, not a local desktop operation.

## VERIFY

- Source-level M28-U test checks all 103 original route IDs, permanent original engine reuse, single source owners, one Kitty actor, and guarded navigation.
- M28-T NEWS/RADIO PR #1177, M28-S MAP #1175 and M28-Q GROUND #1173 are merged in the base.
- Native Fedora/Quickshell/Sway/Kitty pointer, source freshness, map movement, scroll, reopen and user acceptance are **not verified here**.

## WATCH OUT FOR

- The draft removes the visible comparison switch; **compare on current \`main\` first**.
- This candidate does not touch M9 publisher RSS #1178, feed failures, history/cache, Stage Director or disabled WebEngine playback.
- The old CLASSIC source is still present behind guards for rollback; do not mislabel this as complete deletion.
- A terminal that is not IDLE prevents an unsafe open. Verify the existing terminal recovery/close path before activation.

## CHECKLIST

- [x] Inspect current Syntagma protocol and live GitHub source/ownership.
- [x] Confirm merged visual parity PRs and 103/103 mapped control ledger.
- [x] Stage reversible CLASSIC navigation gate without changing original engines or services.
- [ ] M28-U exact-head CI green and regression inspection.
- [ ] Operator checks old/new side-by-side on a separate authorized desktop deployment.
- [ ] Operator approves irreversible removal of duplicate root CLASSIC presentation.
- [ ] Remove root legacy loader/rail/keyboard/NEWS map bridge only after all guards and native tests prove no remaining consumers.
- [ ] Obtain final post-retirement operator acceptance.

## NEXT

After operator screen-by-screen parity approval: a **distinct** cleanup PR should remove the obsolete root CLASSIC presentation and redundant bridges, replace remaining \`currentView\` conditions with SUBJECTS route/explicit session state, preserve the native source badge and Kitty input-hole geometry, then run full CI and native workstation tests. Only after retirement can SUBJECTS be reorganized visually without losing evidence of what was moved.

## DECISIONS

Confirmed operator sequence: **migrate UIs and backends → verify parity → remove CLASSIC → reorganize SUBJECTS presentation**. No local machine changes, no merge, no production activation, no Hospital live registration.