# Company Vector Atlas // M10 motion and fixture-only hub bridge

**Patient:** kudokudo1/The-Post-Apollo-Project  
**Room:** Company Network native vector renderer  
**Role:** external Hospital-compatible Nurse 2; not live registered  
**Assignment:** isolated performance instrumentation and synthetic-only hub feed; no Quickshell installation or active Company access  
**Checkpoint predecessor:** M9 PR #1251 merged; 6/6 CI green, native screenshots manually inspected

## IMPLEMENTATION

M9 proved a geographically anchored **synthetic** map marker and real neighborhood, village and cross-border vector streets. M10 adds two strictly experimental capabilities to the standalone Qt/MapLibre prototype.

1. **Synthetic fixture-to-marker data path.** A fixed, versioned \`experiments/company-vector-qt/fixture-hubs.json\` contains precisely three fake location records near a known public Toronto test viewport. \`--fixture-hubs\` explicitly enables it, and only when \`--styled-online\` or \`--online\` is explicitly selected. C++ opens only this compile-time-pinned file, strictly validates schema, count, keys, lengths, finite coordinates, and duplicates, then passes only four display fields to QML using a context property. QML creates \`MapQuickItem\` objects at those coordinates and supports selection logging by fixture ID. The existing M9 one-marker test remains.
2. **Scripted camera motion and real frame-swap timing.** An explicit \`--bench-pan-zoom\` causes a deterministic, public-coordinate scripted pan and fractional zoom around Toronto after an 8-second tile-loading allowance. The script updates the map every 33 ms for 150 steps, without user input, during a 5-second measurement window. C++ observes \`QQuickWindow::frameSwapped\` using \`QElapsedTimer\`, and logs one structured \`BENCH_FRAME_PACING\` JSON object with frame-interval count, median, p95, and maximum in milliseconds. It refuses to label fewer than 10 intervals as a valid measurement.
3. **CI evidence.** The existing isolated GitHub native job builds the renderer once, retains M5–M9 screenshots, then executes the opt-in Toronto performance/fixture gate. It checks fixture parsing, three marker additions, completion of all 150 motion steps, benchmark output and finite timing values, and uploads the log as an artifact.

## HOW TO USE

All native test work runs in disposable GitHub CI, not on the operator's Fedora Silverblue desktop.

Optional standalone test **only after explicit operator approval and a compatible test installation**:

\`\`\`bash
./company-vector-probe --styled-online --sample=NEIGHBORHOOD \
  --fixture-hubs --bench-pan-zoom
\`\`\`

This makes network tile/glyph requests for the **public Toronto test viewport**. No real company, employee, client, account or provider records are opened, modified or transmitted. The marker fixture is a repository test artifact and has no company authority.

## VERIFY

Python contracts:

\`\`\`bash
python3 -m unittest discover -s tests/company -p 'test_company_vector_motion_m10.py' -v
python3 -m unittest discover -s tests/company -p 'test_company_vector_locality_m9.py' -v
\`\`\`

Native evidence must include \`SYNTHETIC_FIXTURE_VALIDATED 3\`, \`FIXTURE_MARKERS_ADDED count=3\`, \`BENCH_MOTION_DONE steps=150\` and one \`BENCH_FRAME_PACING\` object. No arbitrary "60 FPS passed" claim is allowed.

A CI timing result includes software OpenGL, tile loading and runner scheduling effects. It is **not** representative of the operator's NVIDIA/Fedora GPU, compositor, input-device latency or multi-display setup, and does not by itself prove an interactive user experience without jitter.

## WATCH OUT FOR

- No live Company directory reads, IPC bridge to the Quickshell process, account grants, personnel/client records, or production service coverage. This fixture tests data-to-map plumbing **without** accessing protected systems.
- Do not introduce arbitrary file-path arguments or exports of owner-private Company JSON. Actual Company marker data later needs an explicit read-only, permission-filtered bridge contract and operator acceptance.
- The current QML UI can visually overlap busy city geometry at very high zoom; marker clustering and label collision avoidance remain separate design steps.
- OpenFreeMap is a prototype source with no enterprise SLA. Tile requests disclose only fixed public test locations under this test.
- CI frame swaps are not a proxy for local Wayland input latency or frame pacing. That gate requires explicit native desktop testing.
- M10 is not a live map replacement. Existing Company Coverage and \`shell.qml\` remain unchanged.

## CHECKLIST

- [x] M9 high zoom and one marker native render verified
- [x] Synthetic-only fixed-format fixture and no-private-path validation
- [x] Fixture-fed geographic map items and selection signal
- [x] Deterministic pan/zoom input driver
- [x] Qt frame-swap interval instrumentation
- [x] Isolated CI runner test + artifacts
- [ ] M10 native job and log acceptance
- [ ] Manual inspection that all fixture markers remain geographic during animation
- [ ] Real Fedora/SwayPX compositor benchmark under separate local approval
- [ ] Permission-aware, read-only real Company hub-to-renderer bridge
- [ ] Operator accepts any swap away from old map

## NEXT

Analyze native \`BENCH_FRAME_PACING\` and distinguish source/Qt rendering errors from expected software GPU overhead. Add a second isolated comparison under a cached viewport, and design a local IPC bridge that exposes only authorized, non-personal records. **Do not implement live Company reading or production activation as part of this contract.**

## DECISIONS

This milestone verifies topology and timing with fake data first. Real organization scopes/permissions are not inferred from a local hub label. Existing Company widget, shared shell, Weather, identity services and local desktop are untouched.
