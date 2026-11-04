# Weather StationW // MAGICK M5i Zodiac Visibility Repair

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
ASSIGNMENT // Repair missing zodiac-sector symbols observed in the operator's live compact Station
STAFF ROLE // External Hospital-compatible source worker; no verified live Hospital registration
BASE // main ef989d86d3cd43dfa6e8a8993941d7c9a4e46b14; M5h PR #1171 already merged
BRANCH // fix/weather-magick-zodiac-visible-vectors-20261103
PHASE // GitHub isolated fix verified in CI; merge and live Qt acceptance pending
OWNER BOUNDARY // MAGICK celestial presentation QML only, new pure vector policy, specific tests/workflow; no shared providers, COSMOS, Weather M28-S, Settings++, Clock or Stage Director files

## IMPLEMENTATION

The operator's November 3 live screenshot shows the zodiac wheel rings, body points and luminous timeline thumb but none of the 12 zodiac symbols. GitHub main contains M5h, so this is not simply an unmerged PR.

Root cause is not conclusively proven on the operator machine, but the existing implementation depends on Qt Canvas painting Unicode characters using a requested Noto Sans Symbols 2 font. A missing or incompatible Canvas font fallback is a plausible direct cause. There was no visual/raster test on actual compact dimensions in M5h.

The repair removes the font dependency from the wheel-sector labels:
- Added widgets/weather/StationMagickZodiacVectorPolicy.js: twelve original, hand-drawn normalized 24x24 zodiac sign outlines, conventional Aries-through-Pisces order; sectorCenter positions each at the CENTER of its 30-degree tropical reference slice rather than on boundary spokes. Bounds ensure 9.3px glyph chips stay inside a 100–220px high canvas.
- Updated widgets/weather/StationMagickCelestialInstrument.qml: new paintZodiacVector uses the existing Qt Canvas to stroke each sign using M/L/Q/C/Z vector commands, not Unicode fillText, font files or font fallback. Each sign has a dark legibility chip, colored edge halo, dark outline stroke, bright colored stroke, and stronger glow for the selected source body's sign. Existing orange/green/cyan/magenta elemental palette and data-derived source angular positions remain unchanged.
- Preserves Unicode glyph IDs/abbreviations as metadata in StationMagickCelestialVisualPolicy.js. Replaces center "0° / zodiac character" label with a plain readable "0° / TROPICAL" because the font-dependent character could also fail.
- Updates original M5h tests to require a vector glyph draw path rather than accepting a font-dependent Unicode glyph paint attempt. Earlier time scrubber and source contracts remain unchanged.

Added tests:
- tests/weather/test_magick_zodiac_visible_m5i.js: validates all 12 glyph path shapes, valid finite 0–24-unit commands, uniqueness of visible positions, compact 100/110/120/150/220px wheel clipping, correct tropical 15+30*n-degree centers, actual QML renderer, no source service changes. Can export a tiny SVG fixture with exactly the same vector strokes.
- tests/weather/test_magick_zodiac_visible_m5i_pixels.py: rasterizes SVG via CairoSVG (CI-only) at 4x resolution, samples the glyph interior within the actual 410x112px screen area, excludes the surrounding colored chip and asserts independently colored pixels for every sign. This specifically tests *visibility*, not just source-code presence.
- .github/workflows/weather-magick-zodiac-visible-m5i.yml: pure JS and actual compact raster check, prior M5a-M5h+HOME regressions. CairoSVG and Pillow are installed only on a disposable GitHub runner; there is no end-user dependency.
- docs/weather-magick-zodiac-visible-m5i-handoff.md: this handoff.

No ephemeris/kernel, data producer, timeline slider, root Quickshell Process, browser, location, personal readings, local font, or persistent storage code changed.

## HOW TO USE

After operator-authorized merge and the normal locally approved repository update/restart:

Weather Station > SUBJECTS > MAGICK > ASTROLOGY > CALCULATE > ZODIAC.

