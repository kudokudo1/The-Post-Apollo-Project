# Weather StationW // MAGICK M5h Neon Zodiac + Draggable Timeline

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
ASSIGNMENT // Zodiac glyphs, colored glow, and tactile timeline thumb
ROLE // External Hospital-compatible development worker; live Hospital registration not verified
BASE // main 1ef6fc2a4d0881ad04452ba17cf9edc684e05b49 (M5g PR #1166 merged)
BRANCH // feat/weather-magick-m5h-neon-zodiac-scrubber-20261103
PHASE // Isolated GitHub implementation; CI verified on implementation commit, final PR checks and operator runtime acceptance pending
OWNERSHIP // Existing MAGICK visual/presentation files only; no root Weather, MAGICK Python/JPL provider, Settings++, COSMOS, SUBJECTS or Stage Director changes

## IMPLEMENTATION

The operator requested real zodiac symbols rather than the old AR/TA/GE/.. codes, richer colored glow, and a physically grabbable time thumb that updates the visible chart while moving.

- widgets/weather/StationMagickCelestialVisualPolicy.js: new ZODIAC_GLYPHS with the twelve Unicode symbols in conventional 0–360° tropical reference order, fire/earth/air/water color order mapped to existing Post-Apollo orange/green/cyan/magenta, plus timelineHandleFraction and timelineHandleX based only on actual M4 source time samples. Existing compact ASCII SIGNS remains for backward-compatible inspector text.
- widgets/weather/StationMagickCelestialInstrument.qml: Canvas renders true glyphs using Noto Sans Symbols 2 with Qt fallback. QtQuick Context2D shadowColor/shadowBlur adds restrained luminous halos to zodiac symbols and rings, spoke/relationship paths, source body points, chart curves, event markers, source labels and relation gauge. Existing ActionButton controls already supply native glows.
- The M5g 21px clickable event strip becomes a 30px horizontal slider with a 17x20px magenta/white thumb, grip ribs, and native RectangularShadow halo. Parent Canvas still renders source event ticks and selected-source marker.
- A single topmost MouseArea receives press, drag, release and cancel. Press near thumb retains pointer offset; moving more than 3px immediately selects nearest real M4 sample and updates all linked views. A still click preserves event-marker selection; clicking elsewhere locks the nearest real sample. No release-only commit or fabricated intermediate positions.
- The slider thumb and inspector clamp to actual samples inside the current zoom/pan window. Zoom continues to change the interval under the handler; no external Python calls are triggered.
- Column spacing is reduced from 7px to 5px to accommodate the taller slider without expanding the compact instrument. Existing source/checksum labels, time navigation, event arrows and controls remain.

New tests: tests/weather/test_magick_neon_scrubber_m5h.js
New workflow: .github/workflows/weather-magick-neon-scrubber-m5h.yml
Handoff: docs/weather-magick-neon-zodiac-scrubber-m5h-handoff.md

No new process, timer, network request, user location inference, archive writer, dependency installer, font file, or personal interpretation/journal.

## HOW TO USE

After operator-approved merge and deployment through normal local update/restart:
1. Open Weather Station > SUBJECTS > MAGICK > ASTROLOGY and select CALCULATE.
2. ZODIAC now displays twelve glyphs ♈ ♉ ♊ ♋ ♌ ♍ ♎ ♏ ♐ ♑ ♒ ♓, with element-colored glow and luminous measured planetary markers.
3. In all four modes, grab the white/magenta thumb on the horizontal timeline strip and drag it. Selected UTC time, chart, wheel and inspector move between real M4 samples as you drag.
4. Click a colored event marker without dragging to inspect its calculated UTC event time and the nearest sampled position. Click empty track to select the nearest visible M4 sample.
5. Existing TIME, EVENT, UNLOCK, RESET, scroll zoom, mode switches and source checks continue to work.

A timeline slider suits an ordered time range. An index rail is better for jumping between discrete categories or destinations; unlike the existing vertical SelectorSlider/IndexRail, this is an intentionally horizontal local control, with the same native visual grammar and immediate feedback.

## VERIFY

On implementation commit bb065b8edcd648d9de8d8e2b076bd72e8bf4c1f9, all 3/3 GitHub jobs succeeded: dedicated new tests, M5a–M5g/HOME/COSMOS regression tests, and real Moon/Sun JPL DE440s to M4/M5g presentation checks within a disposable runner. The latter completed 7/7 source-identity checks with zero skips.

Node tests verify zodiac glyph codepoint order, semantic element palette, visible sample time position, source-index drag parity, event-click preservation and QML pointer/Qt glow bindings. They also guard against extra data processes or invented data.

From repo root:
    node --test tests/weather/test_magick_neon_scrubber_m5h.js
    node --test tests/weather/test_magick_relations_timeline_m5g.js
    node --test tests/weather/test_magick_chart_legibility_m5f.js

This is not native Quickshell acceptance. Native font fallback, actual bloom intensity, visual overlap, input capture and frame rate require operator screenshots/testing.

## WATCH OUT FOR

- Unicode zodiac symbols depend on Qt's font support/fallback. If Noto Sans Symbols 2 or a comparable glyph font is absent, the operator may see missing-glyph boxes; no font is bundled or installed.
- Qt Canvas shadowBlur is supported in Qt 6 but actual visual intensity and performance vary by compositor/GPU. The instrument has neonEnabled true by default and can disable blur for a future performance triage.
- The slider selects discrete existing M4 samples and may visibly snap. It does not invent a position between source timestamps.
- Event times may occur between samples, and the displayed position is explicitly the nearest sample. Event markers remain selectable on click.
- When zoom moves a locked point offscreen, the visible inspector/thumb use the nearest sample within the visible window, preventing a misleading offscreen thumb.
- There is a single root-owned M4 Process, and this change does not start another ephemeris worker or install dependencies.
- The semantic palette remains: orange identity/fire, green earth, cyan air/structure, magenta water/selected priority, yellow events. Red is not used.
- Actual compact panel geometry and scrollbar interaction require live Quickshell verification before operator acceptance.
- No Fedora/local machine files, Quickshell instance, launcher or running JPL backend were modified.

## CHECKLIST

- [x] Latest main/M5g merge and active Weather ownership preflight
- [x] Actual zodiac Unicode symbols and elemental semantic colors
- [x] Qt Canvas colored neon for chart, zodiac wheel, relations and timeline
- [x] Luminous physical timeline grab handle, event-tick click retained
- [x] Real sample updates during drag and visible-window clamping
- [x] Dedicated tests/CI and earlier real JPL regression passed
- [ ] Final PR-head check after documentation
- [ ] Operator merge authorization
- [ ] Live small/large Station glyph, glow and drag acceptance

## NEXT

Review M5h in its own PR, merge only under operator authority, then deploy locally with separate approval. Test glow/Unicode text, drag thumb, event ticks, zoom under handle, body inspector and source/error states. Refine visual intensity and thumb dimensions from actual operator screenshots, not guesses. Larger multi-body relationship graphs and automatic first-time MAGICK provisioning remain separate work.

## DECISIONS

Use the horizontal slider interaction pattern rather than an IndexRail or modifying the shared vertical Slider. Preserve live scrubbing, source-backed time samples, isolated visuals and owner-controlled merge/deployment. No live Hospital registration claimed.
