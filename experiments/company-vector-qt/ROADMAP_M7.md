# Company Network M7 // Continuous Post-Apollo vector style pilot

## IMPLEMENTATION

The operator clarified that **Flint and Ontario are only sample locations**. The intended map is a **continuous, nationwide-US and globally extensible basemap**, with Canada and Mexico handled by the same engine. It must expose more detail as the operator zooms without replacing the map with a different-looking raster view.

This work provides an **isolated MapLibre GL Style Specification v8** theme, \`style-post-apollo-online.json\`, for the preexisting standalone Qt/MapLibre experiment. It uses a worldwide OpenMapTiles-compatible vector source from OpenFreeMap (\`https://tiles.openfreemap.org/planet\`) without a country bounding box. It does **not** ship roads locally; detail depends on source availability.

The 43 style layers cover:

- Water and waterways, park/landuse, national and regional borders
- Distinct road classes: motorway, trunk, primary, secondary, tertiary, minor (including residential/unclassified), service, track, pedestrian and paths
- Building footprints at z14+, road names at z12+, address numbers at z17+
- Settlement labels: countries/states, cities, towns, villages, suburbs, quarters, neighborhoods, hamlets and isolated dwellings, with later zoom thresholds for smaller settlements
- Post-Apollo visual palette: \`#1B0623\` background, \`#ED981A\` motorway, \`#C74EC7\` primary, \`#5B5FD4\` secondary, \`#55CFCA\` tertiary; pale lettering, dark water and glowing-color accents

The runtime adds an explicit **\`--styled-online\`** flag for loading this local JSON theme **against online vector tiles**, while leaving the original \`--online\` Liberty reference and the default offline synthetic test unchanged.

Representative camera preset buttons in the experimental Qt window cover the US overview, West Coast, Midwest, Northeast, rural US, Canada, Mexico, Alaska, Hawaii and Flint. These are **test views**, never data limits. The underlying provider remains global.

## HOW TO USE

**Read/test on GitHub** through M7 style CI. No local installation or live desktop change is required.

For optional standalone test **only after the separate M6 MapLibre plugin discovery gate passes and the operator approves a local test environment**:

\`\`\`bash
# On a disposable test build with Qt6/MapLibre dependencies already installed:
./company-vector-probe --styled-online
\`\`\`

This is deliberately opt-in. It contacts OpenFreeMap for vector tiles and glyphs; the network provider can observe the requested map regions and the requesting IP. No worker, client, hub or company records are used.

\`./company-vector-probe\` alone still uses synthetic offline map shapes. \`./company-vector-probe --online\` still uses the unmodified Liberty reference style.

## VERIFY

Deterministic Python tests validate style JSON structure, all road and settlement classes, layer IDs, scale-dependent thresholds, color identity, global source URL/attribution, no credentials, and explicit online flags. GitHub CI only exercises these **static contracts**; it does not assert the runtime QML module loads or that source geometry renders at every scale.

A **native rendering and visual inspection gate** remains required. After M6 runtime is working, test all representative camera presets and scroll/drag/zoom, paying particular attention to small/rural roads, neighborhood labels, and building/number detail.

## WATCH OUT FOR

- **Not yet a full company map.** This is an isolated style and view-selection pilot; no edits to \`CompanyCoveragePane.qml\`, shell or Company services.
- **No guaranteed address completeness.** Building and housenumber availability depend on how well each place is mapped in OSM/OpenMapTiles. No fabricated addresses are added.
- **Not a contracted provider.** OpenFreeMap is the public prototype source, not a signed production SLA. Validate attribution, OpenStreetMap ODbL and OpenMapTiles schema terms, provider limits and enterprise requirements before business deployment.
- **Raster/Qt integration remains pending.** Do not merge into Quickshell or globally force OpenGL. The rendering engine must pass the isolated native test and desktop compatibility gate.
- **Geographic layers are not authorization.** Roads/cities never imply an active hub, client catchment, referral eligibility, or cross-border operating approval.

## CHECKLIST

- [x] Nationwide + international scope fixed
- [x] Create open-licensed vector style for nationwide road hierarchy
- [x] Add town, village, suburb, neighborhood and hamlet labels
- [x] Add buildings, address labels and POIs for close zoom levels
- [x] Keep default offline mode and original Company widget unchanged
- [x] Add deterministic CI checks
- [ ] Verify M6 native Qt plugin/runtime
- [ ] Inspect actual Post-Apollo-styled vector road imagery at multiple US/Canada/Mexico sites
- [ ] Confirm smooth input and zoom performance
- [ ] Define self-hosted/contracted data service and offline caching for company scale
- [ ] Integrate into Company widget or isolated sidecar with operator acceptance

## NEXT

Finish [runtime discovery PR #1237](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1237), then run the explicit styled-online sample at contrasting sites: national overview, city grid, suburban streets, rural roads, and international borders. Fix schema/style mismatches based on screenshots and telemetry. After that, add company hub overlays with evidence-backed coverage.

## DECISIONS

This style uses open geographic data rather than copying proprietary Google/Apple map content. The target is all geographic areas supported by the provider, not a Flint/Ontario corridor. Native integration and production deployment remain separate operator-authorized decisions.