Expected: twelve visible, color-coded zodiac glyphs around the wheel, even if the Noto symbol font is absent. Planetary markers, relationship angle lines, timeline handle and all previous source interactions remain unchanged. The sign under the selected source planetary body's longitude receives a slightly stronger halo.

No new packages, fonts, installation scripts, terminal launch variables or external browser are required for this repair.

## VERIFY

Implementation head aecdd36db5d7ad074336246d518ef01755fcf318:
- GitHub 2/2 jobs successful (font-free compact render and core validate).
- New Node tests 5/5 passed.
- SVG raster CI succeeded at 410x112 with **all 12 glyphs visibly rasterized** and at least 592 matching symbol-color interior pixels in every sign at 4x render resolution. This was an independent actual-pixel test without any installed font glyph.
- Original M5h tests were strengthened to require font-independent renderer, not weakened. All M5h and earlier MAGICK, HOME contracts passed.
- This does not test actual operator Quickshell Canvas pixels or font-independent Qt Context2D runtime behavior. It tests the exact vector source and SVG visibility under compact geometry.

Run from repository root:

    node --test tests/weather/test_magick_zodiac_visible_m5i.js
    node --test tests/weather/test_magick_neon_scrubber_m5h.js

Optional disposable pixel test with CairoSVG and Pillow available on tester/CI:

    node tests/weather/test_magick_zodiac_visible_m5i.js --emit-svg /tmp/zodiac-compact.svg
    python3 tests/weather/test_magick_zodiac_visible_m5i_pixels.py /tmp/zodiac-compact.svg

The 12-symbol visual fixture is diagnostic only, not an asset shipped to users.

## WATCH OUT FOR

- The original absent-glyph symptom is confirmed in the user screenshot; the exact Qt font failure was not reproduced on the operator host. Font-independent vectors remove that failure mode.
- Sign drawings are hand-drawn graphical representations of standard zodiac symbols, rendered as strokes rather than glyph text. They denote 30-degree conventional tropical ecliptic sectors, not sidereal star constellations.
- In very small screens, labels may look dense. The drawing policy positions centers so their dark 9.3px legibility chips fit inside the visible canvas. Real font coverage no longer matters.
- Qt Canvas shadowBlur visual strength and GPU frame cost are not covered by the SVG test. Native Quickshell zoom/pan, click, wheel and compact layout require operator acceptance.
- No local Fedora, Quickshell process, venv, JPL file, or font installation was changed. Repository PR must be merged and changes pulled/deployed before a new screenshot can validate live behavior.
- Concurrent M28-S Weather CLASSIC/SUBJECTS navigation work remains outside this patch. Do not merge or rewrite its branch.

## CHECKLIST

- [x] Confirm M5h merged and current repo main/overlap preflight
- [x] Confirm missing zodiac glyphs from live screenshot
- [x] Replace font-dependent Canvas Unicode with twelve real vector symbols
- [x] Preserve source sample geometry, zodiac metadata, and timeline handler
- [x] Keep symbols inside compact canvas and improve colored contrast
- [x] 2/2 GitHub checks including independent compact-size pixel raster
- [ ] Recheck CI on final PR head after handoff
- [ ] Operator acceptance / authorized merge
- [ ] Local update under user approval
- [ ] Actual Quickshell screenshot verifying twelve symbols and glow
- [ ] Final operator acceptance of visual density and colors

## NEXT

Recheck final PR-head CI and mergeability, then operator review/authorized merge and local rollout. Verify that each zodiac sign is visible at current Station size, that changing the body highlights the correct sector, and that M5h thumb drag/time zoom still works. Keep potential later glow tuning separate from restoring missing symbols.

## DECISIONS

Use font-independent vector art within the existing Canvas rather than adding a new font package, SVG image asset, background renderer, polling service or external browser. Preserve operator authority and existing Weather Station source ownership. No live Hospital registration or local writes claimed.
