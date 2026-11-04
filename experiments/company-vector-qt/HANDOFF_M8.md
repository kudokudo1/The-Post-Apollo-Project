# Company Network // M8 real-vector native smoke and handoff

## IMPLEMENTATION

**Goal:** Prove the already-merged M6 native Qt/MapLibre renderer can display **actual vector streets** from the M7 Post-Apollo style, not only the synthetic offline fixture. Nationwide US, Canada and Mexico, and a globally extensible source remain the intended product scope; screenshot test viewpoints are not boundaries.

M6 compiled the source-built MapLibre v3 QML plugin against matching Qt/ICU and rendered a 1000×700 test fixture. CI uploaded \`company-vector-probe.png\` from run 41910963153. That is native rendering proof but does **not** prove real OSM roads/settlements.

M8 adds two isolated behaviors:

1. \`--sample=USA|RURAL|CANADA|...\` is allowed **only** alongside explicit \`--online\` or \`--styled-online\`. It applies one publicly chosen camera after QML startup and never accepts arbitrary private coordinates.
2. The **existing** isolated native CI job builds the MapLibre library once, renders the original offline fixture and then explicitly renders **USA, RURAL, CANADA** using \`--styled-online\`. It saves four independent screenshots and logs a coarse non-purple pixel count. Screenshots must be visually reviewed; this diagnostic cannot prove road completeness or successful tile loading by itself.

The online style uses OpenFreeMap vector tiles/glyphs and displays attribution. The CI probes disclose **only the three public test viewport locations and the GitHub runner's network information** to OpenFreeMap. They never load private hub data, user geolocation, accounts or personnel. No background task is scheduled and no local desktop process is modified.

## HOW TO USE

Review GitHub CI artifacts from the Company Network M5 isolated Qt6 vector proof workflow on this PR. Inspect four captures: **offline synthetic, USA, RURAL and CANADA**. Success requires that the named OSM vector roads/regions appear in their corresponding captures, not just that a Qt window is present.

On an approved standalone test installation, after the compatible Qt/MapLibre dependencies are verified:

\`\`\`bash
./company-vector-probe --styled-online --sample=RURAL --capture
\`\`\`

This requests remote tiles. Omit flags to keep the default strictly offline.

## VERIFY

Run static tests:

\`\`\`bash
python3 -m unittest discover -s tests/company -p 'test_company_native_online_m8.py' -v
python3 -m unittest discover -s tests/company -p 'test_company_vector_style_m7.py' -v
python3 -m unittest discover -s tests/company -p 'test_company_vector_probe_m5.py' -v
\`\`\`

CI native job is the source of truth for compilation and screenshot output. Any missing/empty map geometry, tile/source errors, missing labels, huge latency or inconsistent palette is a **failed visual acceptance** even if the CI process exits 0.

## WATCH OUT FOR

- OpenFreeMap's public endpoint is a development provider, not an accepted internal enterprise SLA or self-hosted dataset.
- CI screenshot timing is a fixed 15 seconds per online viewport. It cannot prove stable sustained pan/zoom or all geographic coverage; use real runtime telemetry later.
- No Google/Apple proprietary map data is copied.
- MapLibre 3 may have runtime limitations or incompatibilities in Quickshell's process. Standalone success does not authorize global graphics changes.
- Real employee/client records and verified service eligibility remain out of scope.

## NEXT

After screenshot review: fix any M7 OpenMapTiles layer mismatches or style parsing errors; then build the Qt sidecar/view integration and compare latency/zoom smoothness against the old raster-tiles mode. The existing Company widget stays intact until that implementation has independent native acceptance.

## DECISIONS

No live desktop changes, GitHub merges or production activation. Worker is external and Hospital-compatible, with no unverified live registration or takeover claimed.
